from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import os
import re
import subprocess
from playwright.sync_api import sync_playwright

BROWSER_PATH = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/tmp/pw-browsers")
# ======= Fallback automatico installazione Chromium =======
def ensure_chromium():
    browser_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/tmp/pw-browsers")
    chromium_bin = os.path.join(browser_path, "chromium")
    if not os.path.exists(browser_path) or not any("chromium" in d for d in os.listdir(browser_path)):
        print("[INFO] Chromium mancante, installazione...")
        subprocess.run(
            ["playwright", "install", "chromium"],
            env={**os.environ, "PLAYWRIGHT_BROWSERS_PATH": browser_path},
            check=True
        )
        print("[INFO] Chromium installato.")
       



# ==========================================================


app = Flask(__name__)
ensure_chromium()

def fetch_page_content(url):
    """Apre una pagina con Playwright in headless e restituisce HTML e URL corrente. 
       Se Playwright fallisce, prova il fallback con requests."""
    try:
        ensure_chromium()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle")
            html = page.content()
            current_url = page.url
            browser.close()
        return html, current_url
    except Exception as e:
        print(f"[Fallback] Errore Playwright: {e}")
        return fetch_page_fallback(url), url


def fetch_page_fallback(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        return soup.prettify(), url
    except Exception as e:
        return f"Errore nel fallback: {e}", url



def fetch_amazon_data(url):
    html, _ = fetch_page_content(url)
    soup = BeautifulSoup(html, "html.parser")

    # --- Titolo ---
    title_el = soup.select_one("#productTitle")
    title = title_el.get_text(strip=True) if title_el else "Titolo non trovato"

    # --- Prezzo ---
    price = None
    selectors = [
        "#priceblock_ourprice",
        "#priceblock_dealprice",
        "#priceblock_saleprice",
        ".a-price .a-offscreen"
    ]
    for sel in selectors:
        el = soup.select_one(sel)
        if el and el.get_text(strip=True):
            price_text = el.get_text(strip=True)
            price_clean = re.sub(r"[^\d,\.]", "", price_text)
            if "," in price_clean and price_clean.rfind(",") > price_clean.rfind("."):
                price_clean = price_clean.replace(".", "").replace(",", ".")
            else:
                price_clean = price_clean.replace(",", "")
            try:
                price = float(price_clean)
                break
            except:
                continue
    if price is None:
        price = 20.00  # fallback

    # --- Descrizione ---
    desc = None
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        desc = meta_desc["content"].strip()
    else:
        bullet_points = soup.select("#feature-bullets li span")
        desc = " ".join([bp.get_text(strip=True) for bp in bullet_points if bp.get_text(strip=True)]) or "Descrizione non trovata."

    # --- Immagini ---
    images = []
    for img_tag in soup.select("img[src]"):
        src = img_tag["src"]
        if "media-amazon" in src and src.endswith(".jpg") and src not in images:
            images.append(src)
    images = images[:5]  # max 5 immagini

    return {
        "title": title,
        "price": price,
        "description": desc,
        "images": images
    }


def fetch_aliexpress_data(url):
    html, _ = fetch_page_content(url)
    soup = BeautifulSoup(html, "html.parser")

    # --- Titolo ---
    title_el = soup.select_one("h1.product-title-text") or soup.find("title")
    title = title_el.get_text(strip=True) if title_el else "Titolo non trovato"

    # --- Prezzo ---
    price = None
    selectors = [
        "div.product-price-current span",
        "span.uniform-banner-box-price",
        "div.product-price-value"
    ]
    for sel in selectors:
        el = soup.select_one(sel)
        if el and el.get_text(strip=True):
            price_text = el.get_text(strip=True)
            price_clean = re.sub(r"[^\d,\.]", "", price_text)
            if "," in price_clean and price_clean.rfind(",") > price_clean.rfind("."):
                price_clean = price_clean.replace(".", "").replace(",", ".")
            else:
                price_clean = price_clean.replace(",", "")
            try:
                price = float(price_clean)
                break
            except:
                continue
    if price is None:
        price = 10.00  # fallback

    # --- Descrizione ---
    desc = None
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        desc = meta_desc["content"].strip()
    else:
        summary = soup.select_one(".product-detail-main .product-description")
        desc = summary.get_text(strip=True) if summary else "Descrizione non trovata."

    # --- Immagini ---
    images = []
    for img_tag in soup.select("img[src]"):
        src = img_tag["src"]
        if "alicdn.com" in src and src.endswith(".jpg") and src not in images:
            images.append(src)
    images = images[:5]  # max 5 immagini

    return {
        "title": title,
        "price": price,
        "description": desc,
        "images": images
    }



@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']
        if "aliexpress.com" in url:
            data = fetch_aliexpress_data(url)
        elif "amazon." in url:
            data = fetch_amazon_data(url)
        else:
            return "Sito non supportato (solo Amazon e AliExpress)"

        final_price = round(data['price'] * 1.2, 2)

        return render_template(
            'result.html',
            title=data['title'],
            price_original=data['price'],
            price_final=final_price,
            description=data['description'],
            images=data['images']
        )
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>eBay Easy Lister</title></head>
    <body>
        <h2>Inserisci link prodotto Amazon o AliExpress:</h2>
        <form method="post">
            <input type="text" name="url" style="width: 400px" required />
            <input type="submit" value="Genera Scheda" />
        </form>
    </body>
    </html>
    '''

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
