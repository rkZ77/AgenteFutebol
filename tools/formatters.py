"""
Converte dados brutos das tools em strings compactas antes de enviar ao Claude.
Reduz ~70-80% dos tokens comparado ao JSON completo.
"""


def fmt_live_matches(matches: list[dict]) -> str:
    if not matches:
        return "LISTA COMPLETA — 0 partidas ao vivo nas ligas monitoradas agora."
    lines = [f"LISTA COMPLETA — {len(matches)} partida(s) ao vivo nas ligas monitoradas:"]
    for m in matches:
        lines.append(
            f"ID:{m['fixture_id']} | {m['home']} {m['score']} {m['away']} "
            f"| {m['minute']}' | {m['league']}"
        )
    return "\n".join(lines)


def fmt_today_matches(matches: list[dict]) -> str:
    if not matches:
        return "LISTA COMPLETA — 0 jogos encontrados nas ligas monitoradas hoje."
    lines = [f"LISTA COMPLETA — {len(matches)} jogo(s) nas ligas monitoradas hoje:"]
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
    is_halftime = info.get("status", "").lower() in ("halftime", "half time", "ht")

    if stats:
        teams = list(stats.keys())
        if len(teams) == 2:
            t1, t2 = teams
            keys = [
                "Ball Possession", "Total Shots", "Shots on Goal",
                "Corner Kicks", "Fouls", "Yellow Cards", "Red Cards",
                "expected_goals",
            ]
            labels = ["Posse", "Chutes", "A gol", "Escanteios", "Faltas", "Amarelos", "Vermelhos", "xG"]
            rows = [f"{'':16} {t1[:12]:>12} {t2[:12]:>12}"]
            for label, key in zip(labels, keys):
                v1 = stats[t1].get(key) or "0"
                v2 = stats[t2].get(key) or "0"
                rows.append(f"{label:<16} {str(v1):>12} {str(v2):>12}")
            parts.append("STATS:\n" + "\n".join(rows))
    elif is_halftime:
        parts.append("STATS: indisponíveis no intervalo — API não fornece stats durante o HT.")

    events = data.get("events", [])
    if events:
        ev_lines = []
        for e in events:
            ev_lines.append(
                f"{e['minute']}' {e['type'].upper()} {e['team']} ({e['player']}) — {e['detail']}"
            )
        parts.append("EVENTOS:\n" + "\n".join(ev_lines))
    elif is_halftime:
        parts.append("EVENTOS: indisponíveis no intervalo — API não fornece eventos durante o HT.")

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


def _fmt_group_table(teams: list[dict]) -> str:
    header = f"{'Pos':>3} {'Time':<22} {'Pts':>3} {'J':>2} {'V':>2} {'E':>2} {'D':>2} {'SG':>4} {'Forma':<6} {'Status'}"
    rows = [header]
    for t in teams:
        status = f"[{t['description']}]" if t.get("description") else ""
        rows.append(
            f"{t['pos']:>3} {t['team']:<22} {t['pts']:>3} {t['played']:>2} "
            f"{t['won']:>2} {t['draw']:>2} {t['lost']:>2} {t['gd']:>+4} {t.get('form',''):>6} {status}"
        )
    return "\n".join(rows)


def fmt_standings(data: list | dict) -> str:
    if isinstance(data, dict) and "error" in data:
        return data["error"]
    if not data:
        return "Classificação não disponível."

    # Formato de grupos (Libertadores, Sul-Am, Copa do Mundo)
    if isinstance(data, list) and data and isinstance(data[0], dict) and "teams" in data[0]:
        parts = []
        for g in data:
            group_name = g["group"].split(",")[-1].strip() if "," in g["group"] else g["group"]
            parts.append(f"{group_name}:\n{_fmt_group_table(g['teams'])}")
        return "\n\n".join(parts)

    # Formato flat (Brasileirão A/B)
    lines = [f"{'Pos':>3} {'Time':<22} {'Pts':>3} {'J':>2} {'V':>2} {'E':>2} {'D':>2} {'SG':>4} {'Forma':<6}"]
    teams = data[0]["teams"] if (data and isinstance(data[0], dict) and "teams" in data[0]) else data
    for t in teams[:20]:
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


def fmt_lineups(data: list[dict]) -> str:
    if not data:
        return "Escalações não disponíveis para esta partida."
    parts = []
    for t in data:
        lines = [
            f"{t['team']} [{t['formation']}] — Técnico: {t['coach']}",
            f"  GK:  {', '.join(t['gk'])}",
            f"  DEF: {', '.join(t['defenders'])}",
            f"  MED: {', '.join(t['midfielders'])}",
            f"  ATA: {', '.join(t['forwards'])}",
            f"  BNC: {', '.join(t['substitutes'][:6])}{'...' if len(t['substitutes']) > 6 else ''}",
        ]
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def fmt_team_season_stats(data: dict) -> str:
    if "error" in data:
        return data["error"]
    agf = data.get("avg_goals_for", {})
    aga = data.get("avg_goals_against", {})
    lines = [
        f"Stats temporada {data['team']} | {data['league']} {data['season']}",
        f"Jogos: {data['played']} | V:{data['wins']} E:{data['draws']} D:{data['losses']}",
        f"Media gols marcados: casa {agf.get('home','?')} | fora {agf.get('away','?')} | total {agf.get('total','?')}",
        f"Media gols sofridos: casa {aga.get('home','?')} | fora {aga.get('away','?')} | total {aga.get('total','?')}",
        f"Clean sheets: {data.get('clean_sheets',0)} | Sem marcar: {data.get('failed_to_score',0)}",
        f"Maior vitoria: {data.get('biggest_win','?')} | Maior derrota: {data.get('biggest_loss','?')}",
        f"Forma recente: {data.get('form','?')}",
    ]
    return "\n".join(lines)
