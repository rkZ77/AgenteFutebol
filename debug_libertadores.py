import asyncio
import sys
sys.stdout.reconfigure(encoding="utf-8")

from api.api_football import (
    get_fixture_by_id, get_fixture_statistics, get_fixture_events, get_live_fixtures
)
from config import FEATURED_LEAGUE_IDS


async def main():
    # Pega ao vivo para ter um fixture da Libertadores/Sul-Am
    fixtures = await get_live_fixtures(list(FEATURED_LEAGUE_IDS))
    if not fixtures:
        print("Sem jogos ao vivo")
        return

    for f in fixtures[:3]:
        fid = f["fixture"]["id"]
        home = f["teams"]["home"]["name"]
        away = f["teams"]["away"]["name"]
        status = f["fixture"]["status"]["short"]
        score = f["goals"]
        print(f"\nFixture {fid}: {home} x {away} [{status}]")
        print(f"  Score: {score['home']} x {score['away']}")

        # fixture_by_id
        fd = await get_fixture_by_id(fid)
        if fd:
            print(f"  fixture_by_id OK: {fd['teams']['home']['name']} {fd['goals']['home']} x {fd['goals']['away']} {fd['teams']['away']['name']}")
            print(f"  status: {fd['fixture']['status']['long']} {fd['fixture']['status'].get('elapsed', 0)}'")
        else:
            print("  fixture_by_id: NULO")

        # stats
        stats = await get_fixture_statistics(fid)
        print(f"  Stats: {len(stats)} times com dados")
        for td in stats:
            vals = {s["type"]: s["value"] for s in td["statistics"]}
            print(f"    {td['team']['name']}: shots={vals.get('Total Shots')} corners={vals.get('Corner Kicks')} poss={vals.get('Ball Possession')}")

        # events
        events = await get_fixture_events(fid)
        print(f"  Events: {len(events)} eventos")
        for e in events[:5]:
            print(f"    {e['time']['elapsed']}' {e['type']} {e['team']['name']} ({e['player']['name']})")


asyncio.run(main())
