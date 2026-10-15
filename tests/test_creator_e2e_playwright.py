#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CreatorPayCalc — Playwright 真实浏览器 E2E 测试（Async API，独立事件循环）
==========================================================================
覆盖：页面加载、H1 渲染、计算器交互（输入->结果变化）、资源加载无失败。
本地 http.server 的 404 不采用 404.html（部署层才生效），故 404 页直测 /404.html。

运行：python3 tests/test_creator_e2e_playwright.py
退出码 0 = 全部通过。
"""

import asyncio
import http.server
import os
import socketserver
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
CHROMIUM = os.environ.get("CHROMIUM_PATH") or ("/usr/local/bin/chromium" if Path("/usr/local/bin/chromium").exists() else None)
PORT = 8621
BASE = f"http://127.0.0.1:{PORT}"


FAILURES = []


class StaticServer:
    def __enter__(self):
        os.chdir(DIST)
        handler = http.server.SimpleHTTPRequestHandler
        socketserver.TCPServer.allow_reuse_address = True
        self.httpd = socketserver.TCPServer(("127.0.0.1", PORT), handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *a):
        self.httpd.shutdown()
        self.httpd.server_close()


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


async def check(name, coro_fn):
    try:
        await coro_fn()
        print(f"  [OK] {name}")
    except Exception as e:  # noqa: BLE001
        FAILURES.append(name)
        print(f"  [FAIL] {name}: {type(e).__name__}: {e}")



async def run_all():
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        launch_kwargs = {"headless": True, "args": ["--no-sandbox"]}
        if CHROMIUM:
            launch_kwargs["executable_path"] = CHROMIUM
        browser = await p.chromium.launch(**launch_kwargs)


        async def t_home():
            page = await browser.new_page()
            failed = []
            page.on("requestfailed", lambda r: (None if ("googletagmanager.com" in r.url or "google-analytics.com" in r.url or "clarity.ms" in r.url) else failed.append(r.url)))
            await page.goto(BASE + "/")
            assert "CreatorPayCalc — Free Creator Earnings" in await page.title()
            assert await page.locator("h1").count() == 1
            assert "YouTube Money Calculator" in await page.locator("body").inner_text()
            assert failed == [], f"failed requests: {failed}"
            await page.close()

        async def t_youtube():
            page = await browser.new_page()
            failed = []
            page.on("requestfailed", lambda r: (None if ("googletagmanager.com" in r.url or "google-analytics.com" in r.url or "clarity.ms" in r.url) else failed.append(r.url)))
            await page.goto(BASE + "/youtube-money-calculator/")
            assert (await page.locator("h1").inner_text()).strip() == "YouTube Money Calculator"
            assert (await page.locator("#rpm_out").inner_text()) == "$400.00"  # SSR 默认
            await page.locator("#rpm_views").fill("250000")
            await page.locator("#rpm_views").dispatch_event("input")
            assert (await page.locator("#rpm_out").inner_text()) == "$1,000.00"
            assert failed == []
            await page.close()

        async def t_bits():
            page = await browser.new_page()
            failed = []
            page.on("requestfailed", lambda r: (None if ("googletagmanager.com" in r.url or "google-analytics.com" in r.url or "clarity.ms" in r.url) else failed.append(r.url)))
            await page.goto(BASE + "/twitch-bits-to-usd/")
            await page.locator("#bits_count").fill("1000")
            await page.locator("#bits_count").dispatch_event("input")
            assert (await page.locator("#bits_streamer").inner_text()) == "$10.00"
            await page.locator("#bits_count").fill("6500")
            await page.locator("#bits_count").dispatch_event("input")
            assert "$84.35" in await page.locator("#bits_viewer").inner_text()
            assert failed == []
            await page.close()

        async def t_views():
            page = await browser.new_page()
            failed = []
            page.on("requestfailed", lambda r: (None if ("googletagmanager.com" in r.url or "google-analytics.com" in r.url or "clarity.ms" in r.url) else failed.append(r.url)))
            await page.goto(BASE + "/views-to-money-calculator/")
            await page.locator("#v2m_target").fill("2000")
            await page.locator("#v2m_target").dispatch_event("input")
            assert (await page.locator("#v2m_out").inner_text()) == "400,000"
            assert failed == []
            await page.close()

        async def t_amount_page():
            page = await browser.new_page()
            failed = []
            page.on("requestfailed", lambda r: (None if ("googletagmanager.com" in r.url or "google-analytics.com" in r.url or "clarity.ms" in r.url) else failed.append(r.url)))
            await page.goto(BASE + "/twitch-bits-to-usd/25000/")
            assert (await page.locator("h1").inner_text()).strip() == "How Much is 25,000 Twitch Bits?"
            assert "$250.00" in await page.locator("body").inner_text()
            assert failed == []
            await page.close()

        async def t_404():
            page = await browser.new_page()
            failed = []
            page.on("requestfailed", lambda r: (None if ("googletagmanager.com" in r.url or "google-analytics.com" in r.url or "clarity.ms" in r.url) else failed.append(r.url)))
            await page.goto(BASE + "/404.html")
            assert "404" in await page.title()
            assert failed == []
            await page.close()

        await check("首页加载与工具导航", t_home)
        await check("YouTube 计算器交互（100k@$4→$400；250k→$1,000）", t_youtube)
        await check("Twitch Bits 交互（1000→$10；6500 最省 $84.35）", t_bits)
        await check("Views to Money 交互（$2,000@$5→400,000）", t_views)
        await check("按量落地页（25,000 Bits）", t_amount_page)
        await check("404 页面", t_404)

        await browser.close()


def main() -> int:
    with StaticServer():
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(run_all())
        finally:
            loop.close()
    print(f"\n结果：{'PASS' if not FAILURES else 'FAIL'}（{6 - len(FAILURES)}/6）")
    return 0 if not FAILURES else 1


if __name__ == "__main__":
    sys.exit(main())
