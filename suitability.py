import csv
import time
from tqdm import tqdm
import ollama

client = ollama.Client()

INPUT_PATH = 'cleaned_food_output.csv'     # <-- Update if needed
OUTPUT_PATH = 'with_suitability_classification.csv'
MAX_RETRIES = 5

# Mapping: food column index -> suitability column index
food_suitability_map = {
    16: 17,   # Food 1 -> Suitability 1
    25: 26,   # Food 2 -> Suitability 2
    34: 35    # Food 3 -> Suitability 3
}

def classify_suitability(wine, food):
    prompt = (
        f"Given the wine \"{wine}\" and the dish \"{food}\", classify this pairing as one of the following:\n"
        "Highly Suitable, Moderately Suitable, or Less Suitable.\n"
        "Only return the classification label."
    )
    for _ in range(MAX_RETRIES):
        try:
            response = client.generate(model='llama2:7b', prompt=prompt).get("response", "").strip()
            if response:
                return response
        except Exception as e:
            print(f"Retry due to error: {e}")
            time.sleep(1)
    return ""

# === Read Input CSV ===
with open(INPUT_PATH, 'r', encoding='utf-8-sig') as infile:
    reader = list(csv.reader(infile))
    header, rows = reader[0], reader[1:]

# Pad header if necessary
while len(header) <= 35:
    header.append("")

updated_rows = [header]

# === Process Rows ===
for row in tqdm(rows, desc="Classifying suitability"):
    wine = row[0].strip()

    for food_col, suit_col in food_suitability_map.items():
        # Ensure row has enough columns
        while len(row) <= suit_col:
            row.append("")

        food = row[food_col].strip() if food_col < len(row) else ""
        current_value = row[suit_col].strip() if suit_col < len(row) else ""

        # Generate only if wine+food exists and suitability is missing
        if wine and food and not current_value:
            label = classify_suitability(wine, food)
            row[suit_col] = label

    updated_rows.append(row)

# === Write Output CSV ===
with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8-sig') as outfile:
    writer = csv.writer(outfile)
    writer.writerows(updated_rows)

print("✅ Classification done! Output saved to:", OUTPUT_PATH)
