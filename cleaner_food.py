import csv
import time
from tqdm import tqdm
import ollama

client = ollama.Client()
INPUT_PATH = 'cleaned_wine_output.csv'
OUTPUT_PATH = 'cleaned_food_output.csv'
MAX_RETRIES = 10

# Index mapping
food_columns = {
    1: {'name_col': 17, 'fields': list(range(18, 25 + 1))},
    2: {'name_col': 26, 'fields': list(range(27, 34 + 1))},
    3: {'name_col': 35, 'fields': list(range(36, 43 + 1))}
}

# Field prompts (modular per food)
field_prompts = {
    0: "grape and food type",
    1: "tasting notes",
    2: "food and wine acidity",
    3: "regional pairing",
    4: "sweetness and spiciness",
    5: "food type",
    6: "food course"
}

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

with open(INPUT_PATH, 'r', encoding='utf-8-sig') as infile:
    reader = list(csv.reader(infile))
    header, rows = reader[0], reader[1:]

updated_rows = [header]

for row in tqdm(rows, desc="Cleaning food details"):
    for food_num, config in food_columns.items():
        name_idx = config['name_col']
        field_indices = config['fields']
        if name_idx >= len(row): continue
        food_name = row[name_idx].strip()
        if not food_name: continue

        for i, field_idx in enumerate(field_indices):
            if field_idx >= len(row) or not row[field_idx].strip():
                field_label = field_prompts.get(i % 7)
                if field_label:
                    prompt = f"Given this dish: {food_name}, generate {field_label}."
                    result = generate_with_retries(prompt)
                    if field_idx >= len(row):
                        row.extend([""] * (field_idx + 1 - len(row)))
                    row[field_idx] = result
    updated_rows.append(row)

with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8-sig') as outfile:
    writer = csv.writer(outfile)
    writer.writerows(updated_rows)

print("✅ Food detail cleaning complete! Saved to:", OUTPUT_PATH)
