import asyncio
import logging
from typing import Any
import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, MAX_TOKENS, MAX_HISTORY_MESSAGES

logger = logging.getLogger(__name__)
from agent.prompts import SYSTEM_PROMPT
from tools.live_matches import get_live_matches, get_today_matches
from tools.match_stats import get_match_full_stats, find_and_get_stats, get_match_injuries, get_match_prediction, get_match_lineups, get_match_player_stats
from tools.odds import get_prematch_odds, get_live_match_odds
from tools.standings import get_league_standings
from tools.head_to_head import get_h2h, get_team_recent_form, get_team_stats_season, get_team_historical_stats, get_team_historical_stats_any
from tools.formatters import (
    fmt_live_matches, fmt_today_matches, fmt_match_stats,
    fmt_odds, fmt_live_odds, fmt_standings, fmt_h2h, fmt_team_form,
    fmt_injuries, fmt_prediction, fmt_team_season_stats, fmt_lineups,
    fmt_team_historical_stats, fmt_player_stats, fmt_team_historical_stats_any,
)


client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

TOOLS: list[dict] = [
    {
        "name": "get_live_matches",
        "description": "Lista todas as partidas de futebol ao vivo agora. Retorna fixture_id, times, placar, minuto e liga.",
        "input_schema": {
            "type": "object",
            "properties": {
                "only_featured": {
                    "type": "boolean",
                    "description": "Se true, filtra apenas ligas monitoradas (Brasileirão, Copa do Mundo, etc). Default: true.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_today_matches",
        "description": "Lista os jogos programados para hoje, ao vivo ou não.",
        "input_schema": {
            "type": "object",
            "properties": {
                "league_id": {
                    "type": "integer",
                    "description": "ID da liga para filtrar. Opcional.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_match_stats",
        "description": "Retorna estatísticas detalhadas de uma partida pelo fixture_id: posse de bola, chutes, escanteios, cartões, faltas e eventos (gols, cartões com minuto).",
        "input_schema": {
            "type": "object",
            "properties": {
                "fixture_id": {
                    "type": "integer",
                    "description": "ID único da partida (fixture_id).",
                }
            },
            "required": ["fixture_id"],
        },
    },
    {
        "name": "find_match_stats",
        "description": "Busca uma partida ao vivo pelo nome dos dois times e retorna estatísticas completas. Use quando o usuário menciona dois times sem fornecer fixture_id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "team1": {
                    "type": "string",
                    "description": "Nome ou parte do nome do primeiro time (ex: 'Flamengo', 'Palmeiras').",
                },
                "team2": {
                    "type": "string",
                    "description": "Nome ou parte do nome do segundo time.",
                },
            },
            "required": ["team1", "team2"],
        },
    },
    {
        "name": "get_prematch_odds",
        "description": "Retorna as odds pré-jogo de uma partida: 1x2, ambas marcam, over/under gols, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "fixture_id": {
                    "type": "integer",
                    "description": "ID único da partida.",
                }
            },
            "required": ["fixture_id"],
        },
    },
    {
        "name": "get_live_odds",
        "description": "Retorna as odds ao vivo de uma partida em andamento.",
        "input_schema": {
            "type": "object",
            "properties": {
                "fixture_id": {
                    "type": "integer",
                    "description": "ID único da partida.",
                }
            },
            "required": ["fixture_id"],
        },
    },
    {
        "name": "get_standings",
        "description": "Retorna a classificação de uma liga. Ligas disponíveis: brasileirao_a, brasileirao_b, copa_do_brasil, libertadores, sul_americana, copa_do_mundo, champions, premier_league, la_liga.",
        "input_schema": {
            "type": "object",
            "properties": {
                "league_name": {
                    "type": "string",
                    "description": "Nome da liga (ex: 'brasileirao_a', 'copa_do_brasil', 'champions').",
                }
            },
            "required": ["league_name"],
        },
    },
    {
        "name": "get_h2h",
        "description": "Retorna o histórico de confrontos diretos (Head-to-Head) entre dois times.",
        "input_schema": {
            "type": "object",
            "properties": {
                "team1": {
                    "type": "string",
                    "description": "Nome do primeiro time.",
                },
                "team2": {
                    "type": "string",
                    "description": "Nome do segundo time.",
                },
                "last": {
                    "type": "integer",
                    "description": "Quantidade de jogos a buscar no histórico. Default: 8.",
                },
            },
            "required": ["team1", "team2"],
        },
    },
    {
        "name": "get_team_form",
        "description": "Retorna a forma recente de um time (últimos jogos: V=vitória, E=empate, D=derrota).",
        "input_schema": {
            "type": "object",
            "properties": {
                "team_name": {"type": "string", "description": "Nome do time."},
                "last": {"type": "integer", "description": "Quantidade de jogos recentes. Default: 5."},
            },
            "required": ["team_name"],
        },
    },
    {
        "name": "get_injuries",
        "description": "Retorna jogadores lesionados e suspensos de uma partida. Use antes de análises pré-jogo ou ao vivo para identificar desfalques importantes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "fixture_id": {"type": "integer", "description": "ID único da partida."},
            },
            "required": ["fixture_id"],
        },
    },
    {
        "name": "get_prediction",
        "description": "Retorna a previsão da API para uma partida: vencedor sugerido, probabilidades (%), gols esperados, over/under e comparativo entre os times.",
        "input_schema": {
            "type": "object",
            "properties": {
                "fixture_id": {"type": "integer", "description": "ID único da partida."},
            },
            "required": ["fixture_id"],
        },
    },
    {
        "name": "get_lineups",
        "description": "Retorna as escalações confirmadas de uma partida: formação, titulares organizados por posição (GK/DEF/MED/ATA) e banco de reservas de cada time. Disponível a partir de ~1h antes do jogo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "fixture_id": {"type": "integer", "description": "ID único da partida."},
            },
            "required": ["fixture_id"],
        },
    },
    {
        "name": "get_team_season_stats",
        "description": "Retorna estatísticas do time na temporada atual de uma liga específica: média de gols marcados/sofridos (casa e fora), clean sheets, jogos sem marcar, maior vitória/derrota e forma recente. Use no fluxo de análise para entender o padrão de gols do time na competição.",
        "input_schema": {
            "type": "object",
            "properties": {
                "team_name": {"type": "string", "description": "Nome do time (ex: 'Flamengo', 'LDU')."},
                "league_name": {"type": "string", "description": "Nome da liga (ex: 'libertadores', 'brasileirao_a', 'sul_americana')."},
            },
            "required": ["team_name", "league_name"],
        },
    },
    {
        "name": "get_team_historical_stats",
        "description": "Busca stats reais dos últimos N jogos finalizados do time na liga: média de escanteios, chutes, posse, gols marcados/sofridos, cartões e faltas. Use para responder perguntas sobre padrões históricos (ex: 'Corinthians costuma fazer muitos escanteios em casa?').",
        "input_schema": {
            "type": "object",
            "properties": {
                "team_name": {"type": "string", "description": "Nome do time."},
                "league_name": {"type": "string", "description": "Nome da liga (ex: 'libertadores', 'brasileirao_a')."},
                "last": {"type": "integer", "description": "Quantidade de jogos a analisar. Default: 8."},
                "venue": {"type": "string", "enum": ["home", "away", "all"], "description": "Filtrar por casa ('home'), fora ('away') ou todos ('all'). Default: 'all'."},
            },
            "required": ["team_name", "league_name"],
        },
    },
    {
        "name": "get_player_stats",
        "description": "Retorna stats individuais de todos os jogadores de uma partida: rating, gols, assistências, chutes, passes-chave, desarmes, dribles e cartões. Útil para identificar quem está em melhor forma, quem dominou o jogo e embasar mercados de artilheiro.",
        "input_schema": {
            "type": "object",
            "properties": {
                "fixture_id": {"type": "integer", "description": "ID único da partida."},
            },
            "required": ["fixture_id"],
        },
        "cache_control": {"type": "ephemeral"},
    },
    {
        "name": "get_team_stats_any_league",
        "description": "Busca stats reais dos últimos N jogos do time em QUALQUER competição (sem filtro de liga). Use como fallback quando o time não tem dados suficientes na liga do jogo (ex: times estrangeiros na Libertadores, estreantes). Retorna médias de escanteios, chutes, posse, gols, cartões e faltas com breakdown 1ºT/2ºT, além de quais competições foram incluídas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "team_name": {"type": "string", "description": "Nome do time."},
                "last": {"type": "integer", "description": "Quantidade de jogos a analisar. Default: 8."},
                "venue": {"type": "string", "enum": ["home", "away", "all"], "description": "Filtrar por casa ('home'), fora ('away') ou todos ('all'). Default: 'all'."},
            },
            "required": ["team_name"],
        },
    },
]


async def _execute_tool(tool_name: str, tool_input: dict) -> Any:
    if tool_name == "get_live_matches":
        return fmt_live_matches(await get_live_matches(tool_input.get("only_featured", True)))
    elif tool_name == "get_today_matches":
        return fmt_today_matches(await get_today_matches(tool_input.get("league_id")))
    elif tool_name == "get_match_stats":
        return fmt_match_stats(await get_match_full_stats(tool_input["fixture_id"]))
    elif tool_name == "find_match_stats":
        return fmt_match_stats(await find_and_get_stats(tool_input["team1"], tool_input["team2"]))
    elif tool_name == "get_prematch_odds":
        return fmt_odds(await get_prematch_odds(tool_input["fixture_id"]))
    elif tool_name == "get_live_odds":
        return fmt_live_odds(await get_live_match_odds(tool_input["fixture_id"]))
    elif tool_name == "get_standings":
        return fmt_standings(await get_league_standings(tool_input["league_name"]))
    elif tool_name == "get_h2h":
        return fmt_h2h(await get_h2h(tool_input["team1"], tool_input["team2"], tool_input.get("last", 8)))
    elif tool_name == "get_team_form":
        return fmt_team_form(await get_team_recent_form(tool_input["team_name"], tool_input.get("last", 5)))
    elif tool_name == "get_injuries":
        return fmt_injuries(await get_match_injuries(tool_input["fixture_id"]))
    elif tool_name == "get_lineups":
        return fmt_lineups(await get_match_lineups(tool_input["fixture_id"]))
    elif tool_name == "get_prediction":
        return fmt_prediction(await get_match_prediction(tool_input["fixture_id"]))
    elif tool_name == "get_team_season_stats":
        return fmt_team_season_stats(await get_team_stats_season(tool_input["team_name"], tool_input["league_name"]))
    elif tool_name == "get_player_stats":
        return fmt_player_stats(await get_match_player_stats(tool_input["fixture_id"]))
    elif tool_name == "get_team_historical_stats":
        return fmt_team_historical_stats(await get_team_historical_stats(
            tool_input["team_name"],
            tool_input["league_name"],
            tool_input.get("last", 8),
            tool_input.get("venue", "all"),
        ))
    elif tool_name == "get_team_stats_any_league":
        return fmt_team_historical_stats_any(await get_team_historical_stats_any(
            tool_input["team_name"],
            tool_input.get("last", 8),
            tool_input.get("venue", "all"),
        ))
    else:
        return f"Tool desconhecida: {tool_name}"


def _clean_history(messages: list[dict]) -> list[dict]:
    """Mantém só pares texto user/assistant — descarta tool_use e tool_result."""
    result = []
    for msg in messages:
        content = msg["content"]
        if isinstance(content, str) and content:
            result.append(msg)
            continue
        if not isinstance(content, list):
            continue
        # Descarta mensagens que são só tool_results
        if content and isinstance(content[0], dict) and content[0].get("type") == "tool_result":
            continue
        # Extrai só blocos de texto de mensagens do assistant
        text_blocks = []
        for block in content:
            if hasattr(block, "type") and block.type == "text":
                text_blocks.append({"type": "text", "text": block.text})
            elif isinstance(block, dict) and block.get("type") == "text":
                text_blocks.append(block)
        if text_blocks:
            result.append({"role": msg["role"], "content": text_blocks})
    return result


async def run_agent(user_message: str, history: list[dict]) -> tuple[str, list[dict]]:
    history = history[-MAX_HISTORY_MESSAGES:]
    messages = history + [{"role": "user", "content": user_message}]

    while True:
        response = await asyncio.to_thread(
            client.messages.create,
            model=CLAUDE_MODEL,
            max_tokens=MAX_TOKENS,
            system=[{
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            tools=TOOLS,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        usage = response.usage
        cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
        cache_create = getattr(usage, "cache_creation_input_tokens", 0) or 0
        logger.debug(
            f"[TOKENS] input={usage.input_tokens} cache_read={cache_read} cache_write={cache_create} output={usage.output_tokens}"
        )

        if response.stop_reason == "end_turn":
            text = next(
                (block.text for block in response.content if hasattr(block, "text")),
                "Sem resposta.",
            )
            # Salva só pares texto limpos — nunca tool_use/tool_result orphans
            updated_history = _clean_history(messages)[-MAX_HISTORY_MESSAGES:]
            return text, updated_history

        if response.stop_reason == "tool_use":
            tool_results = []
            tool_calls = [b for b in response.content if b.type == "tool_use"]

            results = await asyncio.gather(
                *[_execute_tool(tc.name, tc.input) for tc in tool_calls],
                return_exceptions=True,
            )

            for tc, result in zip(tool_calls, results):
                content = f"ERRO: {result}" if isinstance(result, Exception) else str(result)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": content,
                })

            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return "Não foi possível gerar uma resposta.", history
