import asyncio
import logging
from playwright.async_api import async_playwright

from src.crawler.product_parser import ProductParser
from src.core.models import FilterModel
from src.core.filter_engine import FilterEngine

logging.basicConfig(level=logging.DEBUG)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        url = "https://www.amazon.com/s?k=wireless+mouse"
        print(f"Navigating to {url}")
        await page.goto(url, wait_until="domcontentloaded")
        
        await asyncio.sleep(5)  # Wait for things to settle
        
        print("Parsing products...")
        html = await page.content()
        with open("scratch/amazon_page.html", "w", encoding="utf-8") as f:
            f.write(html)
        await page.screenshot(path="scratch/amazon_page.png")
        products = await ProductParser.parse_search_results(page, url, 1)
        
        print(f"Found {len(products)} products.")
        
        filters = FilterModel(min_price=35.0)
        engine = FilterEngine(filters)
        filtered_products = engine.apply(products)
        
        print("\nAll Products:")
        for p in products:
            print(f"ASIN: {p.asin}, Price: {p.price}, Title: {p.title[:30] if p.title else 'None'}...")
            
        print(f"\nFiltered Products (min_price=35.0) Count: {len(filtered_products)}")
        for p in filtered_products:
            print(f"ASIN: {p.asin}, Price: {p.price}, Title: {p.title[:30] if p.title else 'None'}...")
        
        await browser.close()

asyncio.run(main())
