import csv
import time
from tqdm import tqdm
import ollama

client = ollama.Client()

# === CONFIGURATION ===
INPUT_PATH = 'your_input.csv'
OUTPUT_PATH = 'cleaned_wine_output.csv'
MAX_RETRIES = 10

# Map of column name to its index
wine_fields = {
    'Winery': 3,
    'Grapes': 4,
    'Region': 5,
    'Wine Style': 6,
    'Volume': 8,
    'Volume Unit': 9,
    'Type': 10,
    'Ageing': 11,
    'Seasons': 12,
    'Soil Type': 13,
    'Vintage': 14,
    'Tasting Notes': 15
}

# === Retry LLM call ===
def generate_with_retries(prompt):
    for attempt in range(MAX_RETRIES):
        try:
            res = client.generate(model='llama2:7b', prompt=prompt).get("response", "").strip()
            if res:
                return res
        except Exception as e:
            print(f"Retry {attempt+1} failed: {e}")
            time.sleep(1)
    return ""

# === Clean and Infer Missing Wine Fields ===
with open(INPUT_PATH, 'r', encoding='utf-8-sig') as infile:
    reader = list(csv.reader(infile))
    header, rows = reader[0], reader[1:]

updated_rows = [header]

for row in tqdm(rows, desc="Cleaning wine metadata"):
    wine_name = row[0]
    for field, idx in wine_fields.items():
        if idx >= len(row) or not row[idx].strip():
            prompt = f"Given this wine name: {wine_name}, generate {field.lower()}."
            value = generate_with_retries(prompt)
            if idx >= len(row):
                row.extend([""] * (idx + 1 - len(row)))
            row[idx] = value
    updated_rows.append(row)

with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8-sig') as outfile:
    writer = csv.writer(outfile)
    writer.writerows(updated_rows)

print("✅ Wine cleaning complete! Saved to:", OUTPUT_PATH)
