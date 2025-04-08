import ollama
import csv
import re
import copy

client = ollama.Client()

model = "llama"
prompt_template = "I have this fine wine {wine_name}, what food would you recommend pairing it with, and why?"

input_file = r"C:\\Users\\user\\Desktop\\user1\\list_of_wines.csv"
output_file = r"C:\\Users\\user\\Desktop\\user1\\list_of_wines_with_pairings.csv"

columns = [
    'Wine Name',
    'Food 1', 'Grape and Food Type 1', 'Tasting Notes 1', 'Food & Wine Acidity 1', 'Regional Pairing 1', 'Sweetness & Spiciness 1',
    'Food 2', 'Grape and Food Type 2', 'Tasting Notes 2', 'Food & Wine Acidity 2', 'Regional Pairing 2', 'Sweetness & Spiciness 2',
    'Food 3', 'Grape and Food Type 3', 'Tasting Notes 3', 'Food & Wine Acidity 3', 'Regional Pairing 3', 'Sweetness & Spiciness 3'
]

def parse_response(response):
    food_data = []
    entries = re.split(r'\n\s*\d+\.\s+', response)
    for entry in entries[1:]:
        lines = [line.strip() for line in entry.split('\n') if line.strip()]
        if not lines:
            continue
        food = lines[0]
        sections = {
            'food': food,
            'grape_type': '',
            'tasting': '',
            'acidity': '',
            'region': '',
            'sweetness': ''
        }
        for line in lines[1:]:
            lower = line.lower()
            if "grape" in lower or "variet" in lower or "wine type" in lower:
                sections['grape_type'] = line.split(':', 1)[-1].strip()
            elif "tasting" in lower or "note" in lower:
                sections['tasting'] = line.split(':', 1)[-1].strip()
            elif "acidity" in lower:
                sections['acidity'] = line.split(':', 1)[-1].strip()
            elif "region" in lower:
                sections['region'] = line.split(':', 1)[-1].strip()
            elif "sweet" in lower or "spice" in lower:
                sections['sweetness'] = line.split(':', 1)[-1].strip()
        food_data.append(sections)
    return food_data

# === Load and Copy Input CSV ===
with open(input_file, mode='r', newline='', encoding='utf-8') as infile:
    reader = list(csv.reader(infile))
    data_copy = copy.deepcopy(reader)

# === Process and Extend Rows ===
header = data_copy[0] if any("Wine Name" in cell for cell in data_copy[0]) else ["Wine Name"]
extended_header = header + columns[1:]  # Use original header + new columns if needed

processed_rows = [extended_header]

for i, row in enumerate(data_copy[1:]):  # Skip header
    wine = row[0]
    prompt = prompt_template.format(wine_name=wine)
    response = client.generate(model=model, prompt=prompt).get('response', '')
    parsed = parse_response(response)

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
    while len(new_data) < len(columns) - 1:
        new_data.append("")

    full_row = row + new_data
    processed_rows.append(full_row)

# === Write to New Output CSV ===
with open(output_file, mode='w', newline='', encoding='utf-8-sig') as outfile:
    writer = csv.writer(outfile)
    writer.writerows(processed_rows)

print("✅ Done! Output saved to:", output_file)
