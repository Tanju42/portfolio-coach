from __future__ import annotations

from typing import Any

STABLES = {"USDT", "USDC", "FDUSD", "BUSD", "EUR", "USD"}
MAJOR = {"BTC", "ETH"}
MEME = {"DOGE", "SHIB", "PEPE", "BONK", "FLOKI", "WIF"}

CATEGORIES = {
    "stables": STABLES,
    "major": MAJOR,
    "meme": MEME,
}

GROUP_KEYS = {"STABLES", "ALT", "MAJOR", "STOCKS"}

DEFAULT_TARGETS = {"MAJOR": 35, "ALT": 15, "STABLES": 15, "STOCKS": 35}

DRIFT_TOLERANCE_PCT = 5.0
MIN_TRADE_USD = 10.0


def asset_category(asset: str, kind: str = "crypto") -> str:
    if kind == "stocks":
        return "stocks"
    if asset in STABLES:
        return "stables"
    if asset in MAJOR:
        return "major"
    if asset in MEME:
        return "meme"
    return "alt"


def exposure(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    total = sum(row["value_usd"] for row in rows)
    buckets: dict[str, dict[str, Any]] = {}
    for row in rows:
        kinds = {p["label"] for p in row.get("providers", [])}
        kind = "stocks" if any("Broker" in label for label in kinds) else "crypto"
        category = asset_category(row["asset"], kind)
        bucket = buckets.setdefault(category, {"category": category, "value_usd": 0.0, "assets": []})
        bucket["value_usd"] += row["value_usd"]
        bucket["assets"].append(row["asset"])
    result = sorted(buckets.values(), key=lambda b: -b["value_usd"])
    for bucket in result:
        bucket["weight_pct"] = round(bucket["value_usd"] / total * 100, 1) if total > 0 else 0.0
        bucket["value_usd"] = round(bucket["value_usd"], 2)
        bucket["assets"] = sorted(set(bucket["assets"]))
    return result


def risk_report(rows: list[dict[str, Any]], portfolio_blocks: list[dict[str, Any]]) -> dict[str, Any]:
    total = sum(row["value_usd"] for row in rows)
    if total <= 0:
        return {"score": None, "exposure": [], "warnings": ["no portfolio data available"]}
    exposure_data = exposure(rows)
    by_category = {item["category"]: item["value_usd"] for item in exposure_data}
    top = rows[0]
    top_share = top["value_usd"] / total if top else 0.0
    stables_share = by_category.get("stables", 0.0) / total
    meme_share = by_category.get("meme", 0.0) / total
    asset_count = len(rows)
    avg_reliability = (
        sum(row["basis_reliable_share"] * row["value_usd"] for row in rows) / total if total > 0 else 0.0
    )

    concentration_penalty = min(30.0, max(0.0, top_share - 0.25) * 100 * 0.6)
    stables_penalty = min(25.0, max(0.0, 0.10 - stables_share) * 100 * 1.5)
    meme_penalty = min(20.0, meme_share * 100 * 0.8)
    diversification_penalty = 10.0 if asset_count < 3 else 0.0
    basis_penalty = 10.0 if avg_reliability < 0.5 else 0.0
    score = max(0.0, 100.0 - concentration_penalty - stables_penalty - meme_penalty - diversification_penalty - basis_penalty)

    warnings = []
    if top_share > 0.4:
        warnings.append(f"{top['asset']} is {round(top_share * 100)}% of your portfolio — high concentration risk")
    elif top_share > 0.25:
        warnings.append(f"{top['asset']} is {round(top_share * 100)}% — consider trimming toward 25%")
    if stables_share < 0.05:
        warnings.append("less than 5% in stables — no cash buffer for opportunities or corrections")
    if meme_share > 0.1:
        warnings.append(f"memecoins are {round(meme_share * 100)}% of the portfolio — high-volatility exposure")
    if asset_count < 3:
        warnings.append("very few distinct assets — diversification is thin")
    if avg_reliability < 0.5:
        warnings.append("less than half of your cost basis is verified — import your transaction history")
    if not warnings:
        warnings.append("no risk flags: allocation, concentration and buffer look reasonable")

    return {
        "score": round(score),
        "top_asset": top["asset"] if top else None,
        "top_share_pct": round(top_share * 100, 1),
        "stables_share_pct": round(stables_share * 100, 1),
        "meme_share_pct": round(meme_share * 100, 1),
        "asset_count": asset_count,
        "basis_reliability_pct": round(avg_reliability * 100, 1),
        "unrealized_pnl_usd": round(sum(row["pnl_usd"] for row in rows), 2),
        "exposure": exposure_data,
        "warnings": warnings,
        "penalties": {
            "concentration": round(concentration_penalty, 1),
            "no_stables_buffer": round(stables_penalty, 1),
            "meme_exposure": round(meme_penalty, 1),
            "thin_diversification": diversification_penalty,
            "unknown_basis": basis_penalty,
        },
    }


def _row_kind(row: dict[str, Any]) -> str:
    kind = row.get("kind")
    if kind in ("stocks", "crypto"):
        return kind
    labels = {p.get("label", "") for p in row.get("providers", [])}
    return "stocks" if any("Broker" in label for label in labels) else "crypto"


def expand_targets(targets: dict[str, float], rows: list[dict[str, Any]]) -> dict[str, float]:
    if not targets:
        targets = dict(DEFAULT_TARGETS)
    total_pct = sum(targets.values())
    if abs(total_pct - 100.0) > 0.01:
        targets = {key: value * 100.0 / total_pct for key, value in targets.items()}

    expanded: dict[str, float] = {}
    for key, pct in targets.items():
        upper = key.upper()
        if upper == "STABLES":
            members = [row["asset"] for row in rows if row["asset"] in STABLES]
        elif upper in ("MAJOR", "ALT"):
            members = [
                row["asset"]
                for row in rows
                if asset_category(row["asset"]) == ("major" if upper == "MAJOR" else "alt")
            ]
        elif upper == "STOCKS":
            members = [row["asset"] for row in rows if asset_category(row["asset"], _row_kind(row)) == "stocks"]
        else:
            members = [row["asset"] for row in rows if row["asset"].upper() == upper]
        if not members:
            continue
        share = pct / len(members)
        for member in members:
            expanded[member] = expanded.get(member, 0.0) + share
    return expanded


def rebalance_suggestions(
    rows: list[dict[str, Any]], targets: dict[str, float]
) -> dict[str, Any]:
    total = sum(row["value_usd"] for row in rows)
    if total <= 0:
        return {"current": [], "actions": [], "total_drift_pct": 0.0, "note": "no portfolio data"}
    expanded = expand_targets(targets, rows)
    current = []
    drift_sum = 0.0
    for row in rows:
        weight = row["value_usd"] / total * 100
        target = expanded.get(row["asset"], 0.0)
        drift = weight - target
        drift_sum += abs(drift)
        action = None
        amount_usd = abs(drift) / 100 * total
        if abs(drift) > DRIFT_TOLERANCE_PCT and amount_usd >= MIN_TRADE_USD:
            action = "sell" if drift > 0 else "buy"
        current.append({
            "asset": row["asset"],
            "value_usd": row["value_usd"],
            "weight_pct": round(weight, 1),
            "target_pct": round(target, 1),
            "drift_pct": round(drift, 1),
            "action": action,
            "amount_usd": round(amount_usd, 2) if action else 0.0,
        })
    sells = [item for item in current if item["action"] == "sell"]
    buys = [item for item in current if item["action"] == "buy"]
    actions = sorted(sells, key=lambda x: -x["amount_usd"]) + sorted(buys, key=lambda x: -x["amount_usd"])
    return {
        "current": current,
        "actions": actions,
        "total_drift_pct": round(drift_sum, 1),
        "tolerance_pct": DRIFT_TOLERANCE_PCT,
        "min_trade_usd": MIN_TRADE_USD,
        "note": (
            "Rebalancing suggests trades that move each asset toward its target share. "
            "Review every suggestion in the Coach chat before acting — nothing is executed automatically."
        ),
    }
