import requests
from bs4 import BeautifulSoup
import re
import time
import random

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Cookie': 'i18n-prefs=USD; lc-main=en_US; sp-cdn=L5Z9:US'
}

def parse_price(element):
    # Try .a-price ...
    price_els = element.select('.a-price:not(.a-text-price):not([data-a-strike="true"])')
    for p_el in price_els:
        off = p_el.select_one('.a-offscreen')
        if off:
            text = off.text.strip()
            match = re.search(r"[\$\€\£\₺]?\s*([\d,]+\.?\d*)", text)
            if match:
                return float(match.group(1).replace(',', ''))
                
    # Fallback for "No featured offers" layout
    secondary = element.select_one('[data-cy="secondary-offer-recipe"]')
    if secondary:
        texts = secondary.stripped_strings
        for text in texts:
            match = re.search(r"^\$?([\d,]+\.\d{2})$", text.strip())
            if match:
                return float(match.group(1).replace(',', ''))
    
    return None

pages_to_test = [1, 50, 100, 200, 300, 400]
total_over_35 = 0
total_items = 0

for page_num in pages_to_test:
    url = f"https://www.amazon.com/PC-Gaming-Keyboards/b?ie=UTF8&node=402051011&page={page_num}"
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = soup.select('[data-component-type="s-search-result"]')
        over_35 = 0
        valid_items = 0
        
        for r in results:
            price = parse_price(r)
            if price is not None:
                valid_items += 1
                if price > 35:
                    over_35 += 1
                    
        print(f"Page {page_num}: Found {len(results)} items. {valid_items} had prices. {over_35} are > $35.")
        total_over_35 += over_35
        total_items += valid_items
        time.sleep(1.5)
    except Exception as e:
        print(f"Error on page {page_num}: {e}")

if total_items > 0:
    percentage = (total_over_35 / total_items) * 100
    print(f"\nAcross {len(pages_to_test)} sampled pages:")
    print(f"Average % over $35: {percentage:.1f}%")
    print(f"Estimated total >$35 on 400 pages (400 * 24 = 9600 items): {int(9600 * (percentage/100))}")
else:
    print("Could not extract any prices to estimate.")
