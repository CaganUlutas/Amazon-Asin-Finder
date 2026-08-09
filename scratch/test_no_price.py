import requests
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Cookie': 'i18n-prefs=USD; lc-main=en_US; sp-cdn=L5Z9:US'
}

# Same URL but removed low-price=40 and high-price=
url = "https://www.amazon.com/s?k=Automotive+Interior+Sun+Protection&i=automotive&rh=n%3A15737191%2Cp_72%3A1248861011&dc=&c=ts&qid=1786227530&rnid=386419011&ts_id=15737191&ref=sr_nr_p_36_0_0"

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
