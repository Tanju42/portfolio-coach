import asyncio
from playwright.async_api import async_playwright

URL = "http://192.168.178.12:5173"
OUT = "/home/kev/shots"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            args=["--enable-gpu", "--use-gl=egl", "--ignore-gpu-blocklist", "--no-sandbox"]
        )
        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=3,
            is_mobile=True,
            has_touch=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        )
        page = await context.new_page()
        await page.goto(URL, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(3000)

        await page.screenshot(path=f"{OUT}/01-chat-empty.png")
        print("shot: 01-chat-empty")

        await page.click("text=Portfolio")
        await page.wait_for_timeout(20000)
        await page.screenshot(path=f"{OUT}/02-portfolio-top.png")
        await page.evaluate("document.querySelector('.content').scrollTop = 600")
        await page.wait_for_timeout(800)
        await page.screenshot(path=f"{OUT}/03-portfolio-scrolled.png")
        print("shot: 02-03 portfolio")

        await page.click("text=Import")
        await page.wait_for_timeout(2500)
        await page.screenshot(path=f"{OUT}/04-import.png")
        print("shot: 04-import")

        await page.click("text=Coach")
        await page.wait_for_timeout(1500)
        await page.click("text=Should I sell my SOL?")
        print("waiting for LLM answer...")
        for _ in range(40):
            await page.wait_for_timeout(5000)
            if not await page.query_selector(".thinking"):
                break
        await page.wait_for_timeout(1500)
        await page.screenshot(path=f"{OUT}/05-chat-signal.png")
        await page.evaluate("document.querySelector('.messages').scrollTop = 99999")
        await page.wait_for_timeout(800)
        await page.screenshot(path=f"{OUT}/06-chat-signal-bottom.png")
        print("shot: 05-06 chat-signal")

        await browser.close()
        print("ALL_DONE")


asyncio.run(main())
