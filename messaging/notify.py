import asyncio

import requests

from config import DISCORD_BOT_TOKEN, WEBHOOK_URL

try:
    if DISCORD_BOT_TOKEN:
        from messaging.discord_bot import discord_bot
    else:
        discord_bot = None
except ImportError:
    discord_bot = None


def _send_with_bot(message: str) -> bool:
    if not discord_bot or not discord_bot.is_ready or not discord_bot.event_loop:
        return False
    try:
        future = asyncio.run_coroutine_threadsafe(
            discord_bot.send_message(message), discord_bot.event_loop
        )
        return future.result(timeout=10)
    except Exception as exc:
        print(f"Discord notification failed: {exc}")
        return False


def _send_with_webhook(message: str) -> bool:
    if not WEBHOOK_URL:
        return False
    try:
        response = requests.post(WEBHOOK_URL, json={"content": message}, timeout=10)
        response.raise_for_status()
        return True
    except requests.RequestException as exc:
        print(f"Webhook notification failed: {exc}")
        return False


def send_notification(payload) -> bool:
    message = payload.get("content", str(payload)) if isinstance(payload, dict) else str(payload)
    return _send_with_bot(message) or _send_with_webhook(message)


send_webhook = send_notification
