import asyncio
import sys
sys.stdout.reconfigure(encoding="utf-8")

from tools.live_matches import get_today_matches
from tools.odds import get_prematch_odds
from tools.formatters import fmt_today_matches, fmt_odds


async def main():
    matches = await get_today_matches()
    print("=== Jogos filtrados hoje ===")
    for m in matches:
        fid = m["fixture_id"]
        home = m["home"]
        away = m["away"]
        league = m["league"]
        print(f"  ID:{fid} | {home} x {away} | {league}")

    print()
    for m in matches:
        fid = m["fixture_id"]
        home = m["home"]
        away = m["away"]
        print(f"=== Odds fixture {fid}: {home} x {away} ===")
        result = await get_prematch_odds(fid)
        print(f"  Keys: {list(result.keys())}")
        mkts = result.get("markets", {})
        print(f"  Markets ({len(mkts)}): {list(mkts.keys())[:5]}")
        formatted = fmt_odds(result)
        print(f"  Formatado: {formatted[:300]}")
        print()


asyncio.run(main())
