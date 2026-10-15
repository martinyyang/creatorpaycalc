# CreatorPayCalc — Free Creator Earnings & RPM Calculators

[![Live Site](https://img.shields.io/badge/Live_Tool-creatorpaycalc.com-2563eb?style=for-the-badge)](https://creatorpaycalc.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**CreatorPayCalc** is a fast, 100% client-side + static-prerendered creator earnings calculator suite for YouTube, Twitch, TikTok, and Instagram.

Live site: **https://creatorpaycalc.com**

## Live calculators

1. **[YouTube Money Calculator](https://creatorpaycalc.com/youtube-money-calculator/)** — long-form and Shorts earnings from views and RPM, by niche and country.
2. **[Twitch Bits to USD](https://creatorpaycalc.com/twitch-bits-to-usd/)** — streamer payout at `$0.01` per Bit plus viewer cost with the cheapest pack mix.
3. **[Views to Money Calculator](https://creatorpaycalc.com/views-to-money-calculator/)** — views → earnings or earnings → views.
4. **[YouTube RPM Calculator](https://creatorpaycalc.com/youtube-rpm-calculator/)** — niche × country RPM ranges.
5. **[Twitch Sub Calculator](https://creatorpaycalc.com/twitch-sub-calculator/)** — Tier 1/2/3 subscription take-home.
6. **[TikTok Money Calculator](https://creatorpaycalc.com/tiktok-money-calculator/)** — Creator Rewards vs YouTube per 1,000 views.
7. **[RPM vs CPM](https://creatorpaycalc.com/cpm-vs-rpm/)** — how creator RPM relates to advertiser CPM.

## Legal & methodology

- [Privacy Policy](https://creatorpaycalc.com/privacy-policy)
- [Terms of Service](https://creatorpaycalc.com/terms-of-service)
- [About Us & Methodology](https://creatorpaycalc.com/about)
- [Contact](https://creatorpaycalc.com/contact)

## Build locally

```bash
python3 builder/build_site.py
```

Output is written to `dist/` (static HTML, CSS, sitemap, robots, and `rpm_library.json`).

Optional analytics injection (omit both to skip):

```bash
GA4_MEASUREMENT_ID=G-XXXXXXXXXX CLARITY_PROJECT_ID=xxxxxxxx python3 builder/build_site.py
```

## Tests

```bash
python3 tests/test_creator_site_seo_and_math.py -v
python3 tests/test_creator_e2e_playwright.py
```

## License

Released under the [MIT License](LICENSE).

Copyright (c) 2026 martinyyang
