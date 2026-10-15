#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RPM / 收益基准数据库（数据护城河）
===================================
透明口径：数据为 2026 年公开创作者报告/行业调研聚合（vidIQ、Influencer Marketing Hub、
Mediacube/Lenos、平台官方文档），标注来源与更新日期；金额为规划参考区间，非保证值。
更新机制：本文件为唯一数据源，改 JSON 后重建 dist 即全站生效（反人工原则）。
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent

RPM_LIBRARY = {
    "updated": "2026-10-14",
    "sources": [
        "vidIQ niche RPM data",
        "Influencer Marketing Hub creator surveys 2026",
        "Mediacube / Lenos creator benchmarks 2026",
        "platform official documentation (YouTube Partner Program, Twitch Bits, TikTok Creator Rewards)",
    ],
    "youtube_long_form": {
        # 长视频 RPM 区间（创作者实收口径，已扣除平台 45% 分成）
        "personal_finance_investing": [5.0, 17.0],
        "technology_reviews": [5.0, 12.0],
        "education_howto": [4.0, 10.0],
        "business_marketing": [4.0, 12.0],
        "gaming": [2.0, 7.0],
        "entertainment_vlogs": [1.0, 4.0],
        "lifestyle_beauty": [1.5, 6.0],
        "music": [0.5, 1.5],
    },
    "youtube_shorts": {
        # Shorts 池分账：$0.02–0.15 / 1000 views
        "low": 0.02,
        "high": 0.15,
        "typical": 0.06,
    },
    "tiktok_creator_rewards": {
        # 每 1000 合格播放
        "low": 0.04,
        "high": 1.00,
        "typical": 0.40,
        "notes": "按合格播放计（非全部播放）；创作者后台 RPM 为准",
    },
    "instagram_reels": {
        "low": 0.03,
        "high": 0.30,
        "typical": 0.10,
    },
    "twitch": {
        "bits_rate_per_bit": 0.01,        # 主播实收固定
        "sub_tier1_monthly": 2.50,        # 主播分成后（50/50 标准分成）
        "sub_tier2_monthly": 5.00,
        "sub_tier3_monthly": 12.50,
        "ad_cpm": [3.5, 10.0],            # 广告 CPM 区间（分成前）
        "bits_packs": [                      # 美国官网包价（观众支付）
            [25000, 308.00], [10000, 126.00], [5000, 64.40],
            [1500, 19.95], [500, 7.00], [100, 1.40],
        ],
        "notes": "Bits 主播实收固定 $0.01/Bit；订阅按标准分成估算；移动端购买加约 30%",
    },
    "country_multipliers": {
        # 观众地区乘数（以全球均值 1.0 为基准）
        "worldwide": 1.0,
        "us": 4.3,
        "uk": 3.9,
        "canada": 3.4,
        "australia": 3.1,
        "germany": 2.9,
        "france": 2.4,
        "japan": 2.2,
        "brazil": 0.8,
        "india": 0.24,
        "indonesia": 0.2,
        "vietnam": 0.18,
    },
    "platform_share": {
        "youtube_long_form_creator": 55,   # 创作者分 55%
        "youtube_shorts_creator": 45,
        "twitch_sub_creator_standard": 50,
    },
}

# ---------------------------------------------------------------------------
# 便捷访问
# ---------------------------------------------------------------------------

def country_multiplier(country: str) -> float:
    return RPM_LIBRARY["country_multipliers"].get(country, 1.0)


def youtube_rpm(niche: str, country: str) -> float:
    """长视频 RPM 基准（中值 × 国家乘数）。"""
    lo, hi = RPM_LIBRARY["youtube_long_form"].get(niche, [2.0, 7.0])
    mid = (lo + hi) / 2
    return round(mid * country_multiplier(country), 2)


def save_json(path: Path) -> None:
    path.write_text(
        json.dumps(RPM_LIBRARY, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    out = DATA_DIR / "rpm_library.json"
    save_json(out)
    print(f"RPM 库已导出: {out} ({len(RPM_LIBRARY['youtube_long_form'])} 个 niche)")
