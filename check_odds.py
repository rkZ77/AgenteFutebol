import asyncio, httpx, os
from dotenv import load_dotenv
load_dotenv()

KEY = os.getenv("API_FOOTBALL_KEY")
BASE = "https://v3.football.api-sports.io"
H = {"x-apisports-key": KEY}


async def main():
    async with httpx.AsyncClient(timeout=15) as c:

        # 1. Jogos ao vivo
        live = (await c.get(f"{BASE}/fixtures", headers=H, params={"live": "all"})).json()
        fixtures = live.get("response", [])
        print(f"Jogos ao vivo: {len(fixtures)}")
        for f in fixtures[:8]:
            fid = f["fixture"]["id"]
            home = f["teams"]["home"]["name"]
            away = f["teams"]["away"]["name"]
            league = f["league"]["name"]
            minute = f["fixture"]["status"].get("elapsed", 0)
            print(f"  {fid} | {home} x {away} | {league} | {minute}'")

        if not fixtures:
            print("Nenhum ao vivo. Buscando jogos de hoje (Brasileirao A)...")
            today = (await c.get(f"{BASE}/fixtures", headers=H, params={"date": "2026-05-25", "league": 71, "season": 2026})).json()
            fixtures = today.get("response", [])
            for f in fixtures[:8]:
                fid = f["fixture"]["id"]
                home = f["teams"]["home"]["name"]
                away = f["teams"]["away"]["name"]
                status = f["fixture"]["status"]["short"]
                print(f"  {fid} | {home} x {away} | {status}")

        if not fixtures:
            print("Sem jogos para testar.")
            return

        fid = fixtures[0]["fixture"]["id"]
        print(f"\n--- Testando fixture {fid} ---")

        # 2. Odds pre-jogo
        pre = (await c.get(f"{BASE}/odds", headers=H, params={"fixture": fid})).json()
        pre_resp = pre.get("response", [])
        pre_bm = len(pre_resp[0].get("bookmakers", [])) if pre_resp else 0
        print(f"Pre-jogo: results={pre['results']}  bookmakers={pre_bm}")
        if pre_bm > 0:
            bm = pre_resp[0]["bookmakers"][0]
            bm_name = bm.get("bookmaker", {}).get("name") or bm.get("name", "?")
            bets_names = [b["name"] for b in bm.get("bets", [])[:4]]
            print(f"  {bm_name}: {bets_names}")
            # mostra primeira odd do primeiro mercado
            if bm.get("bets"):
                first_bet = bm["bets"][0]
                print(f"  Exemplo — {first_bet['name']}: {first_bet.get('values', [])[:3]}")

        # 3. Odds ao vivo
        lo = (await c.get(f"{BASE}/odds/live", headers=H, params={"fixture": fid})).json()
        lo_resp = lo.get("response", [])
        bets_n = len(lo_resp[0].get("bets", [])) if lo_resp else 0
        stopped = lo_resp[0].get("status", {}).get("stopped") if lo_resp else "N/A"
        blocked = lo_resp[0].get("status", {}).get("blocked") if lo_resp else "N/A"
        print(f"Live:     results={lo['results']}  bets={bets_n}  stopped={stopped}  blocked={blocked}")
        if bets_n > 0:
            print(f"  Mercados: {[b['name'] for b in lo_resp[0]['bets'][:5]]}")
            b0 = lo_resp[0]["bets"][0]
            print(f"  {b0['name']}: {b0['values']}")

asyncio.run(main())
