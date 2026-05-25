"""
Converte dados brutos das tools em strings compactas antes de enviar ao Claude.
Reduz ~70-80% dos tokens comparado ao JSON completo.
"""


def fmt_live_matches(matches: list[dict]) -> str:
    if not matches:
        return "Nenhuma partida ao vivo no momento."
    lines = []
    for m in matches:
        lines.append(
            f"ID:{m['fixture_id']} | {m['home']} {m['score']} {m['away']} "
            f"| {m['minute']}' | {m['league']}"
        )
    return "\n".join(lines)


def fmt_today_matches(matches: list[dict]) -> str:
    if not matches:
        return "Nenhum jogo encontrado para hoje."
    lines = []
    for m in matches:
        status = m["status_short"]
        score = m["score"] if status not in ("NS", "TBD") else "x"
        lines.append(
            f"ID:{m['fixture_id']} | {m['home']} {score} {m['away']} "
            f"| {status} {m['minute']}' | {m['league']}"
        )
    return "\n".join(lines)


def fmt_match_stats(data: dict) -> str:
    if "error" in data:
        return data["error"]

    parts = []

    info = data.get("match_info", {})
    if info:
        parts.append(
            f"{info['home']} {info['score']} {info['away']} | {info['minute']}' | {info['status']}"
        )

    stats = data.get("statistics", {})
    if stats:
        teams = list(stats.keys())
        if len(teams) == 2:
            t1, t2 = teams
            keys = [
                "Ball Possession", "Total Shots", "Shots on Goal",
                "Corner Kicks", "Fouls", "Yellow Cards", "Red Cards",
            ]
            labels = ["Posse", "Chutes", "A gol", "Escanteios", "Faltas", "Amarelos", "Vermelhos"]
            rows = [f"{'':16} {t1[:12]:>12} {t2[:12]:>12}"]
            for label, key in zip(labels, keys):
                v1 = stats[t1].get(key) or "0"
                v2 = stats[t2].get(key) or "0"
                rows.append(f"{label:<16} {str(v1):>12} {str(v2):>12}")
            parts.append("STATS:\n" + "\n".join(rows))

    events = data.get("events", [])
    if events:
        ev_lines = []
        for e in events:
            ev_lines.append(
                f"{e['minute']}' {e['type'].upper()} {e['team']} ({e['player']}) — {e['detail']}"
            )
        parts.append("EVENTOS:\n" + "\n".join(ev_lines))

    return "\n\n".join(parts) if parts else "Sem dados disponíveis."


def _fmt_markets(markets: dict) -> list[str]:
    lines = []
    for market, outcomes in markets.items():
        parts = []
        for outcome, val in outcomes.items():
            if isinstance(val, dict):
                parts.append(f"{outcome}: {val['odd']} ({val['bookmaker']})")
            else:
                parts.append(f"{outcome}: {val}")
        lines.append(f"{market}: {' | '.join(parts)}")
    return lines


def fmt_odds(data: dict) -> str:
    if data.get("error") == "sem_cobertura":
        return "Sem cobertura de odds para esta partida."
    if data.get("status") == "ok" and data.get("markets"):
        return "\n".join(_fmt_markets(data["markets"]))
    return "Odds pré-jogo não disponíveis."


def fmt_live_odds(data: dict) -> str:
    status = data.get("status", "")
    markets = data.get("markets", {})
    lines = _fmt_markets(markets)

    headers = {
        "live":             "",
        "intervalo_sem_odds": "[INTERVALO] Bookmakers pausaram as odds ao vivo. Retornam no 2º tempo.",
        "suspenso_sem_odds":  "[MERCADO SUSPENSO] Odds ao vivo suspensas temporariamente.",
        "sem_cobertura":      "Sem cobertura de odds ao vivo para esta partida.",
    }

    header = headers.get(status, "")
    if not lines:
        return header or "Sem odds disponíveis."
    return header + "\n".join(lines)


def fmt_standings(data: list | dict) -> str:
    if isinstance(data, dict) and "error" in data:
        return data["error"]
    if not data:
        return "Classificação não disponível."
    lines = [f"{'Pos':>3} {'Time':<22} {'Pts':>3} {'J':>2} {'V':>2} {'E':>2} {'D':>2} {'SG':>4} {'Forma':<6}"]
    for t in data[:20]:
        lines.append(
            f"{t['pos']:>3} {t['team']:<22} {t['pts']:>3} {t['played']:>2} "
            f"{t['won']:>2} {t['draw']:>2} {t['lost']:>2} {t['gd']:>+4} {t.get('form',''):>6}"
        )
    return "\n".join(lines)


def fmt_h2h(data: dict) -> str:
    if "error" in data:
        return data["error"]
    summary = data.get("summary", {})
    matches = data.get("matches", [])
    s = " | ".join(f"{k}: {v}" for k, v in summary.items())
    lines = [f"H2H: {s}"]
    for m in matches:
        lines.append(f"{m['date']} {m['home']} {m['score']} {m['away']} → {m['winner']}")
    return "\n".join(lines)


def fmt_injuries(data: list | dict) -> str:
    if isinstance(data, dict) and "error" in data:
        return data["error"]
    if not data:
        return "Sem lesionados/suspensos registrados para esta partida."
    by_team: dict[str, list[str]] = {}
    for p in data:
        team = p.get("team", "?")
        reason = p.get("reason", p.get("type", ""))
        by_team.setdefault(team, []).append(f"{p['player']} ({reason})")
    lines = []
    for team, players in by_team.items():
        lines.append(f"{team}: {', '.join(players)}")
    return "\n".join(lines)


def fmt_prediction(data: dict | None) -> str:
    if not data:
        return "Previsão não disponível para esta partida."
    lines = []
    if data.get("advice"):
        lines.append(f"Conselho: {data['advice']}")
    if data.get("winner"):
        lines.append(f"Vencedor previsto: {data['winner']}")
    pct = data.get("percent", {})
    if pct:
        lines.append(f"Probabilidades: Casa {pct.get('home','?')} | Empate {pct.get('draw','?')} | Fora {pct.get('away','?')}")
    goals = data.get("goals", {})
    if goals:
        lines.append(f"Gols esperados: Casa {goals.get('home','?')} | Fora {goals.get('away','?')}")
    if data.get("under_over") is not None:
        lines.append(f"Under/Over 2.5: {'+' if data['under_over'] and float(str(data['under_over'])) > 0 else ''}{data['under_over']}")
    comp = data.get("comparison", {})
    if comp.get("form"):
        f = comp["form"]
        lines.append(f"Comparação forma: Casa {f.get('home','?')} | Fora {f.get('away','?')}")
    return "\n".join(lines)


def fmt_team_form(data: dict) -> str:
    if "error" in data:
        return data["error"]
    lines = [f"Forma {data['team']}: {data['form']}"]
    for m in data.get("last_matches", []):
        r = m.get("result_for_team", "")
        lines.append(f"{m['date']} {m['home']} {m['score']} {m['away']} [{r}]")
    return "\n".join(lines)
