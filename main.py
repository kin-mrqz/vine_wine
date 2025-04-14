import csv
import re
import time
import copy
import ollama
from tqdm import tqdm

# === CONFIGURATION ===
MODEL_NAME = "llama2:7b"
INPUT_FILE = r"C:\Users\admin\Desktop\user\vinewine\old site\old_selenium_wines_output.csv"
OUTPUT_FILE = r"C:\Users\admin\Desktop\user\vinewine\old site\combined_model_output.csv"
MAX_RETRIES = 3

# === INIT OLLAMA CLIENT ===
client = ollama.Client()

# === COLUMN HEADERS ===
base_columns = [
    'Wine Name', 'Price', 'Image', 'Winery', 'Grapes', 'Region', 'Wine Style', 'Product URL'
]

wine_fields = [
    'volume', 'volume_unit', 'type', 'ageing', 'seasons',
    'food_type', 'course', 'soil_type', 'vintage', 'tasting_notes'
]

# Per food pairing fields (x3)
food_fields = [
    'Food', 'Grape and Food Type', 'Tasting Notes',
    'Food & Wine Acidity', 'Regional Pairing', 'Sweetness & Spiciness'
]
columns = base_columns + wine_fields + [
    f"{field} {i}" for i in range(1, 4) for field in food_fields
]

# === PARSE LLM RESPONSE ===
def parse_response(response):
    wine_data = {}
    food_data = []

    # Extract wine metadata
    for field in wine_fields:
        pattern = fr"{field}:\s*(.*)"
        match = re.search(pattern, response, re.IGNORECASE)
        wine_data[field] = match.group(1).strip() if match else ""

    # Extract food pairings
    pairings = re.split(r"\n\s*\d+\.\s+", response)
    if len(pairings) > 1:
        for block in pairings[1:]:
            lines = [line.strip() for line in block.strip().split('\n') if line.strip()]
            if not lines:
                continue
            entry = {
                'Food': lines[0],
                'Grape and Food Type': '',
                'Tasting Notes': '',
                'Food & Wine Acidity': '',
                'Regional Pairing': '',
                'Sweetness & Spiciness': ''
            }
            for line in lines[1:]:
                for key in entry.keys():
                    if key.lower() in line.lower():
                        entry[key] = line.split(":", 1)[-1].strip()
            food_data.append(entry)
    return wine_data, food_data

# === GENERATE RESPONSE WITH RETRIES ===
def generate_with_retries(prompt):
    for attempt in range(MAX_RETRIES):
        try:
            response = client.generate(model=MODEL_NAME, prompt=prompt).get('response', '')
            if response.strip():
                return response
        except Exception as e:
            print(f"⚠️ Attempt {attempt+1} failed: {e}")
            time.sleep(1)
    return ""

# === LOAD INPUT CSV ===
with open(INPUT_FILE, mode='r', newline='', encoding='utf-8-sig') as infile:
    reader = list(csv.reader(infile))
    data_copy = copy.deepcopy(reader)

header = data_copy[0]
rows = data_copy[1:]

# === PROCESS EACH WINE ===
processed_rows = [columns]

for row in tqdm(rows, desc="Processing wines"):
    wine_name = row[0]
    prompt = wine_name

    response = generate_with_retries(prompt)
    if not response:
        print(f"❌ Failed to generate for: {wine_name}")
        processed_rows.append(row + [""] * (len(columns) - len(row)))
        continue

    wine_meta, food_entries = parse_response(response)
    flat_data = [wine_meta.get(field, '') for field in wine_fields]

    for i in range(3):
        if i < len(food_entries):
            entry = food_entries[i]
            flat_data.extend([entry.get(f, '') for f in food_fields])
        else:
            flat_data.extend([""] * len(food_fields))

    # Fill base columns if missing
    base_row = row + [""] * (len(base_columns) - len(row))
    full_row = base_row + flat_data
    processed_rows.append(full_row)

# === WRITE OUTPUT CSV ===
with open(OUTPUT_FILE, mode='w', newline='', encoding='utf-8-sig') as outfile:
    writer = csv.writer(outfile)
    writer.writerows(processed_rows)

print("✅ All done! Output saved to:", OUTPUT_FILE)
