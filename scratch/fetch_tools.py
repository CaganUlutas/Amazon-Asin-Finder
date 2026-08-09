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
        
        url = "https://www.amazon.com/s?i=tools&rh=n%3A551238&s=popularity-rank&fs=true&qid=1786221004&xpid=gtX8nlOaT7P76&ref=sr_pg_1"
        print(f"Navigating to {url}")
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)
            
            html = await page.content()
            with open("scratch/tools_html.html", "w", encoding="utf-8") as f:
                f.write(html)
            await page.screenshot(path="scratch/tools_screenshot.png")
            print("Saved HTML and screenshot.")
        except Exception as e:
            print("Error:", e)
            
        await browser.close()

asyncio.run(main())
