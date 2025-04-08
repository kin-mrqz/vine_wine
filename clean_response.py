import ollama
import csv
import re

client = ollama.Client()

model = "llama"
prompt_template = "I have this fine wine {wine_name}, what food would you recommend pairing it with, and why?"

input_file = r"C:\\Users\\user\\Desktop\\user1\\wine_responses_raw.csv"
output_file = r"C:\\Users\\user\\Desktop\\user1\\wine_responses_cleaned.csv"

RESPONSE_COL_INDEX = 8  # Index where raw LLM response is located

manual_header = [
    'Wine Name', 'Price', 'Image', 'Winery', 'Grapes', 'Region', 'Wine Style', 'Product URL',
    'Food 1', 'Grape and Food Type 1', 'Tasting Notes 1', 'Food & Wine Acidity 1', 'Regional Pairing 1', 'Sweetness & Spiciness 1',
    'Food 2', 'Grape and Food Type 2', 'Tasting Notes 2', 'Food & Wine Acidity 2', 'Regional Pairing 2', 'Sweetness & Spiciness 2',
    'Food 3', 'Grape and Food Type 3', 'Tasting Notes 3', 'Food & Wine Acidity 3', 'Regional Pairing 3', 'Sweetness & Spiciness 3'
]

def assign_by_category(sections, category, value):
    lower = category.lower()
    if "grape" in lower or "variet" in lower or "wine type" in lower:
        sections['grape_type'] = value
    elif "tasting" in lower or "note" in lower:
        sections['tasting'] = value
    elif "acidity" in lower:
        sections['acidity'] = value
    elif "region" in lower:
        sections['region'] = value
    elif "sweet" in lower or "spice" in lower:
        sections['sweetness'] = value
    return sections

def parse_response(response):
    food_data = []
    entries = re.split(r'\n\s*\d+\.\s+', response)
    for entry in entries[1:]:
        lines = [line.strip() for line in entry.split('\n') if line.strip()]
        if not lines:
            continue

        sections = {
            'food': '',
            'grape_type': '',
            'tasting': '',
            'acidity': '',
            'region': '',
            'sweetness': ''
        }

        first_line = lines[0]
        if " - " in first_line and ":" in first_line:
            food_part, rest = first_line.split(" - ", 1)
            category, detail = rest.split(":", 1)
            sections['food'] = food_part.strip()
            sections = assign_by_category(sections, category.strip(), detail.strip())
        else:
            sections['food'] = first_line.strip()

        for line in lines[1:]:
            if ':' in line:
                category, detail = line.split(":", 1)
                sections = assign_by_category(sections, category.strip(), detail.strip())

        food_data.append(sections)
    return food_data

def generate_response(wine):
    prompt = prompt_template.format(wine_name=wine)
    try:
        response = client.generate(model=model, prompt=prompt).get('response', '')
        return response
    except Exception as e:
        print(f"⚠️ Error generating for wine '{wine}': {e}")
        return ''

def parse_and_package(resp):
    parsed = parse_response(resp)
    new_data = []
    for food in parsed[:3]:
        new_data.extend([
            food['food'],
            food['grape_type'],
            food['tasting'],
            food['acidity'],
            food['region'],
            food['sweetness']
        ])
    while len(new_data) < 18:
        new_data.append("")
    return new_data

# === Read Input CSV ===
with open(input_file, mode='r', newline='', encoding='utf-8') as infile:
    reader = list(csv.reader(infile))
    rows = reader

processed_rows = [manual_header]

for idx, row in enumerate(rows[1:]):  # Skip header
    wine = row[0]
    original_data = row[:8]  # First 8 columns
    response = row[RESPONSE_COL_INDEX] if len(row) > RESPONSE_COL_INDEX else ""

    attempt = 0
    success = False
    while attempt < 3:
        new_data = parse_and_package(response)
        if any(new_data[::6]):  # Check if any food name exists
            success = True
            break
        attempt += 1
        print(f"🔁 Attempt {attempt + 1}/3 for '{wine}' (previous attempt failed)")
        response = generate_response(wine)

    if success:
        processed_rows.append(original_data + new_data)
    else:
        print(f"❌ Skipped '{wine}' after 3 failed attempts")

# === Write Cleaned Output ===
with open(output_file, mode='w', newline='', encoding='utf-8-sig') as outfile:
    writer = csv.writer(outfile)
    writer.writerows(processed_rows)

print(f"✅ Final cleaned file saved to: {output_file}")
