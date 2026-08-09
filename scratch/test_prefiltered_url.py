import asyncio
from playwright.async_api import async_playwright
from src.crawler.product_parser import ProductParser

async def test_url():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="America/New_York",
        )
        await context.add_cookies([
            {"name": "i18n-prefs", "value": "USD", "domain": ".amazon.com", "path": "/"},
            {"name": "lc-main", "value": "en_US", "domain": ".amazon.com", "path": "/"},
            {"name": "sp-cdn", "value": "L5Z9:US", "domain": ".amazon.com", "path": "/"}
        ])
        page = await context.new_page()
        url = "https://www.amazon.com/s?k=Automotive+Interior+Sun+Protection&i=automotive&rh=n%3A15737191%2Cp_72%3A1248861011&dc=&c=ts&qid=1786227530&rnid=386419011&ts_id=15737191&ref=sr_nr_p_36_0_0&low-price=40&high-price="
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        products = await ProductParser.parse_search_results(page, url, 1)
        print(f"Found {len(products)} products")
        for i, p in enumerate(products[:3]):
            print(f"{i+1}. ASIN: {p.asin}, Price: {p.price}, Rating: {p.rating}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_url())
