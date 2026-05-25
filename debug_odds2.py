import asyncio
import httpx
import os
from datetime import date
from dotenv import load_dotenv

load_dotenv()

KEY = os.getenv("API_FOOTBALL_KEY")
BASE = "https://v3.football.api-sports.io"
H = {"x-apisports-key": KEY}


async def main():
    async with httpx.AsyncClient(timeout=15) as c:
        # Jogos ao vivo
        live = (await c.get(f"{BASE}/fixtures", headers=H, params={"live": "all"})).json()
        fixtures = live.get("response", [])
        print(f"Ao vivo: {len(fixtures)} jogos")

        # Jogos de hoje Brasileirao A
        today = date.today().isoformat()
        br = (await c.get(f"{BASE}/fixtures", headers=H, params={"date": today, "league": 71, "season": 2026})).json()
        br_fixtures = br.get("response", [])
        print(f"Brasileirao hoje ({today}): {len(br_fixtures)} jogos")
        for f in br_fixtures[:5]:
            fid = f["fixture"]["id"]
            home = f["teams"]["home"]["name"]
            away = f["teams"]["away"]["name"]
            status = f["fixture"]["status"]["short"]
            print(f"  {fid} | {home} x {away} | {status}")

        test_fixtures = fixtures or br_fixtures
        if not test_fixtures:
            print("Sem fixtures para testar. Tentando qualquer jogo de hoje...")
            any_today = (await c.get(f"{BASE}/fixtures", headers=H, params={"date": today})).json()
            test_fixtures = any_today.get("response", [])
            print(f"Jogos hoje (qualquer liga): {len(test_fixtures)}")

        if not test_fixtures:
            print("Nenhum jogo encontrado.")
            return

        fid = test_fixtures[0]["fixture"]["id"]
        home = test_fixtures[0]["teams"]["home"]["name"]
        away = test_fixtures[0]["teams"]["away"]["name"]
        league = test_fixtures[0]["league"]["name"]
        status = test_fixtures[0]["fixture"]["status"]["short"]
        print(f"\nTestando fixture {fid}: {home} x {away} ({league}) [{status}]")

        # Pre-jogo
        pre = (await c.get(f"{BASE}/odds", headers=H, params={"fixture": fid})).json()
        n_results = pre.get("results", 0)
        errors = pre.get("errors", [])
        print(f"Pre-jogo odds: results={n_results}, errors={errors}")
        if n_results > 0:
            bms = pre["response"][0].get("bookmakers", [])
            print(f"  Bookmakers: {len(bms)}")
            if bms:
                bm = bms[0]
                bm_name = bm.get("bookmaker", {}).get("name", "?")
                bets = bm.get("bets", [])
                print(f"  {bm_name}: {[b['name'] for b in bets[:4]]}")
                if bets:
                    print(f"  Exemplo: {bets[0]['name']} -> {bets[0].get('values', [])[:3]}")

        # Live odds
        lo = (await c.get(f"{BASE}/odds/live", headers=H, params={"fixture": fid})).json()
        n_lo = lo.get("results", 0)
        lo_errors = lo.get("errors", [])
        print(f"Live odds: results={n_lo}, errors={lo_errors}")
        if n_lo > 0:
            entry = lo["response"][0]
            bets = entry.get("bets", [])
            status_lo = entry.get("status", {})
            print(f"  Status: stopped={status_lo.get('stopped')} blocked={status_lo.get('blocked')}")
            print(f"  Mercados ({len(bets)}): {[b['name'] for b in bets[:5]]}")

asyncio.run(main())
