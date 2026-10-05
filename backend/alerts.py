from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)
_TIMEOUT_S = 5


def _post(url: str, data: bytes, content_type: str) -> None:
    req = urllib.request.Request(url, data=data, headers={"Content-Type": content_type}, method="POST")
    with urllib.request.urlopen(req, timeout=_TIMEOUT_S):
        pass


def notify(message: str) -> bool:
    """Send to every configured channel; True if any delivery succeeded."""
    delivered = False
    token, chat_id = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        try:
            body = urllib.parse.urlencode({"chat_id": chat_id, "text": message}).encode()
            _post(f"https://api.telegram.org/bot{token}/sendMessage", body, "application/x-www-form-urlencoded")
            delivered = True
        except Exception:
            logger.warning("Telegram alert failed", exc_info=True)
    webhook = os.getenv("SLACK_WEBHOOK_URL")
    if webhook:
        try:
            _post(webhook, json.dumps({"text": message}).encode(), "application/json")
            delivered = True
        except Exception:
            logger.warning("Slack alert failed", exc_info=True)
    return delivered
