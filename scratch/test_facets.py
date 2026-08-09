import requests
from bs4 import BeautifulSoup
import urllib.parse

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Cookie': 'i18n-prefs=USD; lc-main=en_US; sp-cdn=L5Z9:US'
}

url = "https://www.amazon.com/PC-Gaming-Keyboards/b?ie=UTF8&node=402051011"
response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

print("Price facet links found:")
for link in soup.select('a.a-link-normal.s-navigation-item'):
    text = link.text.strip()
    if '$' in text:
        href = link.get('href')
        parsed = urllib.parse.urlparse(href)
        print(f"Text: {text} | Path: {parsed.path} | Query: {parsed.query}")
