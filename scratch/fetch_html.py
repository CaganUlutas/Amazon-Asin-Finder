import requests

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Cookie': 'i18n-prefs=USD; lc-main=en_US; sp-cdn=L5Z9:US'
}

url = "https://www.amazon.com/s?k=Automotive+Interior+Sun+Protection&i=automotive&rh=n%3A15737191%2Cp_72%3A1248861011&dc=&c=ts&qid=1786227530&rnid=386419011&ts_id=15737191&ref=sr_nr_p_36_0_0&low-price=40&high-price="

response = requests.get(url, headers=headers)
with open('scratch/automotive.html', 'w', encoding='utf-8') as f:
    f.write(response.text)

print(f"Status: {response.status_code}")
print(f"Length: {len(response.text)}")
