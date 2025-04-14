import csv
import time
import re
from tqdm import tqdm
import ollama

client = ollama.Client()

# === CONFIGURATION ===
INPUT_PATH = 'your_input.csv'
OUTPUT_PATH = 'cleaned_wine_output.csv'
MAX_RETRIES = 10
MODEL = "llama2:7b"

# Map: column name → 0-based index in the CSV
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

# Regex-aware field matching
def parse_response(response, field_keys):
    """
    Parses a string response and returns a dict of field_name -> value.
    Accepts multiple delimiter formats like ':', '-', or even implicit listings.
    """
    result = {k: "" for k in field_keys}
    lines = response.splitlines()

    for line in lines:
        for field in field_keys:
            pattern = rf"{field}\s*[:\-–]\s*(.+)"
            match = re.match(pattern, line.strip(), re.IGNORECASE)
            if match:
                result[field] = match.group(1).strip()
    return result

# Prompt for all wine fields at once
def build_prompt(wine_name):
    return (
        f"Provide the following metadata for the wine '{wine_name}':\n"
        "- Winery:\n- Grapes:\n- Region:\n- Wine Style:\n"
        "- Volume (e.g. 750):\n- Volume Unit (e.g. ml):\n- Type (e.g. red):\n"
        "- Ageing:\n- Seasons:\n- Soil Type:\n- Vintage:\n- Tasting Notes:\n"
    )

# LLM call with retries
def generate_metadata(wine_name):
    prompt = build_prompt(wine_name)
    for attempt in range(MAX_RETRIES):
        try:
            response = client.generate(model=MODEL, prompt=prompt).get("response", "").strip()
            if response:
                return parse_response(response, wine_fields.keys())
        except Exception as e:
            print(f"⚠️ Retry {attempt + 1} for '{wine_name}' failed: {e}")
            time.sleep(1)
    return {k: "" for k in wine_fields.keys()}

# === Load CSV ===
with open(INPUT_PATH, 'r', encoding='utf-8-sig') as infile:
    reader = list(csv.reader(infile))
    header, rows = reader[0], reader[1:]

updated_rows = [header]

# === Process Each Row ===
for row in tqdm(rows, desc="Cleaning wine metadata"):
    wine_name = row[0].strip()

    # Find missing fields
    missing_fields = [field for field, idx in wine_fields.items()
                      if idx >= len(row) or not row[idx].strip()]

    if missing_fields:
        metadata = generate_metadata(wine_name)

        for field in missing_fields:
            idx = wine_fields[field]
            if idx >= len(row):
                row.extend([""] * (idx + 1 - len(row)))
            row[idx] = metadata.get(field, "")

    updated_rows.append(row)

# === Write Output ===
with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8-sig') as outfile:
    writer = csv.writer(outfile)
    writer.writerows(updated_rows)

print("✅ Wine cleaning complete! Output saved to:", OUTPUT_PATH)
