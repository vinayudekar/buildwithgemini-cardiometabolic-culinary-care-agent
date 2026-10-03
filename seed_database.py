"""Seed script for CardioMetabolic Culinary Care Agent Firestore Database with Indian Recipes."""

import os
from google.cloud import firestore

# CRITICAL: Hardcode the GCP Project ID for Firestore client initialization.
# Do NOT rely on google.auth.default() or GOOGLE_CLOUD_PROJECT env var, as Agent Platform sets it to project number.
PROJECT_ID = "qwiklabs-gcp-02-930442269a18"

SEED_RECIPES = [
    {
        "id": "recipe-salmon-quinoa",
        "title": "Mediterranean Baked Salmon & Quinoa Bowl",
        "sodium_mg": 280,
        "glycemic_index": 35,
        "net_carbs_g": 22,
        "fiber_g": 6,
        "saturated_fat_g": 1.5,
        "prep_time_mins": 20,
        "ingredients": [
            "6oz Wild Salmon Filet",
            "1/2 cup Cooked Quinoa",
            "1 cup Steamed Broccoli",
            "1 tbsp Extra Virgin Olive Oil",
            "Fresh Lemon Juice",
            "Garlic Powder"
        ],
        "instructions": "Bake salmon at 400°F for 12-15 mins. Toss warm quinoa with olive oil, lemon juice, and garlic. Serve with steamed broccoli.",
        "tags": ["heart-healthy", "low-sodium", "diabetic-friendly", "mediterranean"],
        "suitable_for": ["Type 2 Diabetes", "Post-Angioplasty", "Post-CABG"]
    },
    {
        "id": "recipe-tuscan-bean-soup",
        "title": "Tuscan White Bean & Kale Soup",
        "sodium_mg": 340,
        "glycemic_index": 28,
        "net_carbs_g": 26,
        "fiber_g": 9,
        "saturated_fat_g": 0.5,
        "prep_time_mins": 25,
        "ingredients": [
            "1 can Low-Sodium Cannellini Beans",
            "2 cups Chopped Lacinato Kale",
            "1/2 Diced Yellow Onion",
            "2 cloves Minced Garlic",
            "3 cups Low-Sodium Vegetable Broth",
            "1 tbsp Extra Virgin Olive Oil"
        ],
        "instructions": "Sauté onion and garlic in olive oil until soft. Add broth, beans, and kale. Simmer for 15 minutes until kale is tender.",
        "tags": ["vegan", "high-fiber", "low-sodium", "cardiac-safe"],
        "suitable_for": ["Type 2 Diabetes", "Post-Angioplasty", "Post-CABG"]
    },
    {
        "id": "recipe-moong-palak-cheela",
        "title": "Moong Dal & Palak Cheela (Lentil Spinach Pancakes)",
        "sodium_mg": 180,
        "glycemic_index": 28,
        "net_carbs_g": 16,
        "fiber_g": 7,
        "saturated_fat_g": 0.5,
        "prep_time_mins": 15,
        "ingredients": [
            "1 cup Soaked Yellow Moong Dal",
            "1 cup Chopped Fresh Palak (Spinach)",
            "1/2 inch Grated Ginger",
            "1 Green Chili chopped",
            "1/2 tsp Cumin seeds (Jeera)",
            "Pinch of Haldi (Turmeric)",
            "1 tsp Cold-Pressed Mustard Oil"
        ],
        "instructions": "Grind soaked moong dal with ginger and green chili into a smooth batter. Stir in chopped palak, cumin, and turmeric. Pour batter thinly onto a heated non-stick tawa with minimal oil and cook both sides until golden.",
        "tags": ["indian", "diabetic-friendly", "high-fiber", "low-gi", "breakfast"],
        "suitable_for": ["Type 2 Diabetes", "Post-Angioplasty", "Post-CABG"]
    },
    {
        "id": "recipe-lauki-chana-dal",
        "title": "Lauki & Chana Dal Stew (Bottle Gourd with Bengal Gram)",
        "sodium_mg": 240,
        "glycemic_index": 25,
        "net_carbs_g": 18,
        "fiber_g": 8,
        "saturated_fat_g": 0.8,
        "prep_time_mins": 25,
        "ingredients": [
            "2 cups Diced Lauki (Bottle Gourd)",
            "1/2 cup Soaked Chana Dal",
            "1 Ripe Tomato diced",
            "1/2 tsp Jeera (Cumin)",
            "1/2 tsp Haldi (Turmeric)",
            "1/2 tsp Coriander Powder",
            "1 tsp Cow Ghee"
        ],
        "instructions": "Pressure cook diced lauki and soaked chana dal with turmeric and 1.5 cups water for 3 whistles. In a small pan, heat ghee, add cumin seeds and tomatoes. Combine with cooked dal-lauki and simmer for 5 minutes.",
        "tags": ["indian", "heart-healthy", "low-sodium", "sattvic", "lunch"],
        "suitable_for": ["Type 2 Diabetes", "Post-Angioplasty", "Post-CABG"]
    },
    {
        "id": "recipe-methi-oats-khichdi",
        "title": "Methi Oats & Moong Khichdi (Fenugreek Porridge)",
        "sodium_mg": 210,
        "glycemic_index": 32,
        "net_carbs_g": 20,
        "fiber_g": 6,
        "saturated_fat_g": 0.6,
        "prep_time_mins": 20,
        "ingredients": [
            "1 cup Rolled Oats",
            "1/2 cup Split Yellow Moong Dal",
            "1 cup Fresh Methi (Fenugreek) Leaves",
            "1/2 tsp Cumin Seeds",
            "1/2 tsp Turmeric",
            "1 tsp Extra Virgin Olive Oil or Ghee"
        ],
        "instructions": "Sauté cumin and washed fresh methi leaves in oil for 2 mins until wilted. Add oats, moong dal, turmeric, and 3 cups water. Simmer on medium heat for 12-15 mins until thick and creamy.",
        "tags": ["indian", "diabetic-friendly", "comfort-food", "low-gi", "dinner"],
        "suitable_for": ["Type 2 Diabetes", "Post-Angioplasty", "Post-CABG"]
    },
    {
        "id": "recipe-karela-baingan-masala",
        "title": "Karela & Baingan Dry Sabzi (Bitter Gourd & Eggplant)",
        "sodium_mg": 150,
        "glycemic_index": 15,
        "net_carbs_g": 9,
        "fiber_g": 5,
        "saturated_fat_g": 0.4,
        "prep_time_mins": 20,
        "ingredients": [
            "2 Medium Karela (Bitter Gourd) thinly sliced",
            "1 cup Diced Baingan (Eggplant)",
            "1/2 tsp Mustard Seeds (Rai)",
            "1/2 tsp Turmeric",
            "1/2 tsp Amchur (Dry Mango Powder)",
            "1 tbsp Cold-Pressed Mustard Oil"
        ],
        "instructions": "Heat mustard oil in a kadai, pop mustard seeds, then add karela and baingan slices. Sprinkle turmeric and amchur. Cover and cook on low heat until tender and crisp.",
        "tags": ["indian", "hypoglycemic", "low-sodium", "cardiac-safe", "side-dish"],
        "suitable_for": ["Type 2 Diabetes", "Post-Angioplasty", "Post-CABG"]
    }
]


def seed_database():
    print(f"Connecting to Firestore for project: '{PROJECT_ID}'...")
    db = firestore.Client(project=PROJECT_ID)
    collection_ref = db.collection("recipes")

    for recipe in SEED_RECIPES:
        doc_id = recipe["id"]
        doc_ref = collection_ref.document(doc_id)
        doc_ref.set(recipe)
        print(f"  ✓ Seeded recipe '{doc_id}': {recipe['title']}")

    print("Firestore database updated with Indian market recipes successfully!")


if __name__ == "__main__":
    seed_database()
