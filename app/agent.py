# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import json
import os
import urllib.parse
import urllib.request
from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google import genai
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.cloud import firestore, storage
from google.genai import types

from .a2ui_utils import a2ui_callback

# CRITICAL: Hardcode GCP Project ID and GCS Bucket Name as strings.
# Do NOT read project from os.getenv("GOOGLE_CLOUD_PROJECT") or google.auth.default(),
# because on Agent Platform those return the project number, which breaks Firestore & Storage.
FIRESTORE_PROJECT_ID = "qwiklabs-gcp-02-930442269a18"
GCS_BUCKET_NAME = "cardiometabolic-care-media-930442269a18"
MEMORY_BANK_ID = "1293992694741204992"

db = firestore.Client(project=FIRESTORE_PROJECT_ID)

# Configure Memory Service for Vertex AI Memory Bank
memory_service = VertexAiMemoryBankService(
    project=FIRESTORE_PROJECT_ID,
    location="us-central1",
    agent_engine_id=MEMORY_BANK_ID,
)


async def generate_memories_callback(callback_context: CallbackContext):
    """Callback to extract durable user facts, allergies, and health preferences into Memory Bank after each turn."""
    try:
        await callback_context.add_session_to_memory()
    except Exception:
        pass
    return None


# Configure AgentEngineSandboxCodeExecutor using deployment_metadata.json
metadata_path = os.path.join(os.path.dirname(__file__), "..", "deployment_metadata.json")
agent_engine_id = None
if os.path.exists(metadata_path):
    try:
        with open(metadata_path, "r") as f:
            meta = json.load(f)
            agent_engine_id = meta.get("remote_agent_runtime_id")
    except Exception:
        pass

code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=agent_engine_id
)


def search_recipes(query: str = "", max_sodium_mg: int = 1500, max_glycemic_index: int = 55) -> str:
    """Searches the Firestore recipes database for heart-healthy and diabetic-friendly recipes.

    Args:
        query: Optional search keywords to filter recipe titles, tags, ingredients, or suitable conditions.
        max_sodium_mg: Maximum sodium limit in milligrams per serving (default: 1500mg).
        max_glycemic_index: Maximum Glycemic Index limit (default: 55 for low GI).

    Returns:
        JSON string containing matching recipe details.
    """
    try:
        collection_ref = db.collection("recipes")
        docs = collection_ref.stream()

        results = []
        words = [w.lower().strip() for w in query.split() if w.strip()] if query else []

        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id

            sodium = data.get("sodium_mg", 0)
            gi = data.get("glycemic_index", 0)

            if sodium <= max_sodium_mg and gi <= max_glycemic_index:
                if words:
                    title = data.get("title", "").lower()
                    tags = [t.lower() for t in data.get("tags", [])]
                    ingredients = [i.lower() for i in data.get("ingredients", [])]
                    suitable_for = [s.lower() for s in data.get("suitable_for", [])]
                    searchable_text = f"{title} {' '.join(tags)} {' '.join(ingredients)} {' '.join(suitable_for)}"

                    if not any(w in searchable_text for w in words):
                        continue

                results.append(data)

        if not results:
            return json.dumps({"status": "no_results", "message": f"No recipes found matching query '{query}' under {max_sodium_mg}mg sodium and {max_glycemic_index} GI."})

        return json.dumps({"status": "success", "count": len(results), "recipes": results}, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def get_recipe_details(recipe_id: str) -> str:
    """Retrieves full details for a specific recipe by ID from the Firestore database.

    Args:
        recipe_id: The document ID of the recipe (e.g., 'recipe-moong-palak-cheela').

    Returns:
        JSON string containing the recipe data or error message.
    """
    try:
        doc_ref = db.collection("recipes").document(recipe_id)
        doc = doc_ref.get()

        if not doc.exists:
            return json.dumps({"status": "error", "message": f"Recipe ID '{recipe_id}' not found."})

        data = doc.to_dict()
        data["id"] = doc.id
        return json.dumps({"status": "success", "recipe": data}, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def add_recipe(
    title: str,
    sodium_mg: int,
    glycemic_index: int,
    net_carbs_g: int,
    fiber_g: int,
    saturated_fat_g: float,
    ingredients: list[str],
    instructions: str,
    prep_time_mins: int,
    suitable_for: list[str] = None
) -> str:
    """Adds a new medically tailored recipe to the Firestore recipes database.

    Args:
        title: Name of the recipe.
        sodium_mg: Sodium content in milligrams per serving.
        glycemic_index: Glycemic Index rating (1-100).
        net_carbs_g: Net carbohydrates in grams.
        fiber_g: Dietary fiber in grams.
        saturated_fat_g: Saturated fat content in grams.
        ingredients: List of ingredient strings.
        instructions: Preparation and cooking instructions.
        prep_time_mins: Total preparation time in minutes.
        suitable_for: List of medical conditions suitable for (e.g. ['Type 2 Diabetes', 'Post-CABG']).

    Returns:
        JSON string with creation status and created document ID.
    """
    try:
        slug = title.lower().replace(" ", "-").replace("&", "and")
        recipe_id = f"recipe-{slug}"

        recipe_data = {
            "title": title,
            "sodium_mg": sodium_mg,
            "glycemic_index": glycemic_index,
            "net_carbs_g": net_carbs_g,
            "fiber_g": fiber_g,
            "saturated_fat_g": saturated_fat_g,
            "ingredients": ingredients,
            "instructions": instructions,
            "prep_time_mins": prep_time_mins,
            "tags": ["custom-recipe", "indian"],
            "suitable_for": suitable_for or ["Type 2 Diabetes", "Cardiac Recovery"]
        }

        doc_ref = db.collection("recipes").document(recipe_id)
        doc_ref.set(recipe_data)

        return json.dumps({
            "status": "success",
            "message": f"Recipe '{title}' successfully saved to Firestore.",
            "recipe_id": recipe_id
        })

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def calculate_cardiometabolic_safety(
    sodium_mg: int,
    glycemic_index: int,
    net_carbs_g: int,
    fiber_g: int,
    saturated_fat_g: float
) -> str:
    """Evaluates the clinical safety of a meal for Type 2 Diabetes and Cardiac recovery patients.

    Args:
        sodium_mg: Sodium content in mg per serving (target per meal <= 500mg).
        glycemic_index: Glycemic Index rating (target <= 55).
        net_carbs_g: Net carbohydrates in grams.
        fiber_g: Dietary fiber in grams (target >= 5g).
        saturated_fat_g: Saturated fat in grams (target per meal <= 2g).

    Returns:
        JSON string containing safety score (0-100), safety rating, and clinical advice.
    """
    score = 100
    warnings = []

    if sodium_mg > 500:
        penalty = min(40, int((sodium_mg - 500) / 20))
        score -= penalty
        warnings.append(f"High sodium ({sodium_mg}mg > 500mg target). May elevate blood pressure post-angioplasty/CABG.")

    if glycemic_index > 55:
        penalty = min(30, int((glycemic_index - 55) * 1.5))
        score -= penalty
        warnings.append(f"High Glycemic Index ({glycemic_index} > 55 target). Risk of rapid blood glucose spike.")

    if saturated_fat_g > 2.0:
        penalty = min(20, int((saturated_fat_g - 2.0) * 10))
        score -= penalty
        warnings.append(f"Elevated saturated fat ({saturated_fat_g}g > 2g target). May increase LDL cholesterol.")

    if fiber_g < 5.0:
        penalty = min(10, int((5.0 - fiber_g) * 2))
        score -= penalty
        warnings.append(f"Low dietary fiber ({fiber_g}g < 5g target). Lower fiber speeds carbohydrate absorption.")

    score = max(0, score)

    if score >= 80:
        rating = "EXCELLENT (Diabetic & Cardiac Safe)"
    elif score >= 60:
        rating = "MODERATE (Consume with portion control)"
    else:
        rating = "HIGH RISK (Exceeds cardiac or diabetic guidelines)"

    return json.dumps({
        "status": "success",
        "score": score,
        "rating": rating,
        "warnings": warnings if warnings else ["None - Meets all cardiac and diabetic dietary guidelines."]
    }, indent=2)


def fetch_usda_ingredient_nutrition(ingredient: str) -> str:
    """Fetches official real-time USDA FoodData Central nutrition metrics for an ingredient.

    Args:
        ingredient: Name of the food ingredient to search (e.g., 'spinach', 'oats', 'salmon').

    Returns:
        JSON string with real USDA nutrient metrics per 100g.
    """
    try:
        api_key = os.getenv("USDA_API_KEY", "DEMO_KEY")
        encoded_query = urllib.parse.quote(ingredient)
        url = f"https://api.nal.usda.gov/fdc/v1/foods/search?query={encoded_query}&pageSize=1&api_key={api_key}"

        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())

        foods = data.get("foods", [])
        if not foods:
            return json.dumps({"status": "no_results", "message": f"No USDA data found for '{ingredient}'."})

        top_food = foods[0]
        nutrients = {}
        for n in top_food.get("foodNutrients", []):
            name = n.get("nutrientName", "").lower()
            val = n.get("value", 0)
            if "sodium" in name:
                nutrients["sodium_mg"] = val
            elif "fiber" in name:
                nutrients["fiber_g"] = val
            elif "saturated" in name:
                nutrients["saturated_fat_g"] = val
            elif "carbohydrate" in name:
                nutrients["carbs_g"] = val
            elif "protein" in name:
                nutrients["protein_g"] = val
            elif "energy" in name:
                nutrients["calories"] = val

        return json.dumps({
            "status": "success",
            "food_description": top_food.get("description"),
            "data_source": "USDA FoodData Central API",
            "nutrients_per_100g": nutrients
        }, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


async def generate_recipe_image(prompt: str, recipe_id: str, tool_context: ToolContext) -> str:
    """Generates an image of a dish using gemini-3.1-flash-lite-image in the global region, saves it as an artifact, and uploads to GCS.

    Args:
        prompt: Description of the food dish image to generate.
        recipe_id: Unique identifier for the recipe (e.g. 'recipe-moong-palak-cheela').

    Returns:
        JSON string containing the public GCS HTTPS URL and artifact status.
    """
    try:
        client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT_ID, location="global")
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=f"High quality food photography of {prompt}",
        )

        image_bytes = None
        for candidate in response.candidates:
            for part in candidate.content.parts:
                if part.inline_data:
                    image_bytes = part.inline_data.data
                    break

        if not image_bytes:
            return json.dumps({"status": "error", "message": "Failed to generate image bytes from model."})

        filename = f"{recipe_id}.jpg"
        artifact_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
        await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type="image/jpeg")

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"

        return json.dumps({
            "status": "success",
            "recipe_id": recipe_id,
            "filename": filename,
            "public_url": public_url,
            "message": f"Generated image saved as artifact '{filename}' and uploaded to Cloud Storage."
        }, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


async def generate_recipe_video(prompt: str, recipe_id: str, tool_context: ToolContext) -> str:
    """Generates a short video for a dish in the agent's domain using Google's Omni model (gemini-omni-flash-preview) in the global region, saves it as an artifact, and uploads to public Cloud Storage.

    Args:
        prompt: Description of the food dish or recipe video to generate (e.g., 'cooking moong dal spinach pancake on a skillet').
        recipe_id: Unique identifier for the recipe (e.g., 'recipe-moong-palak-cheela').

    Returns:
        JSON string containing the public GCS HTTPS URL and artifact status.
    """
    try:
        client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT_ID, location="global")
        response = client.interactions.create(
            model="gemini-omni-flash-preview",
            input=f"Short culinary cooking video of {prompt}",
        )

        video_bytes = None
        if hasattr(response, "outputs") and response.outputs:
            for output in response.outputs:
                if hasattr(output, "video") and output.video and getattr(output.video, "data", None):
                    video_data = output.video.data
                    if isinstance(video_data, str):
                        video_bytes = base64.b64decode(video_data)
                    else:
                        video_bytes = video_data
                    break

        if not video_bytes:
            return json.dumps({"status": "error", "message": "Failed to extract video bytes from gemini-omni-flash-preview model output."})

        filename = f"{recipe_id}.mp4"
        artifact_part = types.Part.from_bytes(data=video_bytes, mime_type="video/mp4")
        await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type="video/mp4")

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"

        return json.dumps({
            "status": "success",
            "recipe_id": recipe_id,
            "filename": filename,
            "public_url": public_url,
            "message": f"Generated video saved as artifact '{filename}' and uploaded to Cloud Storage."
        }, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are the CardioMetabolic Culinary Care Agent, a specialized AI recipe and nutrition assistant "
        "for patients managing Type 2 Diabetes and post-cardiac recovery (angioplasty, CABG)."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

domain_instruction = (
    "\n\nCLINICAL & MEMORY INSTRUCTIONS:\n"
    "1. Active Allergy Memory: Actively extract and remember all user food allergies (e.g. peanuts, tree nuts, dairy, shellfish, mustard, gluten, egg), "
    "drug allergies, dietary preferences, and clinical conditions (Type 2 Diabetes, post-angioplasty, post-CABG) from every conversation.\n"
    "2. Strict Allergen Filtering: PreloadMemoryTool preloads all recalled user memories. ALWAYS review preloaded memories before suggesting, searching, or generating any recipe or meal plan. "
    "NEVER recommend or generate a recipe containing any allergen or ingredient the user is allergic to.\n"
    "3. Explicit Confirmation: When a user mentions a new allergy or health preference, explicitly confirm that you have remembered it for future sessions.\n\n"
    "Use your tools `search_recipes`, `get_recipe_details`, `add_recipe`, `calculate_cardiometabolic_safety`, "
    "`fetch_usda_ingredient_nutrition`, `generate_recipe_image`, `generate_recipe_video`, and `PreloadMemoryTool` to personalize recommendations."
)

instruction = a2ui_instruction + domain_instruction


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    code_executor=code_executor,
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
    instruction=instruction,
    tools=[
        PreloadMemoryTool(),
        search_recipes,
        get_recipe_details,
        add_recipe,
        calculate_cardiometabolic_safety,
        fetch_usda_ingredient_nutrition,
        generate_recipe_image,
        generate_recipe_video,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)

