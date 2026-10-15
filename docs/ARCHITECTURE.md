# CreatorPayCalc architecture

CreatorPayCalc is a static creator-earnings calculator suite for https://creatorpaycalc.com.

## Positioning

One tool family that answers “what is my content worth?” across YouTube, Twitch, TikTok, and Instagram — ads, subscriptions, bits/tips, niche × country RPM, US take-home tax estimate, and reverse targets (views needed to earn $X).

## Page tree

1. `/` — tool hub
2. `/youtube-money-calculator/` — long-form + Shorts, niche × country RPM
3. `/twitch-bits-to-usd/` — streamer payout vs viewer cost + amount landing pages
4. `/views-to-money-calculator/` — views ↔ dollars
5. `/cpm-vs-rpm/` — RPM vs advertiser CPM
6. `/tiktok-money-calculator/` — TikTok vs YouTube per 1,000 views
7. `/youtube-rpm-calculator/` and `/twitch-sub-calculator/`
8. `/blog/how-much-does-youtube-pay-per-view/` and `/blog/how-much-do-creators-make/`
9. Legal: `/privacy-policy`, `/terms-of-service`, `/about`, `/contact`

## Build

- `builder/creator_math.py` — Decimal money engine
- `builder/rpm_library.py` — platform × niche × country benchmarks
- `builder/build_site.py` — template render + SEO injection → `dist/`
- Tests lock unique title/H1/canonical, JSON-LD, substantive SSR, sitemap/robots, and money rounding
