import asyncio
from playwright.async_api import async_playwright

URL = "http://192.168.178.12:5173"
OUT = "/home/kev/shots"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--enable-gpu", "--use-gl=egl", "--ignore-gpu-blocklist", "--no-sandbox"])
        context = await browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True)
        page = await context.new_page()
        await page.goto(URL, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(3000)
        await page.click(".bottom-nav button:has-text('Portfolio')")
        print("portfolio loading (prices)...")
        await page.wait_for_timeout(22000)
        await page.screenshot(path=f"{OUT}/02-portfolio-top.png")
        await page.evaluate("document.querySelector('.content').scrollTop = 700")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=f"{OUT}/03-portfolio-scrolled.png")
        print("DONE4")
        await browser.close()

asyncio.run(main())
