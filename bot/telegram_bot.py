import logging
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode, ChatAction
from telegram.error import BadRequest

from agent.sports_agent import run_agent
from config import TELEGRAM_BOT_TOKEN

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

_user_histories: dict[int, list[dict]] = {}


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "*AgenteEsportivo* ativo!\n\n"
        "Posso analisar:\n"
        "• Partidas ao vivo — stats, odds e entrada sugerida\n"
        "• Classificação de ligas\n"
        "• Histórico H2H entre times\n"
        "• Forma recente de um time\n\n"
        "Exemplos de uso:\n"
        "_\"Flamengo x Palmeiras tá rolando, qual entrada?\"_\n"
        "_\"Quais jogos estão ao vivo?\"_\n"
        "_\"Classificação do Brasileirão\"_\n\n"
        "_⚠️ Aposte com responsabilidade._"
    )
    await _safe_send(update, text)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "*Comandos:*\n"
        "/live — Jogos ao vivo agora\n"
        "/hoje — Jogos do dia\n"
        "/reset — Limpar histórico\n"
        "/help — Esta mensagem\n\n"
        "*Perguntas livres:*\n"
        "• _\"[Time A] x [Time B] — qual entrada?\"_\n"
        "• _\"Odds do [Time] x [Time]\"_\n"
        "• _\"H2H Flamengo x Corinthians\"_\n"
        "• _\"Forma recente do Palmeiras\"_"
    )
    await _safe_send(update, text)


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _user_histories[update.effective_user.id] = []
    await update.message.reply_text("Historico limpo. Nova conversa iniciada.")


async def cmd_live(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"[CMD] /live — @{user.username or user.first_name} ({user.id})")
    await update.message.chat.send_action(ChatAction.TYPING)
    user_id = user.id
    history = _user_histories.get(user_id, [])
    response, new_history = await run_agent("Liste todas as partidas ao vivo agora.", history)
    _user_histories[user_id] = new_history
    await _send_long_message(update, response)


async def cmd_hoje(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"[CMD] /hoje — @{user.username or user.first_name} ({user.id})")
    await update.message.chat.send_action(ChatAction.TYPING)
    user_id = user.id
    history = _user_histories.get(user_id, [])
    response, new_history = await run_agent("Quais são os jogos de hoje?", history)
    _user_histories[user_id] = new_history
    await _send_long_message(update, response)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name or str(user_id)
    user_text = update.message.text.strip()
    if not user_text:
        return

    logger.info(f"[MSG] @{username} ({user_id}): {user_text[:120]}")
    await update.message.chat.send_action(ChatAction.TYPING)
    history = _user_histories.get(user_id, [])

    try:
        import time
        t0 = time.monotonic()
        response, new_history = await run_agent(user_text, history)
        elapsed = time.monotonic() - t0
        _user_histories[user_id] = new_history
        logger.info(f"[RES] @{username} ({user_id}) — {elapsed:.1f}s — {len(response)} chars")
    except Exception as e:
        logger.error(f"[ERR] @{username} ({user_id}): {e}", exc_info=True)
        response = "Ocorreu um erro ao processar sua solicitacao. Tente novamente."

    await _send_long_message(update, response)


async def _safe_send(update: Update, text: str) -> None:
    try:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except BadRequest:
        await update.message.reply_text(text)


async def _send_long_message(update: Update, text: str) -> None:
    MAX_LEN = 4000
    chunks = []
    while len(text) > MAX_LEN:
        # quebra em parágrafo mais próximo do limite
        split_at = text.rfind("\n\n", 0, MAX_LEN)
        if split_at == -1:
            split_at = MAX_LEN
        chunks.append(text[:split_at].strip())
        text = text[split_at:].strip()
    chunks.append(text)

    for chunk in chunks:
        try:
            await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
        except BadRequest:
            # fallback sem markdown se tiver caractere especial problemático
            await update.message.reply_text(chunk)


def build_application() -> Application:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("live", cmd_live))
    app.add_handler(CommandHandler("hoje", cmd_hoje))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return app


async def set_bot_commands(app: Application) -> None:
    commands = [
        BotCommand("start", "Iniciar o agente"),
        BotCommand("help", "Ajuda"),
        BotCommand("live", "Partidas ao vivo"),
        BotCommand("hoje", "Jogos de hoje"),
        BotCommand("reset", "Limpar historico"),
    ]
    await app.bot.set_my_commands(commands)
