from api.api_football import get_fixture_odds, get_live_odds

BR_BOOKMAKERS = {8, 32, 34}  # Bet365, Betano, Superbet

# ── Mercados pré-jogo válidos (por bet_id) ─────────────────────────────────
# Apenas mercados analisáveis com dados estatísticos disponíveis
VALID_PREMATCH_IDS = {
    # Resultado
    1,   # Match Winner (1x2)
    2,   # Home/Away (Draw No Bet)
    12,  # Double Chance
    13,  # First Half Winner
    # Gols tempo normal
    5,   # Goals Over/Under
    8,   # Both Teams Score
    16,  # Total - Home
    17,  # Total - Away
    # Gols 1º tempo
    6,   # Goals Over/Under First Half
    34,  # Both Teams Score - First Half
    105, # Home Team Total Goals (1st Half)
    106, # Away Team Total Goals (1st Half)
    # Gols 2º tempo
    26,  # Goals Over/Under - Second Half
    35,  # Both Teams To Score - Second Half
    # Clean sheet / Win to nil
    27,  # Clean Sheet - Home
    28,  # Clean Sheet - Away
    29,  # Win to Nil - Home
    30,  # Win to Nil - Away
    36,  # Win To Nil
    # Asian Handicap
    4,   # Asian Handicap
    # Escanteios
    45,  # Corners Over Under
    55,  # Corners 1x2
    57,  # Home Corners Over/Under
    58,  # Away Corners Over/Under
    77,  # Total Corners (1st Half)
    127, # Total Corners (2nd Half)
    # Cartões
    80,  # Cards Over/Under
    82,  # Home Team Total Cards
    83,  # Away Team Total Cards
}

# Ordem de exibição — mais relevantes primeiro
_PREMATCH_ORDER = [1, 12, 2, 5, 8, 4, 6, 34, 26, 35, 16, 17, 27, 28, 29, 30, 36, 45, 55, 80]

# ── Mercados ao vivo válidos (por bet_id) ──────────────────────────────────
VALID_LIVE_IDS = {
    59,  # Fulltime Result (1x2)
    72,  # Double Chance
    48,  # Draw No Bet
    33,  # Asian Handicap
    25,  # Match Goals (Over/Under)
    36,  # Over/Under Line
    69,  # Both Teams to Score
    29,  # Result / Both Teams To Score
    49,  # Over/Under (1st Half)
    177, # Over/Under (2nd Half)
    43,  # Both Teams To Score (2nd Half)
    37,  # Total Corners
    20,  # Match Corners (com handicap)
    19,  # 1x2 (1st Half)
    180, # Double Chance (1st Half)
}


def _best_odd(entries: list[dict]) -> dict:
    return max(entries, key=lambda x: float(x["odd"]))


async def get_prematch_odds(fixture_id: int) -> dict:
    raw = await get_fixture_odds(fixture_id)
    if not raw:
        return {"error": "sem_cobertura"}
    bookmakers = raw[0].get("bookmakers", [])
    if not bookmakers:
        return {"error": "sem_cobertura"}

    # Coleta mercados filtrando por bookmaker ID e bet ID
    all_markets: dict[int, dict[str, dict[str, list[dict]]]] = {}
    for bm in bookmakers:
        if bm.get("id") not in BR_BOOKMAKERS:
            continue
        bm_name = bm.get("name") or bm.get("bookmaker", {}).get("name", "?")
        for bet in bm.get("bets", []):
            bet_id = bet.get("id")
            if bet_id not in VALID_PREMATCH_IDS:
                continue
            bet_name = bet["name"]
            if bet_id not in all_markets:
                all_markets[bet_id] = {"name": bet_name, "outcomes": {}}
            for val in bet["values"]:
                outcome = val["value"]
                all_markets[bet_id]["outcomes"].setdefault(outcome, []).append({
                    "bookmaker": bm_name,
                    "odd": val["odd"],
                })

    if not all_markets:
        return {"error": "sem_cobertura"}

    # Ordena pelos mercados mais relevantes primeiro
    ordered: dict[str, dict] = {}
    seen_ids = set()
    for bid in _PREMATCH_ORDER:
        if bid in all_markets:
            entry = all_markets[bid]
            ordered[entry["name"]] = {
                outcome: _best_odd(entries)
                for outcome, entries in entry["outcomes"].items()
            }
            seen_ids.add(bid)
    for bid, entry in all_markets.items():
        if bid not in seen_ids:
            ordered[entry["name"]] = {
                outcome: _best_odd(entries)
                for outcome, entries in entry["outcomes"].items()
            }

    return {"status": "ok", "markets": ordered}


def _parse_live_outcome(v: dict) -> tuple[str, str] | None:
    """Combina value + handicap em chave legível. Descarta outcomes suspensos."""
    if v.get("suspended"):
        return None
    value = v["value"]
    handicap = v.get("handicap")
    key = f"{value} {handicap}" if handicap else value
    return key, v["odd"]


async def get_live_match_odds(fixture_id: int) -> dict:
    """Odds exclusivamente ao vivo. Nunca usa pré-jogo como fallback."""
    live = await get_live_odds(fixture_id)
    live_status = live["status"]
    odds = live["odds"]

    if live_status == "ok" and odds:
        markets: dict[str, dict[str, str]] = {}
        for market in odds:
            if market.get("id") not in VALID_LIVE_IDS:
                continue
            name = market["name"]
            outcomes: dict[str, str] = {}
            for v in market.get("values", []):
                parsed = _parse_live_outcome(v)
                if parsed:
                    outcome_key, odd_val = parsed
                    if outcome_key not in outcomes or float(odd_val) > float(outcomes[outcome_key]):
                        outcomes[outcome_key] = odd_val
            if outcomes:
                markets[name] = outcomes
        return {"status": "live", "markets": markets}

    msgs = {
        "intervalo":     "intervalo_sem_odds",
        "suspenso":      "suspenso_sem_odds",
        "sem_mercados":  "sem_cobertura",
        "sem_cobertura": "sem_cobertura",
    }
    return {"status": msgs.get(live_status, "sem_cobertura"), "markets": {}}
