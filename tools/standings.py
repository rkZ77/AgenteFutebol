from api.api_football import get_standings
from config import LEAGUES, season_for


def _fmt_team_standing(entry: dict) -> dict:
    team = entry["team"]
    all_stats = entry["all"]
    return {
        "pos": entry["rank"],
        "team": team["name"],
        "pts": entry["points"],
        "played": all_stats["played"],
        "won": all_stats["win"],
        "draw": all_stats["draw"],
        "lost": all_stats["lose"],
        "gf": all_stats["goals"]["for"],
        "ga": all_stats["goals"]["against"],
        "gd": entry["goalsDiff"],
        "form": entry.get("form", ""),
    }


async def get_league_standings(league_name: str) -> list[dict] | dict:
    league_name_lower = league_name.lower().replace(" ", "_").replace("ã", "a")
    league_id = None
    for key, lid in LEAGUES.items():
        if league_name_lower in key or key in league_name_lower:
            league_id = lid
            break
    if not league_id:
        try:
            league_id = int(league_name)
        except ValueError:
            return {"error": f"Liga '{league_name}' não encontrada. Use: {list(LEAGUES.keys())}"}

    season = season_for(league_id)
    groups = await get_standings(league_id)
    if not groups:
        return {"error": f"Classificação não disponível para {league_name} (temporada {season})."}

    result = []
    for group in groups:
        result.extend([_fmt_team_standing(e) for e in group])
    return result
