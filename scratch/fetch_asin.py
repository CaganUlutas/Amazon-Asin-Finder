import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="America/New_York",
        )
        await context.add_cookies([
            {"name": "i18n-prefs", "value": "USD", "domain": ".amazon.com", "path": "/"},
            {"name": "lc-main", "value": "en_US", "domain": ".amazon.com", "path": "/"}
        ])
        page = await context.new_page()
        
        # Searching by ASIN usually brings up the product itself in the results.
        url = "https://www.amazon.com/s?k=B00E55DL4I"
        print(f"Navigating to {url}")
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(4)
            
            # Find the element
            element = await page.query_selector(f'[data-asin="B00E55DL4I"]')
            if element:
                html = await element.inner_html()
                with open("scratch/b00e_html.html", "w", encoding="utf-8") as f:
                    f.write(html)
                print("Found element, saved to scratch/b00e_html.html")
            else:
                print("Element not found. Dumping full page.")
                html = await page.content()
                with open("scratch/b00e_html.html", "w", encoding="utf-8") as f:
                    f.write(html)
        except Exception as e:
            print("Error:", e)
            
        await browser.close()

asyncio.run(main())
