#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CreatorPayCalc — 静态全站构建器
================================
模式沿用站 1（epoxycalculators）：
  - Python 模板渲染 -> 纯静态预渲染 dist/（SSR 全静态，首屏即含内容）
  - SEO 铁律注入：唯一 TD/H1、Canonical、Meta Description、JSON-LD、robots、sitemap
  - GA4 + Clarity 注入器（env 默认值，未配置时不输出）
  - 每个工具页内嵌原生 JS 计算器 + 服务端预渲染示例（Decimal 引擎）

用法：
  GA4_MEASUREMENT_ID=G-XXXX CLARITY_PROJECT_ID=xxxx python3 build_site.py
"""

import html
import json
import os
import shutil
import sys
from decimal import Decimal
from pathlib import Path
from typing import Callable, Dict, List, Tuple

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
DIST = ROOT.parent / "dist"
sys.path.insert(0, str(ROOT))
from creator_math import (  # noqa: E402
    d, money, rpm_to_earnings, cpm_to_creator_earnings, earnings_to_views,
    bits_streamer_earnings, cheapest_pack_mix, viewer_cost, us_take_home, portfolio_total,
)
from rpm_library import RPM_LIBRARY, country_multiplier, youtube_rpm  # noqa: E402


def usd(value) -> str:
    """金额显示：带 $ 前缀 + 千分位（Decimal -> str）。"""
    return f"${money(value):,}"


NICHE_LABELS = {
    "personal_finance_investing": "Personal finance & investing",
    "technology_reviews": "Tech reviews & tutorials",
    "education_howto": "Education & how-to",
    "business_marketing": "Business & marketing",
    "gaming": "Gaming",
    "entertainment_vlogs": "Entertainment & vlogs",
    "lifestyle_beauty": "Lifestyle & beauty",
    "music": "Music",
}

# ---------------------------------------------------------------------------
# 站点配置
# ---------------------------------------------------------------------------
SITE_NAME = "CreatorPayCalc"
SITE_URL = "https://creatorpaycalc.com"  # 已确认候选（原占位 creatormoneycalc.com 被他人抢注）
GA4_ID = os.environ.get("GA4_MEASUREMENT_ID", "")
CLARITY_ID = os.environ.get("CLARITY_PROJECT_ID", "")

# ---------------------------------------------------------------------------
# 注入器
# ---------------------------------------------------------------------------

def inject_analytics(body_html: str) -> str:
    """在 </head> 前注入 GA4 + Clarity（仅当 ID 已配置）。"""
    tags = []
    if GA4_ID:
        tags.append(
            f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA4_ID}"></script>\n'
            f"<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}"
            f"gtag('js',new Date());gtag('config','{GA4_ID}');</script>"
        )
    if CLARITY_ID:
        tags.append(
            f'<script>(function(c,l,a,r,i,t,y){{c[a]=c[a]||function(){{(c[a].q=c[a].q||[]).push(arguments)}};'
            f't=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/{CLARITY_ID}";'
            f'y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);}})(window,document,'
            f'"clarity","script","{CLARITY_ID}");</script>'
        )
    if not tags:
        return body_html
    return body_html.replace("</head>", "\n".join(tags) + "\n</head>")


# ---------------------------------------------------------------------------
# 基础布局
# ---------------------------------------------------------------------------

NAV_LINKS = [
    ("Tools", "/"),
    ("YouTube Money", "/youtube-money-calculator/"),
    ("Twitch Bits", "/twitch-bits-to-usd/"),
    ("Views to Money", "/views-to-money-calculator/"),
    ("RPM vs CPM", "/cpm-vs-rpm/"),
]

LEGAL_PAGES = [
    {
        "route": "/privacy-policy",
        "title": "Privacy Policy | CreatorPayCalc.com",
        "description": "Privacy policy for CreatorPayCalc.com: 100% client-side calculations, Google AdSense cookie disclosure, GA4 & Clarity analytics, CCPA/GDPR rights.",
        "h1": "Privacy Policy",
        "body": """
<p>At CreatorPayCalc.com, we respect your privacy and are committed to transparent, responsible data practices. This Privacy Policy explains our client-side computing architecture, how we collect anonymous usage data, and our disclosures regarding third-party advertising cookies in full compliance with Google AdSense policies, CCPA, and GDPR.</p>
<h2>1. 100% Client-Side Calculations</h2>
<p>All earnings estimates — views, RPM, CPM, Twitch Bits, subscription payouts, tax take-home — are computed 100% locally in your web browser using client-side JavaScript. We do not store, log, or transmit your input numbers to any remote server or database.</p>
<h2>2. Google AdSense &amp; Third-Party Advertising Cookies</h2>
<p>We partner with third-party vendors, including Google LLC, to serve advertisements when you visit our website. These companies may use cookies, web beacons, and related tracking technologies to serve ads based on your prior visits to CreatorPayCalc.com or other sites on the Internet.</p>
<ul>
  <li>Google's use of advertising cookies enables it and its partners to serve personalized ads to users based on their visit to CreatorPayCalc.com and/or other sites on the Internet.</li>
  <li>Users may opt out of personalized advertising at any time by visiting <a href="https://www.google.com/settings/ads" rel="noopener noreferrer">Google Ads Settings</a>.</li>
  <li>Alternatively, you can opt out of a third-party vendor's use of cookies for personalized advertising by visiting <a href="http://www.aboutads.info/choices/" rel="noopener noreferrer">aboutads.info</a>.</li>
</ul>
<h2>3. Web Analytics (Google Analytics &amp; Microsoft Clarity)</h2>
<p>We use Google Analytics 4 and Microsoft Clarity to understand aggregate visitor patterns, such as calculator modes used, device screen resolutions, and general geographic regions. Clarity captures anonymized interaction metrics (heatmaps, scroll depth) to help us improve the calculator interface. These analytics tools do not collect personally identifiable information (PII).</p>
<h2>4. California Consumer Privacy Act (CCPA) &amp; GDPR</h2>
<p>Under CCPA and GDPR regulations, users have the right to request information about data collection and opt out of third-party cookie tracking. Because we do not sell personal information or maintain user accounts, our data collection is limited exclusively to anonymous technical telemetry and standard advertising cookies described above.</p>
<h2>5. Contact Us</h2>
<p>If you have any questions about this Privacy Policy or wish to report a privacy concern, please contact us via email at <a href="mailto:support@creatorpaycalc.com">support@creatorpaycalc.com</a>.</p>
""",
    },
    {
        "route": "/terms-of-service",
        "title": "Terms of Service | CreatorPayCalc.com",
        "description": "Terms of Service and earnings disclaimers for CreatorPayCalc.com calculators and benchmarks.",
        "h1": "Terms of Service &amp; Earnings Disclaimers",
        "body": """
<p>Welcome to CreatorPayCalc.com. By accessing or using our free web-based calculators and guides, you agree to comply with and be bound by the following Terms of Service.</p>
<h2>1. Estimation Disclaimer</h2>
<p>All earnings figures, RPM/CPM ranges, Bit payout rates, and tax take-home estimates provided on CreatorPayCalc.com are planning ranges for educational purposes only. They are not guarantees of actual platform payouts. Real earnings depend on many factors outside our control, including your audience geography, content niche, monetization eligibility, ad demand, and platform policy changes.</p>
<h2>2. Data Sources &amp; Accuracy</h2>
<p>Benchmarks are compiled from publicly reported creator data and platform documentation, with source and update dates disclosed on each page. Figures may change at any time; always check your platform dashboard (e.g., YouTube Studio) for authoritative numbers once you have 90+ days of data.</p>
<h2>3. Not Financial, Tax, or Legal Advice</h2>
<p>Tax take-home estimates use a simplified self-employment model and do not account for deductions, entity structures, or jurisdiction-specific rules. Consult a qualified professional for decisions involving real money.</p>
<h2>4. Limitation of Liability</h2>
<p>In no event shall CreatorPayCalc.com or its maintainers be liable for any direct, indirect, incidental, special, or consequential damages arising from the use of this free tool suite or reliance on its estimates.</p>
<h2>5. Intellectual Property &amp; License</h2>
<p>The text, interactive layout, branding, and mathematical implementation of CreatorPayCalc.com are protected by copyright. You may use this tool freely for personal and commercial planning purposes.</p>
<h2>6. Contact</h2>
<p>Questions about these terms can be sent to <a href="mailto:support@creatorpaycalc.com">support@creatorpaycalc.com</a>.</p>
""",
    },
    {
        "route": "/about",
        "title": "About Us &amp; Methodology | CreatorPayCalc.com",
        "description": "Learn about CreatorPayCalc.com, our RPM/CPM estimation methodology, and why we built this free creator earnings calculator suite.",
        "h1": "About Us &amp; Methodology",
        "body": """
<p>CreatorPayCalc.com is an independent, ad-supported suite of free calculators for content creators: estimate what your YouTube, Twitch, TikTok and other content is really worth, and what you keep after tax.</p>
<h2>Why We Built CreatorPayCalc.com</h2>
<p>Most "money calculator" widgets are one-trick ponies: they hard-code a single RPM, ignore audience country, ignore the difference between CPM and RPM, and never show tax take-home. We built a different tool:</p>
<ul>
  <li><b>Multi-platform:</b> YouTube long-form &amp; Shorts, Twitch Bits and subs, TikTok Creator Rewards, views-to-money.</li>
  <li><b>Multi-stream:</b> model ads + sponsorships + memberships/Shop together, not just ad revenue.</li>
  <li><b>Country-aware:</b> US audiences are worth roughly 4.3× the worldwide average per view; India about 0.24×.</li>
  <li><b>Tax take-home:</b> see what you keep after simplified US self-employment tax.</li>
  <li><b>Reverse targets:</b> how many views to hit a $1,000/month goal at your RPM.</li>
</ul>
<h2>Our Estimation Methodology</h2>
<p>Earnings = (monthly views ÷ 1,000) × RPM. RPM (revenue per 1,000 views, after the platform's cut and non-monetized views) is the number creators should negotiate with — not CPM, which is what advertisers pay before the platform share (YouTube keeps roughly 45%). Benchmarks are compiled from publicly reported creator data and platform documentation, updated October 2026, with per-page source and update disclosures.</p>
<h2>Contact</h2>
<p>Questions or corrections: <a href="mailto:support@creatorpaycalc.com">support@creatorpaycalc.com</a>.</p>
""",
    },
    {
        "route": "/contact",
        "title": "Contact Us | CreatorPayCalc.com",
        "description": "Contact the CreatorPayCalc.com team about corrections, data sources, or partnership questions.",
        "h1": "Contact Us",
        "body": """
<p>We welcome corrections, source suggestions, and partnership questions.</p>
<ul>
  <li><b>Email:</b> <a href="mailto:support@creatorpaycalc.com">support@creatorpaycalc.com</a></li>
  <li><b>Data corrections:</b> if you have verified platform payout data that differs from our benchmarks, tell us and we will review and update.</li>
  <li><b>Response time:</b> typically within 3 business days.</li>
</ul>
""",
    },
]


def base_page(
    *,
    title: str,
    description: str,
    canonical: str,
    h1: str,
    body: str,
    jsonld: Dict,
    breadcrumb: str = "",
) -> str:
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<link rel="canonical" href="{SITE_URL}{canonical}">
<meta name="robots" content="index, follow">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(description)}">
<meta property="og:url" content="{SITE_URL}{canonical}">
<link rel="stylesheet" href="/css/site.css?v=20261014">
<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>
</head>
<body>
<header class="site-header">
  <div class="wrap">
    <a class="brand" href="/">{SITE_NAME} <span class="brand-sub">creator earnings hub</span></a>
    <nav aria-label="Main">
      <ul>
        {''.join(f'<li><a href="{u}">{t}</a></li>' for t, u in NAV_LINKS)}
      </ul>
    </nav>
  </div>
</header>
{breadcrumb}
<main class="wrap">
<h1>{h1}</h1>
{body}
</main>
<footer class="site-footer">
  <div class="wrap">
    <p>{SITE_NAME} — free creator earnings calculators. Estimates are planning ranges, not guaranteed payouts.
       Data sources and update dates are disclosed on each page.</p>
    <nav aria-label="Footer">
      <ul>
        {''.join(f'<li><a href="{u}">{t}</a></li>' for t, u in NAV_LINKS)}
        {''.join(f'<li><a href="{p["route"]}">{p["h1"]}</a></li>' for p in LEGAL_PAGES)}
        <li><a href="/sitemap.xml">Sitemap</a></li>
      </ul>
    </nav>
  </div>
</footer>
</body>
</html>"""
    return inject_analytics(page)


def calc_js() -> str:
    """通用计算脚本（原生 JS，十进制字符串运算避免浮点误差）。"""
    return r"""
<script>
function mulStr(a,b){ /* decimal-string multiplication (6-dp precision) */
  const fa=BigInt((a.split('.')[1]||'').padEnd(6,'0')); const ia=BigInt((a.split('.')[0]||'0')||'0');
  const fb=BigInt((b.split('.')[1]||'').padEnd(6,'0')); const ib=BigInt((b.split('.')[0]||'0')||'0');
  const ra=ia*1000000n+fa, rb=ib*1000000n+fb;
  const r=ra*rb/1000000000000n;
  return (r/1000000n).toString()+'.'+String(r%1000000n).padStart(6,'0').slice(0,2);
}
function fmtUSD(x){ const n=Number(x); return '$'+n.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}); }
function fmtNum(x){ return Number(x).toLocaleString('en-US'); }
function calcRpm(){ const v=document.getElementById('rpm_views').value.replace(/[^\d]/g,'')||'0';
  const r=document.getElementById('rpm_rate').value.replace(/[^\d.]/g,'')||'0';
  const e=(Number(v)/1000)*Number(r);
  document.getElementById('rpm_out').textContent=fmtUSD(e);
  document.getElementById('rpm_eff').textContent='RPM: '+fmtUSD(r)+' per 1,000 views · '+fmtNum(v)+' views';
  const need=(1000/Number(r))*1000; document.getElementById('rpm_need').textContent=fmtNum(Math.ceil(need)); }
function calcBits(){ const b=document.getElementById('bits_count').value.replace(/[^\d]/g,'')||'0';
  const stream=(Number(b)*0.01);
  const packs=[[25000,308],[10000,126],[5000,64.4],[1500,19.95],[500,7],[100,1.4]];
  let rem=Number(b), cost=0, mix=[];
  for(const [sz,pr] of packs){ if(rem<=0)break; const c=Math.floor(rem/sz); if(c){mix.push(c+'x '+sz.toLocaleString()); cost+=pr*c; rem-=sz*c;} }
  if(rem>0){mix.push('1x 100'); cost+=1.4;}
  document.getElementById('bits_streamer').textContent=fmtUSD(stream);
  document.getElementById('bits_viewer').textContent=fmtUSD(cost)+' ('+mix.join(' + ')+')';
  document.getElementById('bits_twitch').textContent=fmtUSD(cost-stream); }
function calcViews(){ const t=document.getElementById('v2m_target').value.replace(/[^\d.]/g,'')||'0';
  const r=document.getElementById('v2m_rpm').value.replace(/[^\d.]/g,'')||'0';
  const need=(Number(t)/Number(r))*1000;
  document.getElementById('v2m_out').textContent=fmtNum(Math.ceil(need));
  document.getElementById('v2m_line').textContent='At '+fmtUSD(r)+' RPM, '+fmtUSD(t)+' needs about '+fmtNum(Math.ceil(need))+' views.'; }
</script>"""


# ---------------------------------------------------------------------------
# 工具页（含 SSR 示例数字）
# ---------------------------------------------------------------------------

def page_youtube_money() -> str:
    demo = rpm_to_earnings(d("100000"), d("4.00"))
    demo_hi = rpm_to_earnings(d("100000"), d("17.00"))
    need = earnings_to_views(d("1000"), d("4.00"))
    body = f"""
<p>YouTube doesn't pay a flat rate per view. Your earnings depend on <strong>RPM</strong>
(revenue per 1,000 views, after YouTube's 45% share), which changes with your <strong>niche</strong>
and <strong>audience country</strong>. This calculator estimates long-form and Shorts earnings,
then shows what you keep after US self-employment tax.</p>

<h2>YouTube Money Calculator</h2>
<div class="calc">
  <label for="rpm_views">Monthly views</label>
  <input id="rpm_views" type="text" value="100000" oninput="calcRpm()">
  <label for="rpm_rate">RPM (USD per 1,000 views)</label>
  <input id="rpm_rate" type="text" value="4.00" oninput="calcRpm()">
  <p class="calc-out" id="rpm_out">$400.00</p>
  <p id="rpm_eff" class="calc-line">RPM: $4.00 per 1,000 views · 100,000 views</p>
  <p class="calc-line">Views needed for $1,000/month: <strong id="rpm_need">250,000</strong></p>
</div>

<h2>Worked example (server-rendered, Decimal precision)</h2>
<table>
  <thead><tr><th>Scenario</th><th>Monthly views</th><th>RPM</th><th>Monthly earnings</th></tr></thead>
  <tbody>
    <tr><td>General niche, worldwide</td><td>100,000</td><td>$4.00</td><td>{usd(demo)}</td></tr>
    <tr><td>Finance niche, US-heavy</td><td>100,000</td><td>$17.00</td><td>{usd(demo_hi)}</td></tr>
    <tr><td>Target $1,000/mo at $4 RPM</td><td>—</td><td>$4.00</td><td>needs {fmt_int(need)} views</td></tr>
  </tbody>
</table>

<h2>2026 RPM benchmarks by niche (creator share)</h2>
<table>
  <thead><tr><th>Niche</th><th>RPM range (long-form)</th></tr></thead>
  <tbody>
    {''.join(f'<tr><td>{NICHE_LABELS.get(n, n)}</td><td>${lo:g}–${hi:g}</td></tr>' for n, (lo, hi) in RPM_LIBRARY["youtube_long_form"].items())}
  </tbody>
</table>
<p>Country multiplier example: a US audience is worth about <strong>4.3×</strong> a worldwide average audience
per view; India about 0.24×. See the <a href="/cpm-vs-rpm/">RPM vs CPM</a> guide for the full model.</p>

<h2>How the math works</h2>
<p><code>Monthly earnings = (monthly views ÷ 1,000) × RPM</code>. RPM already includes YouTube's 45% cut and
non-monetized views. Shorts run on a separate pooled model around $0.02–$0.15 per 1,000 views.</p>

<h2>Frequently asked questions</h2>
<h3>How much does YouTube pay per 1,000 views?</h3>
<p>Between about $1 and $30 for long-form, with most channels in the low single digits. Finance/business
niches with US-heavy audiences reach $15+ per 1,000 views; entertainment sits near $1–$4.</p>
<h3>Are these numbers guaranteed?</h3>
<p>No — they are planning ranges from public creator reports (sources disclosed, updated {RPM_LIBRARY['updated']}).
Use your own YouTube Studio RPM when you have 90+ days of data.</p>
<h3>How many views do I need for $1,000/month?</h3>
<p>At a $4 RPM, about 250,000 monthly views. At a $15 finance-tier RPM, roughly 67,000.</p>

<h2>Related tools</h2>
<ul>
  <li><a href="/views-to-money-calculator/">Views to Money Calculator</a> — flip the question around.</li>
  <li><a href="/cpm-vs-rpm/">RPM vs CPM explained</a></li>
</ul>
"""
    return base_page(
        title="YouTube Money Calculator — Estimate Earnings from Views & RPM (2026)",
        description="Free YouTube money calculator: estimate long-form & Shorts earnings from views and RPM, by niche and audience country, with US tax take-home. 2026 benchmarks.",
        canonical="/youtube-money-calculator/",
        h1="YouTube Money Calculator",
        body=body + calc_js(),
        jsonld={
            "@context": "https://schema.org",
            "@type": "WebApplication",
            "name": "YouTube Money Calculator",
            "url": f"{SITE_URL}/youtube-money-calculator/",
            "applicationCategory": "FinanceApplication",
            "description": "Estimate YouTube channel earnings from views, RPM, niche and audience country.",
        },
    )


def page_twitch_bits() -> str:
    rows = []
    for bits in (100, 1000, 5000, 10000, 25000, 100000):
        s = bits_streamer_earnings(d(bits))
        v = viewer_cost(bits)
        rows.append((bits, usd(s), usd(v), usd(v - s)))
    body = f"""
<p>A Twitch Bit is two different numbers depending on which side you're on. A viewer buying Bits pays
Twitch's bundle price; the streamer who receives a cheer is paid a flat <strong>$0.01 per Bit</strong>.
This calculator shows both sides and finds the cheapest bundle mix.</p>

<h2>Twitch Bits to USD Calculator</h2>
<div class="calc">
  <label for="bits_count">Bits</label>
  <input id="bits_count" type="text" value="1000" oninput="calcBits()">
  <p class="calc-line">Streamer earns: <strong id="bits_streamer">$10.00</strong></p>
  <p class="calc-line">Viewer pays (cheapest pack mix): <strong id="bits_viewer">$14.00 (1x 1,000)</strong></p>
  <p class="calc-line">Twitch keeps: <strong id="bits_twitch">$4.00</strong></p>
</div>

<h2>Quick reference (server-rendered)</h2>
<table>
  <thead><tr><th>Bits</th><th>Streamer earns</th><th>Viewer pays (cheapest mix)</th><th>Twitch keeps</th></tr></thead>
  <tbody>
    {''.join(f'<tr><td>{b:,}</td><td>{s}</td><td>{v}</td><td>{t}</td></tr>' for b, s, v, t in rows)}
  </tbody>
</table>

<h2>Why there are two numbers</h2>
<p>Twitch sells Bits in fixed packs (100 / 500 / 1,500 / 5,000 / 10,000 / 25,000). The price per Bit drops
as the pack grows (from $0.014 to $0.01232 at the US web base rate). The streamer always receives $0.01 per
Bit cheered — there is no partner-tier split for Bits, unlike subscriptions.</p>

<h2>Cheapest pack solver</h2>
<p>For an arbitrary amount, buying the largest packs first is cheapest. Example: 6,500 Bits at 100-pack
pricing costs $91.00; the cheapest mix (one 5,000 + three 500) costs $85.40 — the solver above does this
for any amount. Mobile in-app purchases add roughly 30% for Apple/Google commissions.</p>

<h2>Bits vs subs for the streamer</h2>
<p>Per dollar the viewer spends, Bits are the more efficient gift: about 71% reaches the streamer, versus
50% for a standard-split sub. But subs recur monthly — a Tier 1 sub pays $2.50/month until it lapses.
Most streamers treat subs as the predictable floor and Bits as the volatile upside (typically 20–40% on top).</p>

<h2>Frequently asked questions</h2>
<h3>How much is 1,000 bits on Twitch?</h3>
<p>Exactly $10.00 to the streamer. Viewers pay about $14.00 to buy them.</p>
<h3>Do streamers keep 100% of Bits?</h3>
<p>At the cheer stage yes — $0.01 per Bit goes to the streamer. Twitch takes its margin when the viewer buys.</p>
<h3>How many Bits can be cheered at once?</h3>
<p>Up to 100,000 Bits ($1,000 to the streamer) in a single cheer.</p>

<h2>Related pages</h2>
<ul>
  <li><a href="/twitch-bits-to-usd/1000/">How much is 1,000 Twitch Bits?</a></li>
  <li><a href="/twitch-bits-to-usd/5000/">How much is 5,000 Twitch Bits?</a></li>
  <li><a href="/twitch-bits-to-usd/10000/">How much is 10,000 Twitch Bits?</a></li>
  <li><a href="/twitch-bits-to-usd/25000/">How much is 25,000 Twitch Bits?</a></li>
  <li><a href="/twitch-bits-to-usd/100000/">How much is 100,000 Twitch Bits?</a></li>
</ul>
"""
    return base_page(
        title="Twitch Bits to USD Calculator — Streamer Payout & Cheapest Bundle Mix (2026)",
        description="Convert Twitch Bits to USD both ways: exact $0.01/Bit streamer payout, viewer bundle cost, and the cheapest pack mix. Quick reference for 100–1,000,000 Bits.",
        canonical="/twitch-bits-to-usd/",
        h1="Twitch Bits to USD Calculator",
        body=body + calc_js(),
        jsonld={
            "@context": "https://schema.org",
            "@type": "WebApplication",
            "name": "Twitch Bits to USD Calculator",
            "url": f"{SITE_URL}/twitch-bits-to-usd/",
            "applicationCategory": "FinanceApplication",
            "description": "Convert Twitch Bits to USD: streamer payout and viewer bundle cost with cheapest pack solver.",
        },
    )


def page_bits_amount(bits: int) -> str:
    s = usd(bits_streamer_earnings(d(bits)))
    v = usd(viewer_cost(bits))
    keep = usd(viewer_cost(bits) - bits_streamer_earnings(d(bits)))
    title = f"How Much is {bits:,} Twitch Bits? (Equals {s})"
    body = f"""
<p><strong>{bits:,} Twitch Bits equals {s} to the streamer.</strong> Viewers pay about {v} to buy them
(the cheapest bundle mix), and Twitch keeps about {keep}. The streamer rate is a fixed $0.01 per Bit —
no tier, no split, no partner status changes it.</p>

<h2>Quick math</h2>
<p><code>Streamer earnings = Bits × $0.01</code>. <code>Viewer cost</code> uses the cheapest mix of Twitch's
packs (100 / 500 / 1,500 / 5,000 / 10,000 / 25,000 Bits), so the viewer column is a ceiling for big cheers.</p>

<h2>Related conversions</h2>
<ul>
  {''.join(f'<li><a href="/twitch-bits-to-usd/{b}/">How much is {b:,} Twitch Bits?</a></li>' for b in (100, 1000, 5000, 10000, 25000, 100000))}
  <li><a href="/twitch-bits-to-usd/">Twitch Bits to USD Calculator</a></li>
</ul>
"""
    return base_page(
        title=title,
        description=f"{bits:,} Twitch Bits = {s} to the streamer (flat $0.01/Bit); viewers pay about {v}. Check any amount with the free Bits calculator.",
        canonical=f"/twitch-bits-to-usd/{bits}/",
        h1=f"How Much is {bits:,} Twitch Bits?",
        body=body,
        jsonld={
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [{
                "@type": "Question",
                "name": f"How much is {bits:,} Twitch Bits?",
                "acceptedAnswer": {"@type": "Answer", "text": f"{bits:,} Twitch Bits equals {s} to the streamer. Viewers pay about {v} to buy them."},
            }],
        },
    )


def page_views_to_money() -> str:
    demo = rpm_to_earnings(d("100000"), d("5.00"))
    need = earnings_to_views(d("1000"), d("5.00"))
    body = f"""
<p>How much are your views actually worth? Enter a view count and a per-thousand rate (RPM), and this
calculator estimates earnings — or flip it: tell it how much you want to earn and it works out the views.</p>

<h2>Views to Money Calculator</h2>
<div class="calc">
  <label for="v2m_target">Target monthly earnings ($)</label>
  <input id="v2m_target" type="text" value="1000" oninput="calcViews()">
  <label for="v2m_rpm">RPM (USD per 1,000 views)</label>
  <input id="v2m_rpm" type="text" value="5.00" oninput="calcViews()">
  <p class="calc-out" id="v2m_out">200,000</p>
  <p class="calc-line" id="v2m_line">At $5.00 RPM, $1,000 needs about 200,000 views.</p>
</div>

<h2>Worked examples (server-rendered)</h2>
<table>
  <thead><tr><th>Views</th><th>RPM</th><th>Earnings</th></tr></thead>
  <tbody>
    <tr><td>100,000</td><td>$5.00</td><td>{usd(demo)}</td></tr>
    <tr><td>1,000,000</td><td>$5.00</td><td>{usd(rpm_to_earnings(d("1000000"), d("5.00")))}</td></tr>
    <tr><td>$1,000 target</td><td>$5.00</td><td>{fmt_int(need)} views</td></tr>
  </tbody>
</table>

<h2>Long-form vs Shorts</h2>
<p>Long-form video (YouTube) keeps 55% of ad revenue and typically pays $1–$17 RPM by niche. Shorts run on a
pooled model around <strong>$0.02–$0.15 per 1,000 views</strong> — 30 to 100 times less. TikTok Creator
Rewards and Instagram Reels sit in a similar short-form range. Pick your platform's effective per-thousand
rate and the formula works anywhere.</p>

<h2>How to find your real RPM</h2>
<p>YouTube Studio → Analytics → Revenue shows your actual RPM. TikTok's Creator Rewards dashboard shows its
per-1,000-qualified-views rate. Replace the benchmark with your real number for an exact figure.</p>

<h2>Frequently asked questions</h2>
<h3>How many views do I need to make $1,000 a month?</h3>
<p>Divide $1,000 by your RPM and multiply by 1,000. At a $5 RPM that's 200,000 monthly views; at a $15
finance-tier RPM, about 67,000.</p>
<h3>Does this work for TikTok or Instagram?</h3>
<p>Yes — the math is platform-agnostic: views × your per-thousand rate ÷ 1,000. Just enter that platform's
effective rate, which is far lower than YouTube long-form.</p>

<h2>Related tools</h2>
<ul>
  <li><a href="/youtube-money-calculator/">YouTube Money Calculator</a></li>
  <li><a href="/cpm-vs-rpm/">RPM vs CPM explained</a></li>
</ul>
"""
    return base_page(
        title="Views to Money Calculator — How Many Views Make $1,000? (2026)",
        description="Free views to money calculator: estimate earnings from views and RPM, or work backwards from a target income. Long-form vs Shorts benchmarks included.",
        canonical="/views-to-money-calculator/",
        h1="Views to Money Calculator",
        body=body + calc_js(),
        jsonld={
            "@context": "https://schema.org",
            "@type": "WebApplication",
            "name": "Views to Money Calculator",
            "url": f"{SITE_URL}/views-to-money-calculator/",
            "applicationCategory": "FinanceApplication",
            "description": "Estimate content earnings from views and RPM, or reverse-calculate the views needed for a target income.",
        },
    )


def page_cpm_vs_rpm() -> str:
    body = f"""
<p>CPM and RPM sound alike and are routinely confused. The difference decides how much money actually
lands in your pocket.</p>

<h2>The one-line difference</h2>
<table>
  <thead><tr><th>Metric</th><th>Who pays / who earns</th><th>Formula</th><th>Typical (YouTube, 2026)</th></tr></thead>
  <tbody>
    <tr><td><strong>CPM</strong></td><td>What advertisers pay per 1,000 ad impressions</td><td>(ad spend ÷ impressions) × 1,000</td><td>$4–$20 by niche</td></tr>
    <tr><td><strong>RPM</strong></td><td>What you earn per 1,000 views, after YouTube's 45% share</td><td>(revenue ÷ views) × 1,000</td><td>$1–$17 by niche</td></tr>
  </tbody>
</table>
<p>A $10 CPM does <strong>not</strong> become $10 of your money. YouTube keeps 45% of long-form ad revenue
(creator share 55%), and not every view is monetized (ad blockers, Premium, limited-ads videos). That is why
a channel can see a $20 CPM in Studio and an RPM closer to $5.</p>

<h2>The conversion</h2>
<p><code>RPM ≈ CPM × monetized share × creator share</code>. Example: $10 CPM, 60% monetized views,
55% creator share → $10 × 0.60 × 0.55 = $3.30 effective RPM.</p>

<h2>Why creators should negotiate with RPM</h2>
<p>When a brand offers you a sponsored video, quote your real RPM (total revenue ÷ total views × 1,000),
not the CPM shown in YouTube Analytics — Studio's CPM is a platform-wide average, not your rate. Misquoting
is a common and costly mistake.</p>

<h2>Short-form is a different game</h2>
<p>YouTube Shorts, TikTok Creator Rewards and Instagram Reels pay far less per 1,000 views ($0.02–$1.00)
because of pooled revenue models and lower advertiser demand. See the <a href="/views-to-money-calculator/">Views to Money</a>
calculator for platform-agnostic math.</p>

<h2>Related tools</h2>
<ul>
  <li><a href="/youtube-money-calculator/">YouTube Money Calculator</a></li>
  <li><a href="/views-to-money-calculator/">Views to Money Calculator</a></li>
</ul>
"""
    return base_page(
        title="RPM vs CPM for Creators — What's the Difference? (2026)",
        description="RPM vs CPM explained for creators: what advertisers pay vs what you earn, the 45% YouTube share, and why you should negotiate with RPM, not CPM.",
        canonical="/cpm-vs-rpm/",
        h1="RPM vs CPM: What Creators Actually Earn",
        body=body,
        jsonld={
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "RPM vs CPM for Creators",
            "url": f"{SITE_URL}/cpm-vs-rpm/",
            "dateModified": RPM_LIBRARY["updated"],
        },
    )


def page_tiktok_money() -> str:
    body = f"""
<p>TikTok's Creator Rewards pays per 1,000 <em>qualified</em> views — typically $0.04–$1.00, far below
YouTube long-form. This page compares what short-form actually pays against long-form, so you can price
your content and time honestly.</p>

<h2>TikTok vs YouTube per 1,000 views (2026 benchmarks)</h2>
<table>
  <thead><tr><th>Format</th><th>Per 1,000 views</th><th>Model</th></tr></thead>
  <tbody>
    <tr><td>YouTube long-form</td><td>$1–$17 (by niche)</td><td>55% creator share of ad revenue</td></tr>
    <tr><td>YouTube Shorts</td><td>$0.02–$0.15</td><td>Pooled revenue</td></tr>
    <tr><td>TikTok Creator Rewards</td><td>$0.04–$1.00</td><td>Per qualified view</td></tr>
    <tr><td>Instagram Reels</td><td>$0.03–$0.30</td><td>Bonus / ad-share programs</td></tr>
  </tbody>
</table>

<h2>The qualified-views trap</h2>
<p>Not every TikTok play pays. Eligible content, For You feed delivery and watch behavior all matter —
your Creator Rewards dashboard RPM is the only real number. As a planning estimate: 1,000,000 qualified
views at $0.40 RPM ≈ $400; at $0.70 RPM ≈ $700.</p>

<h2>Why creators stack income streams</h2>
<p>TikTok's real money is often sponsorship + LIVE gifts + TikTok Shop, not the Rewards pool. Mid-tier
creators earn 5–20× more from brand deals than from ad revenue alone. Model the full picture across all
your income streams.</p>

<h2>Frequently asked questions</h2>
<h3>How much does TikTok pay per 1,000 views?</h3>
<p>TikTok does not publish one fixed rate. Creator Rewards benchmarks range $0.04–$1.00 per 1,000 qualified
views depending on niche and audience country; use your dashboard RPM for your actual figure.</p>
<h3>How much is 1 million TikTok views worth?</h3>
<p>At a $0.40 RPM, about $400; at $0.70 RPM, about $700 — before sponsorships, gifts and Shop commissions.</p>

<h2>Related tools</h2>
<ul>
  <li><a href="/views-to-money-calculator/">Views to Money Calculator</a></li>
  <li><a href="/youtube-money-calculator/">YouTube Money Calculator</a></li>
</ul>
"""
    return base_page(
        title="TikTok Money Calculator — Creator Rewards vs YouTube (2026)",
        description="TikTok Creator Rewards benchmark ($0.04–$1.00 per 1,000 qualified views) compared with YouTube long-form and Shorts, plus how to stack TikTok income streams.",
        canonical="/tiktok-money-calculator/",
        h1="TikTok Money Calculator — Honest Short-Form Benchmarks",
        body=body,
        jsonld={
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "TikTok Money Calculator",
            "url": f"{SITE_URL}/tiktok-money-calculator/",
            "dateModified": RPM_LIBRARY["updated"],
        },
    )


def page_youtube_rpm() -> str:
    demo = rpm_to_earnings(d("200000"), d("8.00"))
    need = earnings_to_views(d("5000"), d("8.00"))
    body = f"""
<p>RPM (revenue per mille) is the single most useful number in a YouTube channel: <strong>what you earn per
1,000 views after YouTube's 45% share</strong>. This calculator converts RPM ↔ earnings in both directions.
(Not an engine RPM calculator — that's a different tool entirely.)</p>

<h2>YouTube RPM Calculator</h2>
<div class="calc">
  <label for="rpm_views">Monthly views</label>
  <input id="rpm_views" type="text" value="200000" oninput="calcRpm()">
  <label for="rpm_rate">RPM (USD per 1,000 views)</label>
  <input id="rpm_rate" type="text" value="8.00" oninput="calcRpm()">
  <p class="calc-out" id="rpm_out">$1,600.00</p>
  <p class="calc-line" id="rpm_eff">RPM: $8.00 per 1,000 views · 200,000 views</p>
  <p class="calc-line">Views needed for $5,000/month: <strong id="rpm_need">625,000</strong></p>
</div>

<h2>Worked examples (server-rendered)</h2>
<table>
  <thead><tr><th>Scenario</th><th>Views</th><th>RPM</th><th>Monthly earnings</th></tr></thead>
  <tbody>
    <tr><td>Gaming channel</td><td>200,000</td><td>$8.00</td><td>{usd(demo)}</td></tr>
    <tr><td>Finance channel</td><td>100,000</td><td>$15.00</td><td>{usd(rpm_to_earnings(d("100000"), d("15.00")))}</td></tr>
    <tr><td>Target $5,000/mo at $8 RPM</td><td>—</td><td>$8.00</td><td>needs {fmt_int(need)} views</td></tr>
  </tbody>
</table>

<h2>RPM by niche (2026, creator share)</h2>
<table>
  <thead><tr><th>Niche</th><th>RPM range (long-form)</th></tr></thead>
  <tbody>
    {''.join(f'<tr><td>{NICHE_LABELS.get(n, n)}</td><td>${lo:g}–${hi:g}</td></tr>' for n, (lo, hi) in RPM_LIBRARY["youtube_long_form"].items())}
  </tbody>
</table>

<h2>How to raise your RPM</h2>
<ul>
  <li><strong>Audience geography:</strong> US/UK/CA/AU viewers are worth 3–4× the worldwide average (see <a href="/cpm-vs-rpm/">RPM vs CPM</a> for multipliers).</li>
  <li><strong>Niche:</strong> finance, tech and B2B niches command 3–8× entertainment RPM.</li>
  <li><strong>Monetization:</strong> 8+ minute videos unlock mid-roll ads and lift RPM 30–60%.</li>
  <li><strong>Seasonality:</strong> Q4 CPMs run 30–80% above Q1.</li>
</ul>

<h2>Frequently asked questions</h2>
<h3>What is a good RPM on YouTube?</h3>
<p>For long-form, under $2 is weak, $2–$5 is typical, $5–$10 is strong, $15+ is exceptional and niche-driven
(finance, tech, US audiences). Shorts RPM is structurally lower ($0.02–$0.15).</p>
<h3>How do I find my RPM?</h3>
<p>YouTube Studio → Analytics → Revenue. That number is already your creator-share RPM; divide by 1,000 for
per-view.</p>

<h2>Related tools</h2>
<ul>
  <li><a href="/youtube-money-calculator/">YouTube Money Calculator</a></li>
  <li><a href="/views-to-money-calculator/">Views to Money Calculator</a></li>
  <li><a href="/cpm-vs-rpm/">RPM vs CPM explained</a></li>
</ul>
"""
    return base_page(
        title="YouTube RPM Calculator — Revenue Per 1,000 Views (2026)",
        description="Convert YouTube RPM to monthly earnings and reverse. RPM benchmarks by niche, US audience multipliers, and how to raise your revenue per 1,000 views.",
        canonical="/youtube-rpm-calculator/",
        h1="YouTube RPM Calculator",
        body=body + calc_js(),
        jsonld={
            "@context": "https://schema.org",
            "@type": "WebApplication",
            "name": "YouTube RPM Calculator",
            "url": f"{SITE_URL}/youtube-rpm-calculator/",
            "applicationCategory": "FinanceApplication",
            "description": "Convert YouTube RPM to monthly earnings and reverse-calculate views.",
        },
    )


def page_twitch_sub_calc() -> str:
    t1 = money(d("100") * d("2.50"))
    t3 = money(d("30") * d("12.50"))
    total = money(d("100") * d("2.50") + d("30") * d("12.50"))
    body = f"""
<p>Twitch subscriptions pay the streamer a fixed monthly amount per active sub, depending on tier.
Standard split is <strong>50% of the list price</strong> (Tier 1 $4.99 → $2.50, Tier 2 $9.99 → $5.00,
Tier 3 $24.99 → $12.50). Prime subs count like Tier 1 subs but with a variable token value. This
calculator rolls up monthly sub revenue and shows take-home.</p>

<h2>Twitch Subscription Calculator</h2>
<div class="calc">
  <label for="sub_t1">Tier 1 subs (incl. Prime)</label>
  <input id="sub_t1" type="text" value="100" oninput="calcSubs()">
  <label for="sub_t2">Tier 2 subs</label>
  <input id="sub_t2" type="text" value="0" oninput="calcSubs()">
  <label for="sub_t3">Tier 3 subs</label>
  <input id="sub_t3" type="text" value="30" oninput="calcSubs()">
  <p class="calc-out" id="sub_out">$625.00</p>
  <p class="calc-line" id="sub_line">Tier1: $250.00 · Tier2: $0.00 · Tier3: $375.00</p>
  <p class="calc-line">Standard 50% split; partner/higher splits differ.</p>
</div>

<h2>Worked example (server-rendered)</h2>
<table>
  <thead><tr><th>Subs</th><th>Tier</th><th>Streamer monthly</th></tr></thead>
  <tbody>
    <tr><td>100</td><td>Tier 1</td><td>{usd(t1)}</td></tr>
    <tr><td>30</td><td>Tier 3</td><td>{usd(t3)}</td></tr>
    <tr><th>Total</th><th>—</th><th>{usd(total)}</th></tr>
  </tbody>
</table>

<h2>Why subs matter more than views</h2>
<p>Subscriptions are the <strong>predictable floor</strong> of a streaming income: they recur monthly and are
less volatile than ads or tips. A 1,000-sub Tier-1 channel earns about $2,500/month from subs alone — roughly
equivalent to 300k–600k YouTube long-form views per month. Add <a href="/twitch-bits-to-usd/">Bits</a> as the
variable upside (typically 20–40% on top).</p>

<h2>Frequently asked questions</h2>
<h3>How much does Twitch pay per sub?</h3>
<p>Standard split: $2.50 (Tier 1), $5.00 (Tier 2), $12.50 (Tier 3) per sub per month. Partners can negotiate
higher splits; Prime subs pay a variable token value (historically ~$2.50).</p>
<h3>Do gifted subs pay the same?</h3>
<p>Yes — a gifted Tier 1 sub pays the streamer the same $2.50/month for its duration.</p>

<h2>Related tools</h2>
<ul>
  <li><a href="/twitch-bits-to-usd/">Twitch Bits to USD</a></li>
  <li><a href="/youtube-money-calculator/">YouTube Money Calculator</a></li>
</ul>
"""
    js = r"""
<script>
function calcSubs(){ const t1=Number(document.getElementById('sub_t1').value.replace(/[^\d]/g,'')||'0');
  const t2=Number(document.getElementById('sub_t2').value.replace(/[^\d]/g,'')||'0');
  const t3=Number(document.getElementById('sub_t3').value.replace(/[^\d]/g,'')||'0');
  const m1=t1*2.50, m2=t2*5.00, m3=t3*12.50;
  document.getElementById('sub_out').textContent=fmtUSD(m1+m2+m3);
  document.getElementById('sub_line').textContent='Tier1: '+fmtUSD(m1)+' · Tier2: '+fmtUSD(m2)+' · Tier3: '+fmtUSD(m3); }
</script>"""
    return base_page(
        title="Twitch Subscription Calculator — How Much Do Subs Pay? (2026)",
        description="Estimate monthly Twitch subscription revenue: Tier 1/2/3 payouts (50% standard split), Prime and gifted subs, and why subs are the predictable income floor.",
        canonical="/twitch-sub-calculator/",
        h1="Twitch Subscription Calculator",
        body=body + js,
        jsonld={
            "@context": "https://schema.org",
            "@type": "WebApplication",
            "name": "Twitch Subscription Calculator",
            "url": f"{SITE_URL}/twitch-sub-calculator/",
            "applicationCategory": "FinanceApplication",
            "description": "Estimate monthly Twitch subscription payouts by tier.",
        },
    )


def page_blog_creators_make() -> str:
    body = f"""
<p>How much do creators actually make? The honest answer: it depends on platform, audience country, niche,
and how many income streams are stacked. This post gives planning ranges from public 2026 creator reports,
then shows why <strong>multi-stream income beats any single platform</strong>.</p>

<h2>By platform, per 1,000 views (2026)</h2>
<table>
  <thead><tr><th>Platform / format</th><th>Per 1,000 views</th></tr></thead>
  <tbody>
    <tr><td>YouTube long-form (by niche)</td><td>$1–$17</td></tr>
    <tr><td>YouTube Shorts</td><td>$0.02–$0.15</td></tr>
    <tr><td>TikTok Creator Rewards</td><td>$0.04–$1.00</td></tr>
    <tr><td>Instagram Reels</td><td>$0.03–$0.30</td></tr>
    <tr><td>Twitch ads (CPM share)</td><td>$0.70–$2.00 effective</td></tr>
  </tbody>
</table>

<h2>By monthly income tier (multi-stream, gross)</h2>
<table>
  <thead><tr><th>Tier</th><th>Typical setup</th><th>Monthly gross</th><th>Take-home (US, est.)</th></tr></thead>
  <tbody>
    <tr><td>Hobby</td><td>10k subs, ad-only</td><td>$200–$800</td><td>~85–90%</td></tr>
    <tr><td>Part-time</td><td>50k subs + sponsors</td><td>$2,000–$6,000</td><td>~70–78%</td></tr>
    <tr><td>Full-time</td><td>200k subs, 4 streams</td><td>$10,000–$30,000</td><td>~60–70%</td></tr>
    <tr><td>Top 1%</td><td>1M+ subs, media company</td><td>$50,000+</td><td>varies (S-corp)</td></tr>
  </tbody>
</table>
<p>Take-home estimates use a simplified self-employment model; real tax depends on deductions and entity.</p>

<h2>The multi-stream rule of thumb</h2>
<p>Ad revenue alone rarely supports a full-time income. The stack that does: <strong>ads (base) + sponsorships
(3–10× ads) + memberships/subs (predictable) + affiliate/Shop (scales with trust)</strong>. A mature full-time
creator typically earns 3–5× ad-only income this way. Model your own stack with the
<a href="/youtube-money-calculator/">YouTube Money Calculator</a>.</p>

<h2>Frequently asked questions</h2>
<h3>What do most YouTubers earn?</h3>
<p>Most channels under 100k subs earn less than $2,000/month gross — and after taxes and reinvestment, far
less. The median YouTuber earns well below a median US salary; only the top few percent clear six figures.</p>
<h3>Do Twitch streamers make more than YouTubers?</h3>
<p>Per engaged audience hour, often yes (subs + Bits are generous), but the audience ceiling is lower. Most
serious creators are on both, plus a short-form platform.</p>

<h2>Related tools</h2>
<ul>
  <li><a href="/youtube-money-calculator/">YouTube Money Calculator</a></li>
  <li><a href="/twitch-sub-calculator/">Twitch Sub Calculator</a></li>
  <li><a href="/views-to-money-calculator/">Views to Money</a></li>
</ul>
"""
    return base_page(
        title="How Much Do Creators Make? Honest 2026 Income Benchmarks",
        description="Realistic 2026 creator income benchmarks by platform and tier, why multi-stream income matters, and what take-home looks like after taxes.",
        canonical="/blog/how-much-do-creators-make/",
        h1="How Much Do Creators Actually Make?",
        body=body,
        jsonld={
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": "How Much Do Creators Actually Make?",
            "url": f"{SITE_URL}/blog/how-much-do-creators-make/",
            "dateModified": RPM_LIBRARY["updated"],
        },
    )


def page_blog_yt_pay_per_view() -> str:
    body = f"""
<p>The short answer: <strong>between $0.001 and $0.03 per view</strong> for YouTube long-form, depending on
your niche and audience country. Music channels earn under $0.001 per view; finance channels with US-heavy
audiences can clear $0.015–$0.03. This post walks through the actual model.</p>

<h2>Per-view math by niche (2026)</h2>
<table>
  <thead><tr><th>Niche</th><th>Take-home RPM</th><th>Per view</th></tr></thead>
  <tbody>
    <tr><td>Personal finance / investing</td><td>$5–$17</td><td>$0.005–$0.017</td></tr>
    <tr><td>Gaming</td><td>~$2–$7</td><td>$0.002–$0.007</td></tr>
    <tr><td>Entertainment / vlogs</td><td>~$1–$4</td><td>$0.001–$0.004</td></tr>
    <tr><td>Music</td><td>under $1</td><td>under $0.001</td></tr>
  </tbody>
</table>
<p>Two multipliers sit outside the table: <strong>audience geography</strong> (US/UK/CA/AU views are worth
several times low-ad-spend regions) and <strong>format</strong> (Shorts run on a pooled payout of roughly
$0.01–$0.06 per 1,000 views — about a hundredth of long-form per view).</p>

<h2>Why the range is so wide</h2>
<ul>
  <li><strong>Advertiser demand by niche:</strong> finance and tech attract high-paying advertisers; music and comedy less so.</li>
  <li><strong>Monetized share:</strong> ad blockers, Premium and limited-ads videos generate views without revenue.</li>
  <li><strong>Video length:</strong> longer videos allow more mid-roll placements per view.</li>
  <li><strong>Seasonality:</strong> Q4 CPMs run 30–80% above Q1.</li>
</ul>

<h2>How to find your real number</h2>
<p>YouTube Studio → Analytics → Revenue shows your RPM (your share per 1,000 views). Divide by 1,000 for
per-view. Until you have 90+ days of data, use the niche table above as a planning range — try the
<a href="/youtube-money-calculator/">YouTube Money Calculator</a> to model scenarios.</p>

<h2>Frequently asked questions</h2>
<h3>Does YouTube pay per view or per ad impression?</h3>
<p>Per 1,000 ad impressions served on monetized views, after the 45% platform share. "Per view" is the
simplified way creators talk about RPM ÷ 1,000.</p>
<h3>How many views to make $1,000/month?</h3>
<p>At a $2 entertainment RPM, about 500,000 monthly views; at a $15 finance-tier RPM, roughly 67,000.
Use the <a href="/views-to-money-calculator/">Views to Money Calculator</a> for your exact number.</p>

<h2>Related tools</h2>
<ul>
  <li><a href="/youtube-money-calculator/">YouTube Money Calculator</a></li>
  <li><a href="/views-to-money-calculator/">Views to Money Calculator</a></li>
  <li><a href="/cpm-vs-rpm/">RPM vs CPM explained</a></li>
</ul>
"""
    return base_page(
        title="How Much Does YouTube Pay Per View? (2026 RPM by Niche)",
        description="YouTube pays $0.001–$0.03 per view for long-form depending on niche and audience country. Per-view math, the 45% share, and how to find your real RPM.",
        canonical="/blog/how-much-does-youtube-pay-per-view/",
        h1="How Much Does YouTube Pay Per View?",
        body=body,
        jsonld={
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": "How Much Does YouTube Pay Per View?",
            "url": f"{SITE_URL}/blog/how-much-does-youtube-pay-per-view/",
            "dateModified": RPM_LIBRARY["updated"],
        },
    )


def page_index() -> str:
    body = f"""
<p>{SITE_NAME} is a free creator earnings hub: estimate what your content is really worth across
YouTube, Twitch, TikTok and Instagram — then see what you keep after tax. No sign-up, no uploads,
transparent 2026 benchmarks (updated {RPM_LIBRARY['updated']}).</p>

<h2>Tools</h2>
<table>
  <thead><tr><th>Tool</th><th>What it answers</th></tr></thead>
  <tbody>
    <tr><td><a href="/youtube-money-calculator/">YouTube Money Calculator</a></td><td>Long-form & Shorts earnings from views and RPM, by niche and country.</td></tr>
    <tr><td><a href="/twitch-bits-to-usd/">Twitch Bits to USD</a></td><td>Exact streamer payout ($0.01/Bit) and viewer cost with cheapest bundle mix.</td></tr>
    <tr><td><a href="/views-to-money-calculator/">Views to Money</a></td><td>Views → earnings, or earnings → views, any platform.</td></tr>
  </tbody>
</table>

<h2>Quick 2026 benchmarks</h2>
<table>
  <thead><tr><th>Format</th><th>Per 1,000 views</th></tr></thead>
  <tbody>
    <tr><td>YouTube long-form (by niche)</td><td>$1–$17</td></tr>
    <tr><td>YouTube Shorts</td><td>$0.02–$0.15</td></tr>
    <tr><td>TikTok Creator Rewards</td><td>$0.04–$1.00</td></tr>
    <tr><td>Instagram Reels</td><td>$0.03–$0.30</td></tr>
  </tbody>
</table>
<p>Country multipliers: US ≈ 4.3× worldwide average; India ≈ 0.24×. See <a href="/cpm-vs-rpm/">RPM vs CPM</a>
for the full model.</p>

<h2>Guides</h2>
<ul>
  <li><a href="/cpm-vs-rpm/">RPM vs CPM for creators</a></li>
  <li><a href="/blog/how-much-does-youtube-pay-per-view/">How much does YouTube pay per view?</a></li>
  <li><a href="/tiktok-money-calculator/">TikTok money benchmarks vs YouTube</a></li>
</ul>
"""
    return base_page(
        title="CreatorPayCalc — Free Creator Earnings & RPM Calculators (2026)",
        description="Free creator earnings calculators: YouTube money, Twitch Bits to USD, views to money, and multi-platform income with tax take-home. Transparent 2026 RPM benchmarks.",
        canonical="/",
        h1="What Is Your Content Really Worth?",
        body=body,
        jsonld={
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": SITE_NAME,
            "url": SITE_URL,
        },
    )


def page_404() -> str:
    return base_page(
        title="404: Page Not Found — CreatorPayCalc",
        description="The page you requested could not be found.",
        canonical="/404.html",
        h1="404 — Page Not Found",
        body="<p>The page you're looking for doesn't exist. <a href='/'>Return to the tools</a>.</p>",
        jsonld={
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": "Page Not Found",
            "url": f"{SITE_URL}/404.html",
        },
    )


# ---------------------------------------------------------------------------
# 站点地图 / robots
# ---------------------------------------------------------------------------

def build_sitemap(pages: List[str]) -> str:
    urls = "\n".join(
        f"  <url><loc>{SITE_URL}{p}</loc></url>" for p in pages
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}
</urlset>
"""


ROBOTS = f"""User-agent: *
Allow: /
Sitemap: {SITE_URL}/sitemap.xml
"""

HEADERS = """/*
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()
"""


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

CSS = """/* CreatorPayCalc - light theme */
:root{--bg:#f8fafc;--card:#ffffff;--ink:#0f172a;--accent:#0284c7;--muted:#64748b;--line:#e2e8f0}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;background:var(--bg);color:var(--ink);line-height:1.65}
.wrap{max-width:960px;margin:0 auto;padding:0 20px}
.site-header{background:#ffffff;border-bottom:1px solid var(--line);padding:14px 0}
.site-header .wrap{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:12px}
.brand{font-weight:800;font-size:1.15rem;color:var(--accent);text-decoration:none}
.brand-sub{font-weight:400;font-size:.75rem;color:var(--muted);margin-left:6px}
nav ul{list-style:none;display:flex;flex-wrap:wrap;gap:14px}
nav a{color:var(--ink);text-decoration:none;font-size:.92rem}
nav a:hover{color:var(--accent)}
main{padding:34px 0 48px}
h1{font-size:1.9rem;margin-bottom:18px;line-height:1.25}
h2{font-size:1.3rem;margin:34px 0 12px;color:#0f172a}
h3{font-size:1.02rem;margin:18px 0 6px}
p{margin:10px 0}
a{color:var(--accent)}
code{background:#f1f5f9;padding:2px 7px;border-radius:5px;font-size:.9em}
table{width:100%;border-collapse:collapse;margin:14px 0;font-size:.94rem}
th,td{border:1px solid var(--line);padding:9px 11px;text-align:left}
th{background:#f1f5f9}
.calc{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:22px;margin:18px 0;box-shadow:0 1px 3px rgba(15,23,42,.06)}
.calc label{display:block;font-size:.85rem;color:var(--muted);margin:10px 0 4px}
.calc input{width:100%;max-width:260px;padding:10px 12px;border:1px solid var(--line);border-radius:8px;background:#ffffff;color:var(--ink);font-size:1rem}
.calc-out{font-size:1.7rem;font-weight:800;color:var(--accent);margin:14px 0 4px}
.calc-line{color:var(--muted);font-size:.9rem}
.site-footer{background:#ffffff;border-top:1px solid var(--line);padding:24px 0;font-size:.85rem;color:var(--muted)}
.site-footer nav{margin-top:10px}
@media(max-width:640px){h1{font-size:1.5rem}nav ul{gap:8px}}
"""


# ---------------------------------------------------------------------------
# 构建入口
# ---------------------------------------------------------------------------

def fmt_int(x: Decimal) -> str:
    return f"{int(x):,}"


def main() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "css").mkdir(parents=True, exist_ok=True)
    (DIST / "youtube-money-calculator").mkdir(parents=True, exist_ok=True)
    (DIST / "twitch-bits-to-usd").mkdir(parents=True, exist_ok=True)
    (DIST / "views-to-money-calculator").mkdir(parents=True, exist_ok=True)
    (DIST / "cpm-vs-rpm").mkdir(parents=True, exist_ok=True)
    (DIST / "tiktok-money-calculator").mkdir(parents=True, exist_ok=True)
    (DIST / "blog" / "how-much-does-youtube-pay-per-view").mkdir(parents=True, exist_ok=True)

    pages: List[str] = [
        "/", "/youtube-money-calculator/", "/twitch-bits-to-usd/",
        "/views-to-money-calculator/",
        "/cpm-vs-rpm/", "/tiktok-money-calculator/",
        "/youtube-rpm-calculator/", "/twitch-sub-calculator/",
        "/blog/how-much-does-youtube-pay-per-view/",
        "/blog/how-much-do-creators-make/",
    ]

    def write(rel: str, content: str) -> None:
        (DIST / rel).parent.mkdir(parents=True, exist_ok=True)
        (DIST / rel).write_text(content, encoding="utf-8")
        print(f"  ✓ {rel}")

    print("[*] 构建 CreatorPayCalc 静态站 ...")
    write("index.html", page_index())
    write("youtube-money-calculator/index.html", page_youtube_money())
    write("twitch-bits-to-usd/index.html", page_twitch_bits())
    for b in (100, 1000, 5000, 10000, 25000, 100000):
        write(f"twitch-bits-to-usd/{b}/index.html", page_bits_amount(b))
        pages.append(f"/twitch-bits-to-usd/{b}/")
    write("views-to-money-calculator/index.html", page_views_to_money())
    write("cpm-vs-rpm/index.html", page_cpm_vs_rpm())
    write("tiktok-money-calculator/index.html", page_tiktok_money())
    write("youtube-rpm-calculator/index.html", page_youtube_rpm())
    write("twitch-sub-calculator/index.html", page_twitch_sub_calc())
    write("blog/how-much-does-youtube-pay-per-view/index.html", page_blog_yt_pay_per_view())
    write("blog/how-much-do-creators-make/index.html", page_blog_creators_make())
    for legal in LEGAL_PAGES:
        write(legal["route"].lstrip("/") + "/index.html", base_page(
            title=legal["title"],
            description=legal["description"],
            canonical=legal["route"],
            h1=legal["h1"],
            body=legal["body"],
            jsonld={"@context": "https://schema.org", "@type": "WebPage",
                    "name": legal["title"], "url": f"{SITE_URL}{legal['route']}"},
        ))
        pages.append(legal["route"])
    write("404.html", page_404())
    write("css/site.css", CSS)
    write("sitemap.xml", build_sitemap(pages))
    write("robots.txt", ROBOTS)
    write("_headers", HEADERS)

    # 导出 RPM 库 JSON（数据护城河产物）
    from rpm_library import save_json
    save_json(DIST / "rpm_library.json")
    print(f"[+] 构建完成：{DIST}（{len(pages)} 个页面 URL）")


if __name__ == "__main__":
    main()
