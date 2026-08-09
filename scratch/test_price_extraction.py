import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content('''
        <style>
        .a-offscreen { position: absolute; left: -10000px; clip: rect(0 0 0 0); }
        </style>
        <div class="a-price">
            <span class="a-offscreen">$34.99</span>
        </div>
        ''')
        
        # Test 1: inner_text()
        el = await page.query_selector('.a-offscreen')
        inner_text = await el.inner_text()
        print(f"inner_text: {repr(inner_text)}")
        
        # Test 2: text_content()
        text_content = await el.text_content()
        print(f"text_content: {repr(text_content)}")
        
        await browser.close()

asyncio.run(main())
