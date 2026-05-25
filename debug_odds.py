"""Script de diagnóstico — roda direto: python debug_odds.py"""
import asyncio
import httpx
import json
from dotenv import load_dotenv
import os

load_dotenv()
KEY = os.getenv("API_FOOTBALL_KEY", "")
BASE = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": KEY}


async def get(endpoint: str, params: dict) -> dict:
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(f"{BASE}/{endpoint}", headers=HEADERS, params=params)
        return r.json()


async def main():
    # 1. Busca um jogo ao vivo
    print("=== JOGOS AO VIVO ===")
    live = await get("fixtures", {"live": "all"})
    fixtures = live.get("response", [])
    print(f"Total ao vivo: {len(fixtures)}")
    if not fixtures:
        print("Nenhum jogo ao vivo no momento. Tentando jogos de hoje...")
        today = await get("fixtures", {"date": "2026-05-25", "league": 71, "season": 2026})
        fixtures = today.get("response", [])
        print(f"Jogos hoje Brasileirao: {len(fixtures)}")

    if not fixtures:
        print("Sem jogos para testar. Tente em outro horário.")
        return

    f = fixtures[0]
    fid = f["fixture"]["id"]
    home = f["teams"]["home"]["name"]
    away = f["teams"]["away"]["name"]
    print(f"\nTestando fixture: {fid} | {home} x {away}")

    # 2. Odds pré-jogo
    print("\n=== ODDS PRÉ-JOGO (/odds) ===")
    odds = await get("odds", {"fixture": fid})
    print(f"errors: {odds.get('errors')}")
    print(f"results: {odds.get('results')}")
    resp = odds.get("response", [])
    print(f"bookmakers retornados: {len(resp[0].get('bookmakers', [])) if resp else 0}")
    if resp and resp[0].get("bookmakers"):
        bm = resp[0]["bookmakers"][0]
        print(f"  Primeiro bookmaker: {bm['bookmaker']['name']}")
        print(f"  Mercados: {[b['name'] for b in bm['bets'][:5]]}")
    else:
        print("  Nenhuma odd retornada")
        print(f"  Resposta completa: {json.dumps(odds, indent=2)[:500]}")

    # 3. Odds ao vivo
    print("\n=== ODDS AO VIVO (/odds/live) ===")
    live_odds = await get("odds/live", {"fixture": fid})
    print(f"errors: {live_odds.get('errors')}")
    print(f"results: {live_odds.get('results')}")
    resp_live = live_odds.get("response", [])
    print(f"entradas retornadas: {len(resp_live)}")
    if resp_live:
        entry = resp_live[0]
        bets = entry.get("bets", [])
        print(f"  Mercados ao vivo: {[b['name'] for b in bets[:5]]}")
    else:
        print("  Nenhuma odd ao vivo retornada")
        print(f"  Resposta completa: {json.dumps(live_odds, indent=2)[:500]}")

    # 4. Verifica status da conta
    print("\n=== STATUS DA CONTA ===")
    status = await get("status", {})
    print(json.dumps(status, indent=2))


asyncio.run(main())
