import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

HALT_FILENAME = ".HALT"


def runtime_dir() -> str:
    return os.environ.get("QX_DATA_DIR", "data")


class KillSwitch:
    def __init__(self, directory: str | None = None) -> None:
        self.directory = directory or runtime_dir()

    @property
    def path(self) -> str:
        return os.path.join(self.directory, HALT_FILENAME)

    def active(self) -> bool:
        return os.path.exists(self.path)

    def trip(self, by: str, reason: str) -> None:
        os.makedirs(self.directory, exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"tripped_at_unix": time.time(), "by": by, "reason": reason}, f)
        os.replace(tmp, self.path)
        logger.warning("kill switch tripped by %s: %s", by, reason)

    def clear(self) -> bool:
        try:
            os.remove(self.path)
        except FileNotFoundError:
            return False
        logger.warning("kill switch cleared")
        return True

    def info(self) -> dict[str, Any] | None:
        """None when inactive; {} when active but unreadable."""
        if not self.active():
            return None
        try:
            with open(self.path, encoding="utf-8") as f:
                parsed = json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
