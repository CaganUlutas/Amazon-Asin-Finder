import requests
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Cookie': 'i18n-prefs=USD; lc-main=en_US; sp-cdn=L5Z9:US'
}

# Construct /b URL with price filter (3500-7000)
url = "https://www.amazon.com/PC-Gaming-Keyboards/b?ie=UTF8&node=402051011&rh=n%3A402051011%2Cp_36%3A3500-7000"

# Note: allow_redirects=False to see if Amazon redirects it to /s
response = requests.get(url, headers=headers, allow_redirects=False)

print(f"Status: {response.status_code}")
if response.status_code in [301, 302]:
    print(f"Redirects to: {response.headers.get('Location')}")
else:
    soup = BeautifulSoup(response.text, 'html.parser')
    h1 = soup.find('h1')
    if h1:
        print("H1:", h1.text.strip().replace('\n', ' '))
    pagination = soup.select_one('.s-pagination-strip')
    if pagination:
        print("Pagination:", pagination.text.strip().replace('\n', ' '))
    else:
        print("No pagination found")
