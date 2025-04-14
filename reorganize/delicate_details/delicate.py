import ollama
import csv
import time

client = ollama.Client()
model = "llama2:7b"

# === Prompt Template ===
prompt_template = (
    "For the wine '{wine_name}', please return the following metadata:\n"
    "- Soil_type (e.g., limestone, clay, gravel, granite, volcanic)\n"
    "- Vintage (four-digit year)\n"
    "- Tasting_notes (e.g., citrus, floral, crisp acidity)\n\n"
    "Provide only the 3 labeled fields exactly as shown. No extra text."
)

# === Metadata Fields to Extract ===
meta_fields = ['soil_type', 'vintage', 'tasting_notes']

# === File Paths ===
input_file = r"C:\Users\User\Desktop\Uni\Career\WS\data\vine_wine\Vine Wine Ltd - Wine to Food Recommendations  - food_suggestions_new.csv"
output_file = r"C:\Users\User\Desktop\Uni\Career\WS\MAIN\vine_wine\vinewine\delicate_details\delicate.csv"

# === Limit for Rows to Process ===
row_limit = 10  # Set to None for full run

# === Parse model response into a metadata dictionary ===
def parse_metadata(response):
    metadata = {field: "" for field in meta_fields}
    for line in response.splitlines():
        if ':' in line:
            key, val = line.split(':', 1)
            key_clean = key.strip().lower()
            val = val.strip()
            if key_clean in metadata:
                metadata[key_clean] = val
    return metadata

# === Retry Wrapper ===
def get_model_response(wine_name, max_retries=10, delay=1):
    for attempt in range(1, max_retries + 1):
        try:
            prompt = prompt_template.format(wine_name=wine_name)
            response = client.generate(model=model, prompt=prompt).get('response', '').strip()
            if all(f + ':' in response.lower() for f in meta_fields):  # crude check
                return response
        except Exception as e:
            print(f"⚠️ Error on attempt {attempt} for '{wine_name}':", e)
        time.sleep(delay)
    print(f"❌ Failed to get valid response for '{wine_name}' after {max_retries} attempts.")
    return ""

# === Load Input CSV ===
with open(input_file, mode='r', newline='', encoding='utf-8-sig') as infile:
    reader = list(csv.reader(infile))
    header = reader[0]
    rows = reader[1:]

# === Add metadata columns if not already present ===
for field in meta_fields:
    if field not in header:
        header.append(field)

processed_rows = [header]

# === Process Rows ===
for i, row in enumerate(rows):
    if row_limit and i >= row_limit:
        break

    wine_name = row[0]
    print(f"🍷 [{i+1}] Processing: {wine_name}")

    response = get_model_response(wine_name)
    metadata = parse_metadata(response)
    meta_values = [metadata.get(field, "") for field in meta_fields]
    
    # Ensure the row is long enough before extending it
    full_row = row + [""] * (len(header) - len(row))  # pad if short
    for idx, value in enumerate(meta_values):
        full_row[13 + idx] = value  # [0] → [13], [14], [15]

    processed_rows.append(full_row)

# === Write to Output CSV ===
with open(output_file, mode='w', newline='', encoding='utf-8-sig') as outfile:
    writer = csv.writer(outfile)
    writer.writerows(processed_rows)

print("✅ Done! Metadata saved to:", output_file)
