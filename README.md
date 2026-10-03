# CardioMetabolic Culinary Care Agent

An AI-powered clinical recipe, meal planning, and nutrition assistant built with the **Google Agent Development Kit (ADK)** for patients managing **Type 2 Diabetes** and **post-cardiac recovery** (angioplasty, CABG).

![CardioMetabolic Culinary Care Agent Demo](demo.gif)

---

## What the Agent Does

The **CardioMetabolic Culinary Care Agent** combines clinical nutrition guardrails, long-term patient memory, real-time USDA food database queries, and generative media tools to help post-cardiac and diabetic patients maintain safe, culturally relevant diets.

### Implemented Capabilities & Tools

1. **Vertex AI Memory Bank & Long-Term Memory**:
   - Powered by `VertexAiMemoryBankService` and `PreloadMemoryTool`.
   - Automatically remembers durable user facts across sessions—including food allergies (peanuts, tree nuts, gluten, dairy, shellfish), medical conditions, and dietary preferences.
   - Enforces strict allergen filtering prior to recommending any recipe.

2. **Google Cloud Firestore Recipe Database**:
   - `search_recipes`: Filters recipes in Firestore by title, tags, ingredients, maximum sodium content ($\le 1500\text{mg}$), and Glycemic Index ($\le 55$).
   - `get_recipe_details`: Fetches complete ingredient lists, prep time, and step-by-step cooking instructions.
   - `add_recipe`: Allows adding custom medically tailored recipes into the Firestore database.

3. **Cardiometabolic Safety Calculator (`calculate_cardiometabolic_safety`)**:
   - Evaluates meal safety against clinical targets (sodium $\le 500\text{mg/meal}$, Glycemic Index $\le 55$, saturated fat $\le 2\text{g}$, fiber $\ge 5\text{g}$).
   - Produces a 0–100 safety score, categorical rating (*EXCELLENT*, *MODERATE*, *HIGH RISK*), and actionable health warnings.

4. **Official USDA FoodData Central API Integration (`fetch_usda_ingredient_nutrition`)**:
   - Queries real-time official USDA nutrient metrics (sodium, fiber, saturated fat, net carbs, calories) per 100g for any food ingredient.

5. **AI Image Generation (`generate_recipe_image`)**:
   - Uses `gemini-3.1-flash-lite-image` in the `global` region via Vertex AI to generate food photography.
   - Saves image files as ADK artifacts (`tool_context.save_artifact`) and uploads them to a public Google Cloud Storage bucket (`cardiometabolic-care-media-930442269a18`).

6. **AI Video Generation (`generate_recipe_video`)**:
   - Uses Google's Omni model `gemini-omni-flash-preview` in the `global` region via `client.interactions.create` to generate short cooking videos.
   - Saves video files as ADK artifacts (`tool_context.save_artifact`) and uploads them to Google Cloud Storage.

7. **A2UI Rich Surfaces (v0.8 Basic Catalog)**:
   - Uses `A2uiSchemaManager` and `a2ui_callback` to format agent responses as structured A2UI JSON cards, columns, rows, text, and images instead of plain text.

8. **Custom FastAPI Proxy & Chat Frontend**:
   - Lightweight FastAPI proxy (`frontend/main.py`) powered by `a2a-sdk` and `google-auth`.
   - Single-page chat interface (`frontend/static/index.html`) featuring a medical teal theme, quick-prompt pills, sender badges, and a client-side A2UI renderer.

---

## Planned (Not Yet Implemented)

- **Real-Time Continuous Glucose Monitor (CGM) API Sync**: Planned integration with Dexcom/Libre APIs.
- **EHR / FHIR Interoperability**: Direct integration with Epic/Cerner FHIR endpoints for real-time lab data sync.

---

## Architecture & Wired Services

```
┌─────────────────────────────────────────────────────────┐
│              FastAPI Frontend / A2A Proxy               │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│      Google ADK Root Agent (gemini-2.5-flash)           │
└──────┬────────────┬────────────┬────────────┬───────────┘
       │            │            │            │
       ▼            ▼            ▼            ▼
┌────────────┐┌────────────┐┌───────────┐┌──────────────┐
│  Firestore ││ Memory Bank││ GCS Bucket││  USDA API    │
│  Recipes   ││ (Allergies)││ (Media)   ││ (FoodData)   │
└────────────┘└────────────┘└───────────┘└──────────────┘
```

- **LLM Engine**: Gemini 2.5 Flash (`gemini-2.5-flash`)
- **Memory Service**: Vertex AI Memory Bank (`VertexAiMemoryBankService`)
- **Database**: Google Cloud Firestore (`recipes` collection)
- **Object Storage**: Google Cloud Storage (`cardiometabolic-care-media-930442269a18`)
- **Generative Media**: `gemini-3.1-flash-lite-image` (Image) & `gemini-omni-flash-preview` (Video)

---

## Local Setup & Run Instructions

### Prerequisites
- Python 3.11+
- `uv` package manager installed (`pip install uv`)
- GCP project access with Firestore and Vertex AI enabled

### 1. Environment Setup
Clone the repository and install dependencies:
```bash
git clone <repo-url>
cd cardiometabolic-culinary-care-agent
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

### 2. Run Agent Playground Locally
Start the agent with the Vertex AI Memory Bank service:
```bash
uv run adk web . --port 8080 --reload_agents --memory_service_uri=agentengine://1293992694741204992
```

### 3. Run Custom Frontend Locally
Navigate to the `frontend/` directory, install frontend requirements, set environment variables, and launch Uvicorn:
```bash
cd frontend
uv pip install -r requirements.txt
AGENT_ENGINE_RESOURCE_NAME="projects/<project-id>/locations/us-central1/reasoningEngines/<agent-id>" AGENT_DIRECTORY="app" python -m uvicorn main:app --host 0.0.0.0 --port 8080
```
