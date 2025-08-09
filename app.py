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
    chromium_bin = os.path.join(browsers_path, "chromium")
    if not os.path.exists(browsers_path) or not any("chromium" in d for d in os.listdir(browsers_path)):
        print("[INFO] Chromium mancante, installazione...")
        subprocess.run(
            ["playwright", "install", "chromium"],
            env={**os.environ, "PLAYWRIGHT_BROWSERS_PATH": browsers_path},
            check=True
        )
        print("[INFO] Chromium installato.")
       



# ==========================================================


app = Flask(__name__)
    ensure_chromium()

def fetch_page_content(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                executable_path=None  # Lascia che Playwright trovi il binario installato in runtime
            )
            page = browser.new_page()
            page.goto(url, wait_until="networkidle")
            html = page.content()
            browser.close()
        return html
    except Exception as e:
        print(f"[Fallback] Errore Playwright: {e}")
        return fetch_page_fallback(url)

def fetch_page_fallback(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        return soup.prettify()
    except Exception as e:
        return f"Errore nel fallback: {e}"

def fetch_amazon_data(url):
    html, _ = fetch_page_content(url)

    # Titolo
    title_match = re.search(r'id="productTitle".*?>(.*?)<', html, re.S)
    title = title_match.group(1).strip() if title_match else "Titolo non trovato"

    # Prezzo (più robusto)
    price_match = re.search(r'€\s?([\d,.]+)', html)
    price = float(price_match.group(1).replace('.', '').replace(',', '.')) if price_match else 20.00

    # Descrizione
    desc_match = re.search(r'<meta name="description" content="([^"]+)"', html)
    description = desc_match.group(1).strip() if desc_match else "Descrizione non trovata."

    # Immagini
    images = list(set(re.findall(r'https://[^"]+\.jpg', html)))
    images = [img for img in images if "media-amazon" in img][:5]

    return {
        "title": title,
        "price": price,
        "description": description,
        "images": images
    }

def fetch_aliexpress_data(url):
    html, _ = fetch_page_content(url)

    # Titolo
    title_match = re.search(r'<title>(.*?)</title>', html, re.S)
    title = title_match.group(1).strip() if title_match else "Titolo non trovato"

    # Prezzo
    price_match = re.search(r'"salePrice"\s*:\s*"([\d,.]+)"', html)
    if not price_match:
        price_match = re.search(r'"price"\s*:\s*"([\d,.]+)"', html)
    price = float(price_match.group(1).replace(',', '.')) if price_match else 10.00

    # Descrizione
    desc_match = re.search(r'<meta name="description" content="([^"]+)"', html)
    description = desc_match.group(1).strip() if desc_match else "Descrizione non trovata."

    # Immagini
    images = list(set(re.findall(r'https://[^"]+\.jpg', html)))
    images = [img for img in images if "alicdn.com" in img][:5]

    return {
        "title": title,
        "price": price,
        "description": description,
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
