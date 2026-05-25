from api.api_football import (
    get_fixture_statistics,
    get_fixture_events,
    get_fixture_by_id,
    get_injuries,
    get_predictions,
    search_fixture,
)


async def get_match_full_stats(fixture_id: int) -> dict:
    stats_raw = await get_fixture_statistics(fixture_id)
    events_raw = await get_fixture_events(fixture_id)
    fixture_data = await get_fixture_by_id(fixture_id)

    stats: dict = {}
    for team_data in stats_raw:
        team_name = team_data["team"]["name"]
        stats[team_name] = {}
        for stat in team_data["statistics"]:
            stats[team_name][stat["type"]] = stat["value"]

    events = []
    for e in events_raw:
        events.append({
            "minute": e["time"]["elapsed"],
            "team": e["team"]["name"],
            "player": e["player"]["name"],
            "type": e["type"],
            "detail": e["detail"],
        })

    result: dict = {"statistics": stats, "events": events}

    if fixture_data:
        fixture = fixture_data["fixture"]
        teams = fixture_data["teams"]
        goals = fixture_data["goals"]
        status = fixture["status"]
        result["match_info"] = {
            "home": teams["home"]["name"],
            "away": teams["away"]["name"],
            "score": f"{goals['home'] or 0} x {goals['away'] or 0}",
            "minute": status.get("elapsed") or 0,
            "status": status["long"],
        }

    return result


async def find_and_get_stats(team1: str, team2: str) -> dict:
    fixtures = await search_fixture(team1, team2)
    if not fixtures:
        return {"error": f"Partida entre '{team1}' e '{team2}' não encontrada ao vivo ou hoje."}
    f = fixtures[0]
    fixture_id = f["fixture"]["id"]
    data = await get_match_full_stats(fixture_id)
    data["fixture_id"] = fixture_id
    return data


async def get_match_injuries(fixture_id: int) -> list[dict]:
    raw = await get_injuries(fixture_id)
    result = []
    for p in raw:
        result.append({
            "team": p["team"]["name"],
            "player": p["player"]["name"],
            "reason": p["player"]["reason"],
            "type": p["player"]["type"],
        })
    return result


async def get_match_prediction(fixture_id: int) -> dict | None:
    raw = await get_predictions(fixture_id)
    if not raw:
        return None
    pred = raw.get("predictions", {})
    teams = raw.get("teams", {})
    comparison = raw.get("comparison", {})
    return {
        "winner": pred.get("winner", {}).get("name"),
        "win_or_draw": pred.get("win_or_draw"),
        "advice": pred.get("advice"),
        "percent": pred.get("percent", {}),
        "goals": pred.get("goals", {}),
        "under_over": pred.get("under_over"),
        "home_form": teams.get("home", {}).get("league", {}).get("form", ""),
        "away_form": teams.get("away", {}).get("league", {}).get("form", ""),
        "comparison": {
            k: comparison.get(k, {}) for k in ["form", "att", "def", "poisson_distribution", "h2h"]
        },
    }
