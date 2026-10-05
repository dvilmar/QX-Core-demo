import alerts


def test_notify_is_silent_without_config(monkeypatch):
    for var in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "SLACK_WEBHOOK_URL"):
        monkeypatch.delenv(var, raising=False)
    assert alerts.notify("hello") is False


def test_notify_posts_to_configured_channels(monkeypatch):
    sent = []
    monkeypatch.setattr(alerts, "_post", lambda url, data, ct: sent.append((url, ct)))
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "c")
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.example/x")
    assert alerts.notify("boom") is True
    assert len(sent) == 2


def test_notify_survives_delivery_errors(monkeypatch):
    def boom(*_a):
        raise OSError("down")

    monkeypatch.setattr(alerts, "_post", boom)
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.example/x")
    assert alerts.notify("boom") is False
