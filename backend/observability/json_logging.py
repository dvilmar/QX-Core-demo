from __future__ import annotations

import json
import logging
import os
from logging.handlers import TimedRotatingFileHandler


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def attach_json_handler(log_dir: str, filename: str = "api.jsonl") -> logging.Handler:
    os.makedirs(log_dir, exist_ok=True)
    handler = TimedRotatingFileHandler(os.path.join(log_dir, filename), when="midnight", backupCount=30)
    handler.setFormatter(JsonFormatter())
    logging.getLogger().addHandler(handler)
    return handler
