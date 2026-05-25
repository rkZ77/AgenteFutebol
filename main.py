import asyncio
import logging
import sys
import httpx

from bot.telegram_bot import build_application, set_bot_commands
from config import TELEGRAM_BOT_TOKEN, ANTHROPIC_API_KEY, API_FOOTBALL_KEY

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def _check_config() -> bool:
    missing = []
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not ANTHROPIC_API_KEY:
        missing.append("ANTHROPIC_API_KEY")
    if not API_FOOTBALL_KEY:
        missing.append("API_FOOTBALL_KEY")
    if missing:
        logger.error(f"Variaveis de ambiente faltando: {', '.join(missing)}")
        return False
    return True


async def _close_existing_session() -> None:
    """Fecha qualquer sessão de polling ativa no Telegram antes de iniciar."""
    tg_base = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Remove webhook
        await client.post(f"{tg_base}/deleteWebhook", json={"drop_pending_updates": True})
        # Fecha polling ativo com timeout=0 (invalida sessão anterior imediatamente)
        await client.get(f"{tg_base}/getUpdates", params={"offset": -1, "timeout": 0})
    await asyncio.sleep(1)


async def main() -> None:
    if not _check_config():
        sys.exit(1)

    logger.info("AgenteEsportivo iniciando...")
    await _close_existing_session()

    app = build_application()

    async with app:
        await set_bot_commands(app)
        logger.info("Bot iniciado! Aguardando mensagens...")
        await app.updater.start_polling(drop_pending_updates=True)
        await app.start()
        try:
            await asyncio.Event().wait()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Encerrando bot...")
        finally:
            await app.updater.stop()
            await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
