import asyncio
from playwright.async_api import async_playwright
import re

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # non-headless to avoid bot detection
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        url = "https://www.amazon.com/s?k=B00E55DL4I"
        print(f"Navigating to {url}")
        await page.goto(url, wait_until="domcontentloaded")
        
        await asyncio.sleep(3)
        
        # Get the container for this ASIN
        element = await page.query_selector(f'[data-asin="B00E55DL4I"]')
        if not element:
            print("Product not found on page.")
            await browser.close()
            return
            
        html = await element.inner_html()
        with open("scratch/asin_html.html", "w", encoding="utf-8") as f:
            f.write(html)
            
        print("Product HTML saved to scratch/asin_html.html")
        
        # Now try to extract price manually
        # 1. Try .a-price:not(.a-text-price) .a-offscreen (excludes strike-through original prices!)
        try:
            price_els = await element.query_selector_all('.a-price:not(.a-text-price):not([data-a-strike="true"])')
            for i, price_el in enumerate(price_els):
                print(f"Price Element {i}:")
                print(f"  Inner HTML: {await price_el.inner_html()}")
                offscreen = await price_el.query_selector(".a-offscreen")
                if offscreen:
                    text = await offscreen.text_content()
                    print(f"  Offscreen text_content: '{text}'")
                    # _parse_price_string
                    match = re.search(r"[\$\€\£\₺]?\s*([\d,]+\.?\d*)", text if text else "")
                    if match:
                        raw = match.group(1).replace(",", "")
                        print(f"  Parsed as: {float(raw)}")
                else:
                    print("  No .a-offscreen found")
        except Exception as e:
            print("Error in 1:", e)

        # fallback
        try:
            price_el = await element.query_selector(".a-color-price")
            if price_el:
                print("Color price HTML:", await price_el.inner_html())
                text = await price_el.text_content()
                print("Color price text_content:", text)
        except Exception as e:
            pass

        await browser.close()

asyncio.run(main())
