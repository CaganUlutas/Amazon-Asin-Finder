import requests
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Cookie': 'i18n-prefs=USD; lc-main=en_US; sp-cdn=L5Z9:US'
}

url = "https://www.amazon.com/Automotive-Window-Sunshades/b/ref=dp_bc_4?ie=UTF8&node=15737211"

response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

h1 = soup.find('h1')
if h1:
    print("H1:", h1.text.strip().replace('\n', ' '))
    
pagination = soup.select_one('.s-pagination-strip')
if pagination:
    print("Pagination:", pagination.text.strip().replace('\n', ' '))
else:
    print("No pagination strip found")
