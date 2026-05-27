import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

API_FOOTBALL_BASE = "https://v3.football.api-sports.io"
API_FOOTBALL_HEADERS = {
    "x-apisports-key": API_FOOTBALL_KEY,
    "x-rapidapi-host": "v3.football.api-sports.io",
    "x-rapidapi-key": API_FOOTBALL_KEY,
}
API_TIMEZONE = "America/Sao_Paulo"

# Ligas monitoradas — nome: id
LEAGUES = {
    "brasileirao_a":  71,
    "brasileirao_b":  72,
    "copa_do_brasil": 73,
    "libertadores":   13,
    "sul_americana":  11,
    "copa_do_mundo":   1,
}

LEAGUE_SEASONS: dict[int, int] = {
    71: 2026,   # Brasileirão Série A
    72: 2026,   # Brasileirão Série B
    73: 2026,   # Copa do Brasil
    13: 2026,   # Libertadores
    11: 2026,   # Sul-Americana
    1:  2026,   # Copa do Mundo FIFA 2026
}

FEATURED_LEAGUE_IDS = set(LEAGUES.values())
BRAZILIAN_LEAGUE_IDS = {71, 72, 73}

CLAUDE_MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 2000
MAX_HISTORY_MESSAGES = 2

ODDS_MIN = 1.40
ODDS_MAX = 2.20


def season_for(league_id: int) -> int:
    return LEAGUE_SEASONS.get(league_id, 2026)
