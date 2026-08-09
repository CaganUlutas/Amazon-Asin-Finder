import requests
from bs4 import BeautifulSoup
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Cookie': 'i18n-prefs=USD; lc-main=en_US; sp-cdn=L5Z9:US'
}

def parse_price(element):
    price_els = element.select('.a-price:not(.a-text-price):not([data-a-strike="true"])')
    for p_el in price_els:
        off = p_el.select_one('.a-offscreen')
        if off:
            text = off.text.strip()
            match = re.search(r"[\$\€\£\₺]?\s*([\d,]+\.?\d*)", text)
            if match: return float(match.group(1).replace(',', ''))
    secondary = element.select_one('[data-cy="secondary-offer-recipe"]')
    if secondary:
        texts = secondary.stripped_strings
        for text in texts:
            match = re.search(r"^\$?([\d,]+\.\d{2})$", text.strip())
            if match: return float(match.group(1).replace(',', ''))
    return None

url = "https://www.amazon.com/PC-Gaming-Keyboards/b?ie=UTF8&node=402051011&s=price-desc-rank"
response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

results = soup.select('[data-component-type="s-search-result"]')[:5]
for r in results:
    price = parse_price(r)
    print(f"Price: {price}")
