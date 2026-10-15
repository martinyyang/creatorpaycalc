#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CreatorPayCalc — SEO 五条铁律 + 数学精度单测
==============================================
沿用站 1（epoxycalculators）TDD 基座：
  1) 每个页面 TD 唯一、H1 唯一、Canonical 正确、Meta Description 非空
  2) 全站 JSON-LD 结构数据
  3) SSR 内容实质（每页正文 ≥ 300 字符，反薄内容/反 Scaled Content Abuse）
  4) 站内链接全部可达（无 404 内链）
  5) robots.txt / sitemap.xml 与产物一致；GA4/Clarity 注入器按 env 生效
  数学：所有金额 Decimal 2 位 ROUND_HALF_UP；打包求解器最优性抽查。

运行：python3 tests/test_creator_site_seo_and_math.py -v
"""

import os
import re
import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILDER = ROOT / "builder"
DIST = ROOT / "dist"

sys.path.insert(0, str(BUILDER))
from creator_math import (  # noqa: E402
    d, money, rpm_to_earnings, cpm_to_creator_earnings, earnings_to_views,
    bits_streamer_earnings, cheapest_pack_mix, viewer_cost, us_take_home, portfolio_total,
)

SITE_URL = "https://creatorpaycalc.com"


def read(rel: str) -> str:
    return (DIST / rel).read_text(encoding="utf-8")


class TestMathPrecision(unittest.TestCase):
    def test_rpm_to_earnings_basic(self):
        self.assertEqual(money(rpm_to_earnings(d("100000"), d("4.00"))), money("400.00"))
        self.assertEqual(money(rpm_to_earnings(d("0"), d("4.00"))), money("0.00"))

    def test_rpm_to_earnings_rounding_half_up(self):
        # 100,001 views @ $1.00 RPM = $100.001 -> 取整 $100.00 (ROUND_HALF_UP 对 .001 向下)
        self.assertEqual(money(rpm_to_earnings(d("100001"), d("1.00"))), money("100.00"))
        # 100,005 views @ $1.00 RPM = $100.005 -> ROUND_HALF_UP -> $100.01
        self.assertEqual(money(rpm_to_earnings(d("100005"), d("1.00"))), money("100.01"))

    def test_cpm_to_creator_earnings(self):
        # 100k views, $10 CPM, 60% monetized, 55% creator share
        self.assertEqual(
            money(cpm_to_creator_earnings(d("100000"), d("10.00"), d("60"), d("55"))),
            money("330.00"),
        )

    def test_earnings_to_views(self):
        self.assertEqual(money(earnings_to_views(d("1000"), d("5.00"))), money("200000.00"))
        self.assertEqual(money(earnings_to_views(d("1000"), d("0"))), money("0.00"))

    def test_bits_streamer_flat_rate(self):
        self.assertEqual(money(bits_streamer_earnings(d("1000"))), money("10.00"))
        self.assertEqual(money(bits_streamer_earnings(d("25000"))), money("250.00"))

    def test_cheapest_pack_mix_6500(self):
        mix, total = cheapest_pack_mix(6500)
        # 最优：1x5000 + 1x1500 = 64.40 + 19.95 = 84.35（比 5000+3x500 更省）
        self.assertEqual(total, money("84.35"))
        sizes = dict(mix)
        self.assertEqual(sizes.get(5000), 1)
        self.assertEqual(sizes.get(1500), 1)

    def test_cheapest_pack_mix_single_pack(self):
        _, total = cheapest_pack_mix(10000)
        self.assertEqual(total, money("126.00"))

    def test_viewer_cost_ceiling(self):
        # 观众成本 >= 主播实收（Twitch 必然抽成）
        for bits in (100, 1000, 5000, 10000, 25000, 100000):
            self.assertGreaterEqual(
                viewer_cost(bits), money(bits_streamer_earnings(d(bits)))
            )

    def test_us_take_home_sanity(self):
        res = us_take_home(d("100000"))
        self.assertEqual(res["gross"], money("100000.00"))
        self.assertGreater(res["take_home"], money("0"))
        self.assertLess(res["take_home"], res["gross"])
        self.assertGreater(res["effective_rate"], d("50"))  # 六位数十万级有效到手 >50%

    def test_portfolio_total(self):
        gross, take = portfolio_total([("a", d("1000")), ("b", d("500")), ("c", d("250.5"))])
        self.assertEqual(gross, money("1750.50"))
        self.assertLess(take, gross)


class TestSEOIronRules(unittest.TestCase):
    PAGES = [
        "index.html", "youtube-money-calculator/index.html",
        "twitch-bits-to-usd/index.html", "views-to-money-calculator/index.html",
        "cpm-vs-rpm/index.html",
        "tiktok-money-calculator/index.html",
        "youtube-rpm-calculator/index.html", "twitch-sub-calculator/index.html",
        "blog/how-much-does-youtube-pay-per-view/index.html",
        "blog/how-much-do-creators-make/index.html",
        "404.html",
    ]
    AMOUNT_PAGES = [f"twitch-bits-to-usd/{b}/index.html" for b in (100, 1000, 5000, 10000, 25000, 100000)]

    def _all_pages(self):
        return self.PAGES + self.AMOUNT_PAGES

    def test_title_unique_and_present(self):
        seen = set()
        for p in self._all_pages():
            html = read(p)
            m = re.search(r"<title>(.*?)</title>", html, re.S)
            self.assertIsNotNone(m, f"{p}: missing <title>")
            title = m.group(1).strip()
            self.assertTrue(len(title) > 10, f"{p}: title too short")
            self.assertNotIn(title, seen, f"{p}: duplicate title")
            seen.add(title)

    def test_h1_unique_and_present(self):
        seen = set()
        for p in self._all_pages():
            html = read(p)
            h1s = re.findall(r"<h1>(.*?)</h1>", html, re.S)
            self.assertEqual(len(h1s), 1, f"{p}: must have exactly one H1, got {len(h1s)}")
            h1 = h1s[0].strip()
            self.assertTrue(h1, f"{p}: empty H1")
            self.assertNotIn(h1, seen, f"{p}: duplicate H1")
            seen.add(h1)

    def test_canonical_correct(self):
        expected = {
            "index.html": "/",
            "youtube-money-calculator/index.html": "/youtube-money-calculator/",
            "twitch-bits-to-usd/index.html": "/twitch-bits-to-usd/",
            "views-to-money-calculator/index.html": "/views-to-money-calculator/",
            "cpm-vs-rpm/index.html": "/cpm-vs-rpm/",
            "tiktok-money-calculator/index.html": "/tiktok-money-calculator/",
            "youtube-rpm-calculator/index.html": "/youtube-rpm-calculator/",
            "twitch-sub-calculator/index.html": "/twitch-sub-calculator/",
            "blog/how-much-does-youtube-pay-per-view/index.html": "/blog/how-much-does-youtube-pay-per-view/",
            "blog/how-much-do-creators-make/index.html": "/blog/how-much-do-creators-make/",
        }
        for b in (100, 1000, 5000, 10000, 25000, 100000):
            expected[f"twitch-bits-to-usd/{b}/index.html"] = f"/twitch-bits-to-usd/{b}/"
        for p, path in expected.items():
            html = read(p)
            self.assertIn(
                f'<link rel="canonical" href="{SITE_URL}{path}">', html, f"{p}: canonical mismatch"
            )

    def test_meta_description_nonempty(self):
        for p in self._all_pages():
            html = read(p)
            m = re.search(r'<meta name="description" content="(.*?)">', html, re.S)
            self.assertIsNotNone(m, f"{p}: missing meta description")
            self.assertTrue(len(m.group(1).strip()) >= 40, f"{p}: meta description too short")

    def test_jsonld_present(self):
        for p in self._all_pages():
            html = read(p)
            self.assertIn('application/ld+json', html, f"{p}: missing JSON-LD")
            self.assertIn('"@context": "https://schema.org"', html, f"{p}: invalid JSON-LD context")

    def test_ssr_substantive_content(self):
        # 反 Scaled Content Abuse：每页正文实质内容（去标签后）>= 300 字符
        for p in self._all_pages():
            html = read(p)
            body = re.sub(r"<script.*?</script>", "", html, flags=re.S)
            body = re.sub(r"<[^>]+>", " ", body)
            body = re.sub(r"\s+", " ", body).strip()
            self.assertGreaterEqual(len(body), 300, f"{p}: thin content ({len(body)} chars)")

    def test_internal_links_resolve(self):
        # 站内 href 全部可达（相对路径对照 dist 文件）
        for p in self._all_pages():
            html = read(p)
            for href in re.findall(r'href="(/[^"]*)"', html):
                if href.endswith(".xml") or href == "/404.html":
                    continue
                href = href.split("?")[0]  # 剥离 CSS 版本号查询参数
                rel = href.lstrip("/")
                if rel.endswith("/"):
                    rel += "index.html"
                self.assertTrue(
                    (DIST / rel).exists(),
                    f"{p}: broken internal link {href}",
                )

    def test_robots_and_sitemap_consistency(self):
        robots = read("robots.txt")
        self.assertIn("Sitemap:", robots)
        sitemap = read("sitemap.xml")
        urls = re.findall(r"<loc>(.*?)</loc>", sitemap)
        # 每个 sitemap URL 都有对应产物
        for u in urls:
            path = u.replace(SITE_URL, "").lstrip("/")
            if path.endswith("/"):
                path += "index.html"
            self.assertTrue((DIST / path).exists(), f"sitemap URL missing file: {u}")
        # 每个产物页面（除 404/robots/css/json）都在 sitemap；404 不应入 sitemap
        for p in self._all_pages():
            if p == "404.html":
                continue
            url_path = "/" + p.replace("index.html", "")
            self.assertIn(SITE_URL + url_path, urls, f"{p} missing from sitemap")

    def test_html_lang_and_viewport(self):
        for p in self._all_pages():
            html = read(p)
            self.assertIn('<html lang="en">', html, f"{p}: missing lang")
            self.assertIn('name="viewport"', html, f"{p}: missing viewport")

    def test_no_duplicate_canonical_or_h1_in_amount_pages(self):
        for p in self.AMOUNT_PAGES:
            html = read(p)
            self.assertEqual(html.count('rel="canonical"'), 1, f"{p}: canonical count")

    def test_analytics_injection_env(self):
        # 注入器：env 设置时输出 GA4/Clarity，未设置时不输出
        from build_site import inject_analytics
        sample = "<html><head></head><body>x</body></html>"
        out = inject_analytics(sample)
        self.assertNotIn("googletagmanager", out)
        os.environ["GA4_MEASUREMENT_ID"] = "G-TEST123456"
        os.environ["CLARITY_PROJECT_ID"] = "testproj1"
        import importlib
        import build_site as bs
        importlib.reload(bs)
        out = bs.inject_analytics(sample)
        self.assertIn("G-TEST123456", out)
        self.assertIn("clarity.ms", out)
        del os.environ["GA4_MEASUREMENT_ID"]
        del os.environ["CLARITY_PROJECT_ID"]


if __name__ == "__main__":
    unittest.main(verbosity=2)
