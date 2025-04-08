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

# === Setup Selenium ===
chrome_options = Options()
chrome_options.add_argument("--headless")  # Remove this to see the browser
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920x1080")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# === Config ===
base_url = "https://vinewine.shoplineapp.com/products?page={}&sort_by=&order_by=&limit=72"
pages_to_scrape = 9
wine_links = []
wine_data = []

# Create image folder -- images downloaded locally
os.makedirs("images", exist_ok=True)

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

def get_shopline_price(driver):
    try:
        # Try to get the discounted price
        discount = driver.find_element(By.CSS_SELECTOR, "div.price-sale.price.js-price").text
        print(f"💰 Found discounted price: {discount}")
        return discount
    except NoSuchElementException:
        try:
            # Fallback to regular price if no discount
            regular = driver.find_element(By.CSS_SELECTOR, "div.price-regular.price.js-price").text
            print(f"💵 Found regular price: {regular}")
            return regular
        except NoSuchElementException:
            print("⚠️ No price found on page.")
            return ""

def get_product_summary(driver):
    try:
        p_tag = driver.find_element(By.CSS_SELECTOR, "p.Product-summary.Product-summary-block")
        html = p_tag.get_attribute("innerHTML").strip()

        lines = [line.strip().strip('"') for line in html.split('<br>') if line.strip()]
        winery, grapes, region, wine_style = "", "", "", ""

        for line in lines:
            if line.startswith("Winery:"):
                winery = line.replace("Winery:", "").strip()
            elif line.startswith("Grapes:"):
                grapes = line.replace("Grapes:", "").strip()
            elif line.startswith("Region:"):
                region = line.replace("Region:", "").strip()
            elif line.startswith("Wine style:"):
                wine_style = line.replace("Wine style:", "").strip()

        return winery, grapes, region, wine_style

    except NoSuchElementException:
        print(f"❌ Failed to extract product summary")
        return "", "", "", ""

# === Step 2: Collect product links ===
for page in range(1, pages_to_scrape + 1):
    url = base_url.format(page)
    print(f"\n📄 Loading page {url}")
    driver.get(url)
    time.sleep(3)

    handle_age_gate()

    product_elements = driver.find_elements(By.CSS_SELECTOR, "product-item")
    for product in product_elements:
        print(product)
        try:
            link = product.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
            print(link)
            if link not in wine_links:
                wine_links.append(link)
        except:
            print("no link element found")
            continue

# === Step 3: Visit each product page ===
for wine_url in wine_links:
    print(f"🔍 Scraping: {wine_url}")
    driver.get(wine_url)
    time.sleep(1)

    try:
        name = driver.find_element(By.CSS_SELECTOR, "h1.Product-title").text  # product_title entry-title
        price = get_shopline_price(driver)

        winery, grapes, region, wine_style = get_product_summary(driver)
        try:
            image_url = driver.find_element(By.CSS_SELECTOR, 'img[role="presentation"]').get_attribute("src")
        except:
            image_url = ""  # fallback if not found


        image_path = download_image(image_url, name)


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
        print(wine_data)

    except Exception as e:
        print(f"❌ Failed to scrape {wine_url}: {e}")
    time.sleep(1)

# === Step 4: Save to CSV ===
if wine_data:
    with open("selenium_wines_output.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=wine_data[0].keys())
        writer.writeheader()
        writer.writerows(wine_data)

    print("\n✅ All done! Data saved to selenium_wines_output.csv")
else:
    print("⚠️ No data scraped.")

# === Cleanup ===
driver.quit()
