import asyncio
import sys
sys.stdout.reconfigure(encoding="utf-8")

from api.api_football import _get
from config import LEAGUES, season_for


async def main():
    for name, lid in LEAGUES.items():
        season = season_for(lid)
        data = await _get("standings", {"league": lid, "season": season})
        resp = data.get("response", [])
        errors = data.get("errors", [])
        results = data.get("results", 0)

        if resp:
            league_info = resp[0]["league"]
            standings = league_info.get("standings", [])
            print(f"[OK] {name} (liga {lid}, season {season}): {len(standings)} grupo(s)")
            for group in standings[:2]:
                print(f"  Grupo com {len(group)} times:")
                for entry in group[:3]:
                    print(f"    {entry['rank']}. {entry['team']['name']} - {entry['points']}pts")
        else:
            print(f"[VAZIO] {name} (liga {lid}, season {season}) - results={results}, errors={errors}")


asyncio.run(main())
