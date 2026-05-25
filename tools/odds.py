from api.api_football import get_fixture_odds, get_live_odds

BR_BOOKMAKERS = {8, 32, 34}  # Bet365, Betano, Superbet

_MARKETS_PREMATCH = [
    "Match Winner",
    "Double Chance",
    "Both Teams Score",
    "Goals Over/Under",
    "Asian Handicap",
    "First Half Winner",
]


def _best_odd(entries: list[dict]) -> dict:
    return max(entries, key=lambda x: float(x["odd"]))


async def get_prematch_odds(fixture_id: int) -> dict:
    raw = await get_fixture_odds(fixture_id)
    if not raw:
        return {"error": "sem_cobertura"}
    bookmakers = raw[0].get("bookmakers", [])
    if not bookmakers:
        return {"error": "sem_cobertura"}

    all_markets: dict[str, dict[str, list[dict]]] = {}
    for bm in bookmakers:
        if bm.get("id") not in BR_BOOKMAKERS:
            continue
        bm_name = bm.get("name") or bm.get("bookmaker", {}).get("name", "?")
        for bet in bm.get("bets", []):
            market = bet["name"]
            all_markets.setdefault(market, {})
            for val in bet["values"]:
                outcome = val["value"]
                all_markets[market].setdefault(outcome, []).append({
                    "bookmaker": bm_name,
                    "odd": val["odd"],
                })

    if not all_markets:
        return {"error": "sem_cobertura"}

    ordered: dict[str, dict] = {}
    for m in _MARKETS_PREMATCH:
        if m in all_markets:
            ordered[m] = all_markets[m]
    for m, data in all_markets.items():
        if m not in ordered:
            ordered[m] = data

    return {
        "status": "ok",
        "markets": {
            market: {outcome: _best_odd(entries) for outcome, entries in outcomes.items()}
            for market, outcomes in ordered.items()
        },
    }


async def get_live_match_odds(fixture_id: int) -> dict:
    """Odds exclusivamente ao vivo. Nunca usa pré-jogo como fallback — pré-jogo fecha quando o jogo começa."""
    live = await get_live_odds(fixture_id)
    live_status = live["status"]
    bets = live["bets"]

    if live_status == "ok" and bets:
        markets = {bet["name"]: {v["value"]: v["odd"] for v in bet.get("values", [])} for bet in bets}
        return {"status": "live", "markets": markets}

    msgs = {
        "intervalo":    "intervalo_sem_odds",
        "suspenso":     "suspenso_sem_odds",
        "sem_mercados": "sem_cobertura",
        "sem_cobertura":"sem_cobertura",
    }
    return {"status": msgs.get(live_status, "sem_cobertura"), "markets": {}}
