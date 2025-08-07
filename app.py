
from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

def fetch_aliexpress_data(url):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')

    # Titolo
    title = soup.find('title').text.strip()

    # Prezzo (semplificato)
    price = re.search(r'"priceAmount":([\d.]+)', r.text)
    price = float(price.group(1)) if price else 10.00

    # Descrizione (semplificata)
    desc_tag = soup.find('meta', {'name': 'description'})
    description = desc_tag['content'] if desc_tag else "Descrizione non trovata."

    # Immagini principali
    images = re.findall(r'"imageUrl":"(https://[^"]+\.jpg)', r.text)
    images = list(set(images))[:5]  # primi 5 unici

    return {
        "title": title,
        "price": price,
        "description": description,
        "images": images
    }

def fetch_amazon_data(url):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')

    # Titolo
    title = soup.find(id='productTitle')
    title = title.text.strip() if title else "Titolo non trovato"

    # Prezzo (tentativi)
    price_tag = soup.find('span', {'class': 'a-price-whole'})
    price = float(price_tag.text.replace(',', '.').replace('€', '').strip()) if price_tag else 20.00

    # Descrizione (semplificata)
    desc = soup.find('meta', {'name': 'description'})
    description = desc['content'] if desc else "Descrizione non trovata."

    # Immagini
    images = re.findall(r'"hiRes":"(https://[^"]+\.jpg)', r.text)
    images = list(set(images))[:5]

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

        # Calcola nuovo prezzo +20%
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
    app.run(debug=True)
