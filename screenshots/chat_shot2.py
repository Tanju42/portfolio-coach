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
        await page.click(".bottom-nav button:has-text('Coach')")
        await page.wait_for_timeout(1500)
        await page.click(".empty-chat .chip:has-text('biggest risk')")
        print("sent; waiting for LLM answer...")
        for _ in range(40):
            await page.wait_for_timeout(5000)
            if not await page.query_selector(".thinking"):
                break
        await page.wait_for_timeout(2000)
        await page.evaluate("document.querySelector('.messages').scrollTop = 99999")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=f"{OUT}/06-chat-risk-bottom.png")
        print("DONE3")
        await browser.close()

asyncio.run(main())
