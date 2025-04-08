import csv
import time
import requests
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from tqdm import tqdm

# === Setup Selenium ===
chrome_options = Options()
# chrome_options.add_argument("--headless")  # Remove this to see the browser
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920x1080")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# === Config ===
wine_links = []
wine_data = []
MAX_RETRIES = 3

# Create image folder -- images downloaded locally
os.makedirs("images_bordeaux", exist_ok=True)

# === Category List ===
product_categories = [
    "bordeaux"
]
seen_links = set()


# === Step 1: Navigate and bypass age gate once ===
def handle_age_gate():
    try:
        yes_button = driver.find_element(By.CSS_SELECTOR, 'button[data-submit="yes"]')
        yes_button.click()
        print("✅ Age gate bypassed")
        time.sleep(2)  # Wait for redirection
    except NoSuchElementException:
        print("🔓 No age gate detected")

def download_image(image_url, wine_name):
    try:
        # Sanitize file name (no spaces/symbols)
        file_name = f"{wine_name.strip().replace(' ', '_').replace('/', '_')}.jpg"
        image_path = os.path.join("images", file_name)

        response = requests.get(image_url)
        with open(image_path, "wb") as f:
            f.write(response.content)

        return image_path  # to store in CSV
    except Exception as e:
        print(f"❌ Failed to download image from {image_url}: {e}")
        return ""

# === Step 2: Loop through categories and collect product links ===
for category in product_categories:
    print(f"\n🔎 Scraping category: {category}")

    # Load first page to detect pagination count
    driver.get(f"https://vinewineltd.com/shop/?yith_wcan=1&product_cat={category}")
    time.sleep(3)
    handle_age_gate()

    max_pages = 1
    try:
        pagination = driver.find_elements(By.CSS_SELECTOR, "ul.page-numbers li a.page-numbers")
        page_numbers = [int(p.text) for p in pagination if p.text.isdigit()]
        if page_numbers:
            max_pages = max(page_numbers)
        print(f"📌 Found {max_pages} pages for category: {category}")
    except Exception as e:
        print(f"⚠️ Could not detect page count for {category}. Defaulting to 1. Error: {e}")

    for page in range(1, max_pages + 1):
        if page == 1:
            url = f"https://vinewineltd.com/shop/?yith_wcan=1&product_cat={category}"
        else:
            url = f"https://vinewineltd.com/shop/page/{page}/?yith_wcan=1&product_cat={category}"

        print(f"📄 Loading page {url}")
        driver.get(url)
        time.sleep(3)
        handle_age_gate()

        product_elements = driver.find_elements(By.CSS_SELECTOR, "h2.woocommerce-loop-product__title")
        if not product_elements:
            print("⚠️ No products found on this page.")
            break

        for product in product_elements:
            try:
                link = product.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                if link not in seen_links:
                    wine_links.append(link)
                    seen_links.add(link)
            except:
                print("⚠️ Skipping product with missing link.")


# === Step 3: Visit each product page ===
def get_summary(driver):
    """Returns the summary section element."""
    try:
        return driver.find_element(By.CSS_SELECTOR, "div.summary")
    except NoSuchElementException:
        print("❌ Summary section not found.")
        return None

def get_wine_name(summary):
    try:
        return summary.find_element(By.CSS_SELECTOR, "h1.product_title").text
    except NoSuchElementException:
        return ""

def get_wine_price(summary):
    try:
        # First try discounted price
        return summary.find_element(By.CSS_SELECTOR, "ins span.woocommerce-Price-amount > bdi").text
    except NoSuchElementException:
        try:
            return summary.find_element(By.CSS_SELECTOR, "span.woocommerce-Price-amount > bdi").text
        except NoSuchElementException:
            return ""

def get_image_url(driver):
    try:
        return driver.find_element(By.CSS_SELECTOR, "img.zoomImg").get_attribute("src")
    except NoSuchElementException:
        try:
            return driver.find_element(By.CSS_SELECTOR, 'img[role="presentation"]').get_attribute("src")
        except NoSuchElementException:
            return ""

def get_short_description(driver):
    try:
        container = driver.find_element(By.CSS_SELECTOR, "div.woocommerce-product-details__short-description")
        all_lines = []

        # First, handle divs like <div class="ewa-rteLine">Key: Value</div>
        div_lines = container.find_elements(By.CSS_SELECTOR, "div.ewa-rteLine")
        if div_lines:
            for div in div_lines:
                text = div.text.strip()
                if text and ":" in text:
                    all_lines.append(text)

        # Fallback to previous <p><span><span> or <p><br> methods
        if not all_lines:
            # Try nested spans
            span_spans = container.find_elements(By.CSS_SELECTOR, "p span span")
            for span in span_spans:
                text = span.text.strip()
                if text and text != "\xa0":
                    all_lines.append(text)

            if not all_lines:
                p_tags = container.find_elements(By.TAG_NAME, "p")
                for p in p_tags:
                    html = p.get_attribute("innerHTML").strip()
                    if not html or html == "&nbsp;":
                        continue
                    lines = [line.strip().strip('"') for line in html.split('<br>') if line.strip()]
                    all_lines.extend(lines)

        # Define keys
        winery_keys = {"winery", "winer", "wineries"}
        grapes_keys = {"grapes", "grape", "grape variety"}
        region_keys = {"region"}
        wine_style_keys = {"wine style"}

        winery = grapes = region = wine_style = ""
        for line in all_lines:
            line = line.replace("：", ":")  # Normalize colon
            if ":" not in line:
                continue

            key_part, value = line.split(":", 1)
            key = key_part.strip().lower()
            value = value.strip()

            if key in winery_keys:
                winery = value
            elif key in grapes_keys:
                grapes = value
            elif key in region_keys:
                region = value
            elif key in wine_style_keys:
                wine_style = value

        return winery, grapes, region, wine_style
    except Exception as e:
        print(f"❌ Failed to extract short description: {e}")
        return "", "", "", ""

# === Main Scraping Loop ===
for wine_url in tqdm(wine_links, desc="🍷 Scraping wines", unit="wine"):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            driver.get(wine_url)
            time.sleep(1)

            summary = get_summary(driver)
            if not summary:
                raise Exception("Summary not found")

            name = get_wine_name(summary)
            price = get_wine_price(summary)
            image_url = get_image_url(driver)
            image_path = download_image(image_url, name)
            winery, grapes, region, wine_style = get_short_description(driver)

            wine_data.append({
                "Name": name,
                "Price": price,
                "Image": image_path,
                "Winery": winery,
                "Grapes": grapes,
                "Region": region,
                "Wine Style": wine_style,
                "Product URL": wine_url
            })

            break  # Break out of retry loop if successful

        except Exception as e:
            print(f"⚠️ Attempt {attempt} failed for {wine_url}: {e}")
            time.sleep(2)

            if attempt == MAX_RETRIES:
                print(f"❌ Giving up on {wine_url} after {MAX_RETRIES} attempts.")


# === Step 4: Save to CSV ===
if wine_data:
    with open("selenium_wines_output_bordeaux.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=wine_data[0].keys())
        writer.writeheader()
        writer.writerows(wine_data)

    print("\n✅ All done! Data saved to selenium_wines_output.csv")
else:
    print("⚠️ No data scraped.")

# === Cleanup ===
driver.quit()
