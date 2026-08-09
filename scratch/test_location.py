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
        
        # Initial navigation to get session cookies
        page = await context.new_page()
        await page.goto("https://www.amazon.com/", wait_until="domcontentloaded")
        
        # Add the location cookie
        await context.add_cookies([
            {"name": "sp-cdn", "value": "L5Z9:US", "domain": ".amazon.com", "path": "/"},
            {"name": "i18n-prefs", "value": "USD", "domain": ".amazon.com", "path": "/"},
            {"name": "lc-main", "value": "en_US", "domain": ".amazon.com", "path": "/"}
        ])
        
        # Go to tools search page
        url = "https://www.amazon.com/s?i=tools&rh=n%3A551238&s=popularity-rank&fs=true"
        await page.goto(url, wait_until="domcontentloaded")
        
        await asyncio.sleep(3)
        
        # Check delivery location text
        nav_global = await page.query_selector("#nav-global-location-slot")
        if nav_global:
            print("Location slot:", await nav_global.inner_text())
            
        # Count price elements
        prices = await page.query_selector_all(".a-price")
        print("Number of prices found:", len(prices))
        
        await browser.close()

asyncio.run(main())
