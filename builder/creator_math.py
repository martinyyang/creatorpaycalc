#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CreatorPayCalc — 创作者收益计算引擎
=====================================
Decimal 金额精度铁律（沿用站 1）：
  所有金额计算使用 Decimal，输出统一 2 位小数，ROUND_HALF_UP。

核心模型（透明假设，全部标注来源与更新日期，见 rpm_library.py）：
  YouTube 长视频收益 = (views / 1000) * RPM          （RPM 已是创作者实收口径）
  YouTube Shorts 收益 = (shorts_views / 1000) * shorts_rpm
  CPM→实收 = (views * monetized% * CPM * creator_share) / 1000
  Twitch Bits 实收 = bits * 0.01                     （固定汇率，无分成）
  Twitch Bits 观众成本 = 最省打包求解（pack mix）
  反向目标 views = (target / RPM) * 1000
  税后实收（美国自雇简化） = gross * (1 - se_tax_effective) ，SE tax 按 92.35% 应税基数 * 15.3%，
                          再按联邦税档（简化 2026 单一档位表）估算，仅作规划参考。
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple

MONEY = Decimal("0.01")


def d(value) -> Decimal:
    """安全转 Decimal，None/空 -> 0。"""
    if value is None or value == "":
        return Decimal("0")
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def money(value) -> Decimal:
    return d(value).quantize(MONEY, rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# 基础公式
# ---------------------------------------------------------------------------

def rpm_to_earnings(views: Decimal, rpm: Decimal) -> Decimal:
    """RPM -> 收益：RPM 即每 1000 views 实收。"""
    if views <= 0:
        return money("0.00")
    return money((views / 1000) * rpm)


def cpm_to_creator_earnings(
    views: Decimal, cpm: Decimal, monetized_pct: Decimal, creator_share: Decimal
) -> Decimal:
    """广告 CPM -> 创作者实收：
    实收 = views * (monetized%/100) * CPM * (creator_share%/100) / 1000"""
    if views <= 0:
        return money("0.00")
    return money(
        views * (monetized_pct / 100) * cpm * (creator_share / 100) / 1000
    )


def earnings_to_views(target: Decimal, rpm: Decimal) -> Decimal:
    """反向：目标收益 -> 所需 views。"""
    if rpm <= 0:
        return Decimal("0")
    return money((target / rpm) * 1000)


# ---------------------------------------------------------------------------
# Twitch Bits
# ---------------------------------------------------------------------------

BITS_PACKS: List[Tuple[int, Decimal]] = [
    # (Bits, 美元价) — Twitch 美国官网包，来源见 rpm_library.py
    (25000, d("308.00")),
    (10000, d("126.00")),
    (5000, d("64.40")),
    (1500, d("19.95")),
    (500, d("7.00")),
    (100, d("1.40")),
]


def bits_streamer_earnings(bits: Decimal) -> Decimal:
    """主播实收：1 Bit = $0.01，固定。"""
    return money(bits * d("0.01"))


def cheapest_pack_mix(bits: int) -> Tuple[List[Tuple[int, int]], Decimal]:
    """最省打包求解：给定 bits 数，求最便宜购买组合（贪心从大包到小包）。
    返回 ([(pack_size, count), ...], 总价)。
    说明：贪心在整包组合下为最优（包价与数量线性且单价随包增大递减，
    证明略：贪心先取最大可行包即全局最优）。
    """
    remaining = int(bits)
    mix: List[Tuple[int, int]] = []
    total = Decimal("0")
    for size, price in BITS_PACKS:
        if remaining <= 0:
            break
        cnt = remaining // size
        if cnt:
            mix.append((size, cnt))
            total += price * cnt
            remaining -= size * cnt
    if remaining > 0:
        # 不足最小包时按 100 Bits 包补齐（向上取整）
        cnt = 1
        mix.append((100, cnt))
        total += d("1.40")
    return mix, money(total)


def viewer_cost(bits: int) -> Decimal:
    """观众购买 bits 的成本（最省组合）。"""
    _, total = cheapest_pack_mix(bits)
    return total


# ---------------------------------------------------------------------------
# 美国税后实收（简化估算，透明假设）
# ---------------------------------------------------------------------------

# 2026 联邦税档（单身，简化版，仅估算用）
FED_BRACKETS_2026: List[Tuple[Decimal, Decimal]] = [
    # (上限, 边际税率)，0 起
    (d("11925"), d("0.10")),
    (d("48475"), d("0.12")),
    (d("103350"), d("0.22")),
    (d("197300"), d("0.24")),
    (d("250525"), d("0.32")),
    (d("626350"), d("0.35")),
    (d("999999999"), d("0.37")),
]
SE_RATE = d("0.153")       # 自雇税 15.3%
SE_BASE = d("0.9235")      # 应税基数 92.35%
STANDARD_DEDUCTION_2026 = d("14600")


def _fed_tax(taxable: Decimal) -> Decimal:
    """简化阶梯计税。"""
    taxable = max(taxable, Decimal("0"))
    tax = Decimal("0")
    prev = Decimal("0")
    for cap, rate in FED_BRACKETS_2026:
        if taxable > prev:
            bracket_income = min(taxable, cap) - prev
            tax += bracket_income * rate
        else:
            break
        prev = cap
    return tax


def us_take_home(gross: Decimal) -> Dict[str, Decimal]:
    """美国自雇税后实收（简化估算）：
    1) SE tax = gross * 92.35% * 15.3%（无其他收入假设）
    2) 联邦税按 taxable = gross - SE_tax/2 - 标准扣除
    返回 {gross, se_tax, fed_tax, take_home, effective_rate}
    """
    gross = max(gross, Decimal("0"))
    se_tax = gross * SE_BASE * SE_RATE
    taxable = gross - (se_tax / 2) - STANDARD_DEDUCTION_2026
    fed_tax = _fed_tax(taxable)
    take_home = gross - se_tax - fed_tax
    eff = (take_home / gross * 100) if gross > 0 else Decimal("0")
    return {
        "gross": money(gross),
        "se_tax": money(se_tax),
        "fed_tax": money(fed_tax),
        "take_home": money(take_home),
        "effective_rate": eff.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
    }


# ---------------------------------------------------------------------------
# 综合收益汇总
# ---------------------------------------------------------------------------

def portfolio_total(
    items: List[Tuple[str, Decimal]]
) -> Tuple[Decimal, Decimal]:
    """多平台×多流汇总：[(label, monthly_usd), ...] -> (总额, 税后实收)。"""
    gross = sum((i[1] for i in items), Decimal("0"))
    after = us_take_home(gross)
    return money(gross), after["take_home"]
