import re
import csv
import time
from tqdm import tqdm
import ollama

client = ollama.Client()
INPUT_FILE = 'main_wine_output.csv'
OUTPUT_FILE = 'cleaner_food_output.csv'
MAX_RETRIES = 10

# 0-based indexing: Food name column → related column indices for subfields
FOOD_BLOCKS = {
    16: list(range(17, 25)),  # Food 1 block
    25: list(range(26, 34)),  # Food 2 block
    34: list(range(35, 43))   # Food 3 block
}

FIELD_NAMES = [
    "Grape and Food Type", "Tasting Notes", "Food & Wine Acidity",
    "Regional Pairing", "Sweetness & Spiciness", "Food Type", "Course"
]

def get_prompt(food_name, field):
    return f"Given the dish \"{food_name}\", generate its {field}."

def extract_field(response, target_label):
    """Use regex to extract response line that starts with target label and grab text after ':' or '-'"""
    pattern = rf"{target_label}\s*[:\-–]\s*(.+)"
    match = re.search(pattern, response, re.IGNORECASE)
    return match.group(1).strip() if match else ""

def generate_all_fields(food_name):
    fields = []
    for field in FIELD_NAMES:
        prompt = get_prompt(food_name, field)
        for _ in range(MAX_RETRIES):
            try:
                res = client.generate(model='llama2:7b', prompt=prompt)
                text = res.get('response', '').strip()
                if text:
                    value = extract_field(text, field)
                    fields.append(value or text)
                    break
            except:
                time.sleep(1)
        else:
            fields.append("")
    return fields

# === Load CSV ===
with open(INPUT_FILE, 'r', encoding='utf-8-sig') as f:
    reader = list(csv.reader(f))
    header, rows = reader[0], reader[1:]

# === Process Rows ===
for row in tqdm(rows, desc="Cleaning food fields"):
    for food_col, field_indices in FOOD_BLOCKS.items():
        food_name = row[food_col].strip() if food_col < len(row) else ""
        if not food_name:
            continue

        # If any of the target cols are empty, regenerate the full block
        needs_generation = any(
            col >= len(row) or not row[col].strip() for col in field_indices
        )

        if needs_generation:
            generated = generate_all_fields(food_name)
            for j, gen_val in enumerate(generated):
                dest_idx = field_indices[j]
                if len(row) <= dest_idx:
                    row.extend([""] * (dest_idx + 1 - len(row)))
                row[dest_idx] = gen_val

# === Save Output ===
with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(rows)

print("✅ Cleaner food details saved to:", OUTPUT_FILE)
