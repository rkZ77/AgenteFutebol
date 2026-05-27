from api.api_football import get_head_to_head, search_team, get_team_fixtures, get_team_season_statistics
from config import LEAGUES, season_for


async def _resolve_team_id(name: str) -> int | None:
    teams = await search_team(name)
    if not teams:
        return None
    return teams[0]["team"]["id"]


def _fmt_past_fixture(f: dict) -> dict:
    fixture = f["fixture"]
    teams = f["teams"]
    goals = f["goals"]
    league = f["league"]
    return {
        "date": fixture["date"][:10],
        "league": league["name"],
        "home": teams["home"]["name"],
        "away": teams["away"]["name"],
        "score": f"{goals['home'] or 0} x {goals['away'] or 0}",
        "winner": (
            teams["home"]["name"] if teams["home"]["winner"]
            else teams["away"]["name"] if teams["away"]["winner"]
            else "Empate"
        ),
    }


async def get_h2h(team1_name: str, team2_name: str, last: int = 8) -> dict:
    t1_id = await _resolve_team_id(team1_name)
    t2_id = await _resolve_team_id(team2_name)

    if not t1_id:
        return {"error": f"Time '{team1_name}' não encontrado."}
    if not t2_id:
        return {"error": f"Time '{team2_name}' não encontrado."}

    fixtures = await get_head_to_head(t1_id, t2_id, last)
    if not fixtures:
        return {"error": "Sem histórico de confrontos diretos disponível."}

    past = [_fmt_past_fixture(f) for f in fixtures]

    home_wins = sum(1 for p in past if p["winner"] == past[0]["home"])
    away_wins = sum(1 for p in past if p["winner"] == past[0]["away"])
    draws = sum(1 for p in past if p["winner"] == "Empate")

    # resume wins for each resolved team
    t1_wins = sum(1 for f in fixtures if f["teams"]["home"]["winner"] and f["teams"]["home"]["id"] == t1_id
                  or f["teams"]["away"]["winner"] and f["teams"]["away"]["id"] == t1_id)
    t2_wins = sum(1 for f in fixtures if f["teams"]["home"]["winner"] and f["teams"]["home"]["id"] == t2_id
                  or f["teams"]["away"]["winner"] and f["teams"]["away"]["id"] == t2_id)
    draws_count = len(past) - t1_wins - t2_wins

    return {
        "summary": {
            team1_name: t1_wins,
            team2_name: t2_wins,
            "empates": draws_count,
            "total": len(past),
        },
        "matches": past,
    }


async def get_team_stats_season(team_name: str, league_name: str) -> dict:
    """Estatísticas do time na temporada atual da liga especificada."""
    teams = await search_team(team_name)
    if not teams:
        return {"error": f"Time '{team_name}' não encontrado."}
    team_id = teams[0]["team"]["id"]
    team_real_name = teams[0]["team"]["name"]

    league_key = league_name.lower().replace(" ", "_").replace("ã", "a")
    league_id = None
    for key, lid in LEAGUES.items():
        if league_key in key or key in league_key:
            league_id = lid
            break
    if not league_id:
        return {"error": f"Liga '{league_name}' não encontrada."}

    season = season_for(league_id)
    data = await get_team_season_statistics(team_id, league_id, season)
    if not data:
        return {"error": f"Sem estatísticas de temporada para {team_real_name} em {league_name}."}

    fixtures = data.get("fixtures", {})
    goals = data.get("goals", {})
    avg_goals_for = goals.get("for", {}).get("average", {})
    avg_goals_against = goals.get("against", {}).get("average", {})
    biggest = data.get("biggest", {})
    clean_sheet = data.get("clean_sheet", {})
    failed_to_score = data.get("failed_to_score", {})

    return {
        "team": team_real_name,
        "league": league_name,
        "season": season,
        "played": fixtures.get("played", {}).get("total", 0),
        "wins": fixtures.get("wins", {}).get("total", 0),
        "draws": fixtures.get("draws", {}).get("total", 0),
        "losses": fixtures.get("loses", {}).get("total", 0),
        "avg_goals_for": {
            "home": avg_goals_for.get("home", "0"),
            "away": avg_goals_for.get("away", "0"),
            "total": avg_goals_for.get("total", "0"),
        },
        "avg_goals_against": {
            "home": avg_goals_against.get("home", "0"),
            "away": avg_goals_against.get("away", "0"),
            "total": avg_goals_against.get("total", "0"),
        },
        "clean_sheets": clean_sheet.get("total", 0),
        "failed_to_score": failed_to_score.get("total", 0),
        "biggest_win": biggest.get("wins", {}).get("total", ""),
        "biggest_loss": biggest.get("loses", {}).get("total", ""),
        "form": data.get("form", ""),
    }


async def get_team_recent_form(team_name: str, last: int = 5) -> dict:
    teams = await search_team(team_name)
    if not teams:
        return {"error": f"Time '{team_name}' não encontrado."}
    team_id = teams[0]["team"]["id"]
    fixtures = await get_team_fixtures(team_id, last)
    if not fixtures:
        return {"error": "Sem jogos recentes disponíveis."}

    matches = []
    for f in fixtures:
        fmt = _fmt_past_fixture(f)
        team_is_home = f["teams"]["home"]["id"] == team_id
        team_result = (
            "V" if (team_is_home and f["teams"]["home"]["winner"]) or (not team_is_home and f["teams"]["away"]["winner"])
            else "D" if (team_is_home and f["teams"]["away"]["winner"]) or (not team_is_home and f["teams"]["home"]["winner"])
            else "E"
        )
        fmt["result_for_team"] = team_result
        matches.append(fmt)

    form_str = "".join(m["result_for_team"] for m in matches)
    return {
        "team": teams[0]["team"]["name"],
        "form": form_str,
        "last_matches": matches,
    }
