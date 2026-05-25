import httpx
from typing import Any
from config import API_FOOTBALL_BASE, API_FOOTBALL_HEADERS, API_TIMEZONE, season_for


async def _get(endpoint: str, params: dict) -> dict[str, Any]:
    params.setdefault("timezone", API_TIMEZONE)
    url = f"{API_FOOTBALL_BASE}/{endpoint}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, headers=API_FOOTBALL_HEADERS, params=params)
        resp.raise_for_status()
        return resp.json()


# ── Fixtures ────────────────────────────────────────────────────────────────

async def get_live_fixtures(league_ids: list[int] | None = None) -> list[dict]:
    data = await _get("fixtures", {"live": "all"})
    fixtures = data.get("response", [])
    if league_ids:
        fixtures = [f for f in fixtures if f["league"]["id"] in league_ids]
    return fixtures


async def get_fixture_by_id(fixture_id: int) -> dict | None:
    data = await _get("fixtures", {"id": fixture_id})
    resp = data.get("response", [])
    return resp[0] if resp else None


def _name_matches(query: str, full_name: str) -> bool:
    q = query.lower().strip()
    n = full_name.lower()
    return q in n or any(q in word for word in n.split())


async def search_fixture(team1: str, team2: str) -> list[dict]:
    # 1. Ao vivo — sem filtro de season
    data = await _get("fixtures", {"live": "all"})
    results = [
        f for f in data.get("response", [])
        if (_name_matches(team1, f["teams"]["home"]["name"]) or _name_matches(team1, f["teams"]["away"]["name"]))
        and (_name_matches(team2, f["teams"]["home"]["name"]) or _name_matches(team2, f["teams"]["away"]["name"]))
    ]
    if results:
        return results

    # 2. Jogos de hoje — busca sem season primeiro (pega tudo), depois filtra por nome
    today_data = await _get("fixtures", {"date": _today()})
    results = [
        f for f in today_data.get("response", [])
        if (_name_matches(team1, f["teams"]["home"]["name"]) or _name_matches(team1, f["teams"]["away"]["name"]))
        and (_name_matches(team2, f["teams"]["home"]["name"]) or _name_matches(team2, f["teams"]["away"]["name"]))
    ]
    return results


async def get_fixture_statistics(fixture_id: int) -> list[dict]:
    data = await _get("fixtures/statistics", {"fixture": fixture_id})
    return data.get("response", [])


async def get_fixture_events(fixture_id: int) -> list[dict]:
    data = await _get("fixtures/events", {"fixture": fixture_id})
    return data.get("response", [])


async def get_fixtures_today(league_id: int | None = None) -> list[dict]:
    params: dict = {"date": _today()}
    if league_id:
        # usa a temporada correta para a liga especificada
        params["league"] = league_id
        params["season"] = season_for(league_id)
    data = await _get("fixtures", params)
    return data.get("response", [])


# ── Standings ────────────────────────────────────────────────────────────────

async def get_standings(league_id: int) -> list[dict]:
    season = season_for(league_id)
    data = await _get("standings", {"league": league_id, "season": season})
    resp = data.get("response", [])
    if not resp:
        return []
    return resp[0]["league"]["standings"]


# ── Head-to-Head / Form ───────────────────────────────────────────────────────

async def get_head_to_head(team1_id: int, team2_id: int, last: int = 10) -> list[dict]:
    data = await _get("fixtures/headtohead", {
        "h2h": f"{team1_id}-{team2_id}",
        "last": last,
    })
    return data.get("response", [])


async def get_team_fixtures(team_id: int, last: int = 5) -> list[dict]:
    data = await _get("fixtures", {"team": team_id, "last": last})
    return data.get("response", [])


async def search_team(name: str) -> list[dict]:
    data = await _get("teams", {"search": name})
    return data.get("response", [])


# ── Odds ──────────────────────────────────────────────────────────────────────

async def get_fixture_odds(fixture_id: int) -> list[dict]:
    data = await _get("odds", {"fixture": fixture_id})
    return data.get("response", [])


async def get_live_odds(fixture_id: int) -> dict:
    """Retorna odds ao vivo com status detalhado (stopped=HT, blocked=suspenso, sem_mercados=sem cobertura)."""
    url = f"{API_FOOTBALL_BASE}/odds/live"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, headers=API_FOOTBALL_HEADERS, params={"fixture": fixture_id})
        resp.raise_for_status()
        data = resp.json()
    entries = data.get("response", [])
    if not entries:
        return {"status": "sem_cobertura", "bets": []}
    entry = entries[0]
    status = entry.get("status", {})
    bets = entry.get("bets", [])
    if status.get("stopped"):
        return {"status": "intervalo", "bets": bets}
    if status.get("blocked"):
        return {"status": "suspenso", "bets": bets}
    if not bets:
        return {"status": "sem_mercados", "bets": []}
    return {"status": "ok", "bets": bets}


# ── Injuries / Predictions ───────────────────────────────────────────────────

async def get_injuries(fixture_id: int) -> list[dict]:
    data = await _get("injuries", {"fixture": fixture_id})
    return data.get("response", [])


async def get_predictions(fixture_id: int) -> dict | None:
    data = await _get("predictions", {"fixture": fixture_id})
    resp = data.get("response", [])
    return resp[0] if resp else None


def _today() -> str:
    from datetime import date
    return date.today().isoformat()
