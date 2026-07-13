"""Unit tests for notification dispatcher."""

import json
from unittest.mock import patch

import httpx
import pytest
import respx
from httpx import Response

import pricerecon.core.notifications as notifications_module
from pricerecon.core.notifications import (
    dispatch_for_event,
    dispatch_notifications,
    format_message,
    send_discord,
    send_telegram,
    send_webhook,
)
from pricerecon.models import EventType


@pytest.mark.asyncio
async def test_send_webhook_success():
    """Test successful webhook send."""
    with respx.mock:
        route = respx.post("https://example.com/webhook").mock(
            return_value=Response(200, json={"status": "ok"})
        )

        result = await send_webhook("https://example.com/webhook", {"test": "data"})

        assert result is True
        assert route.call_count == 1


@pytest.mark.asyncio
async def test_send_webhook_failure():
    """Test webhook send failure."""
    with respx.mock:
        respx.post("https://example.com/webhook").mock(return_value=Response(500))

        result = await send_webhook("https://example.com/webhook", {"test": "data"})

        assert result is False


@pytest.mark.asyncio
async def test_send_telegram_success():
    """Test successful Telegram send."""
    with respx.mock:
        route = respx.post("https://api.telegram.org/bot123:ABC/sendMessage").mock(
            return_value=Response(200, json={"ok": True})
        )

        result = await send_telegram("123:ABC", "123456", "Test message")

        assert result is True
        assert route.call_count == 1
        assert json.loads(route.calls[0].request.content) == {
            "chat_id": "123456",
            "text": "Test message",
            "parse_mode": "HTML",
        }


@pytest.mark.asyncio
async def test_send_telegram_respects_rate_limit_and_retries_429(monkeypatch):
    """Telegram sends should pace and retry once on 429."""
    notifications_module._TELEGRAM_LAST_SEND_AT = 99.8
    current_time = {"value": 100.0}
    sleep_calls: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)
        current_time["value"] += seconds

    class FakeResponse:
        def __init__(self, status_code: int, headers: dict[str, str] | None = None):
            self.status_code = status_code
            self.headers = headers or {}

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                request = httpx.Request(
                    "POST",
                    "https://api.telegram.org/bot123:ABC/sendMessage",
                )
                raise httpx.HTTPStatusError(
                    "rate limited",
                    request=request,
                    response=httpx.Response(
                        self.status_code, headers=self.headers, request=request
                    ),
                )

    responses = [
        FakeResponse(429, {"Retry-After": "2"}),
        FakeResponse(200),
    ]

    async def fake_send_once(bot_token: str, chat_id: str, message: str):
        response = responses.pop(0)
        response.raise_for_status()
        return response

    monkeypatch.setattr(notifications_module.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(notifications_module, "_send_telegram_once", fake_send_once)
    monkeypatch.setattr(notifications_module.time, "monotonic", lambda: current_time["value"])

    result = await send_telegram("123:ABC", "123456", "Test message")

    assert result is True
    assert sleep_calls[0] == pytest.approx(0.3)
    assert sleep_calls[1] == pytest.approx(2.0)
    assert notifications_module._TELEGRAM_LAST_SEND_AT == pytest.approx(102.3)


@pytest.mark.asyncio
async def test_send_discord_success():
    """Test successful Discord send."""
    with respx.mock:
        route = respx.post("https://discord.com/api/webhooks/123/test").mock(
            return_value=Response(204)
        )

        result = await send_discord("https://discord.com/api/webhooks/123/test", "Test message")

        assert result is True
        assert route.call_count == 1
        assert json.loads(route.calls[0].request.content) == {
            "content": "Test message",
        }


@pytest.mark.asyncio
async def test_send_discord_failure():
    """Test Discord send failure."""
    with respx.mock:
        respx.post("https://discord.com/api/webhooks/123/test").mock(return_value=Response(400))

        result = await send_discord("https://discord.com/api/webhooks/123/test", "Test message")

        assert result is False


def test_format_message_new_listing():
    """Test message formatting for new listing event."""
    listing = {
        "title_raw": "NVIDIA GeForce RTX 3090",
        "price": "650.00",
        "currency": "GBP",
        "source": "ebay",
        "url": "https://example.com/item/123",
    }

    message = format_message(EventType.NEW_LISTING, "RTX Watch", listing)

    assert "🆕" in message
    assert "GBP650.00" in message
    assert "NVIDIA GeForce RTX 3090" in message
    assert "ebay" in message
    assert "https://example.com/item/123" in message


def test_format_message_price_drop():
    """Test message formatting for price drop event."""
    listing = {
        "title_raw": "NVIDIA GeForce RTX 3090",
        "price": "635.00",
        "currency": "GBP",
        "source": "ebay",
        "url": "https://example.com/item/123",
        "previous_price": "665.00",
    }

    message = format_message(EventType.PRICE_DROP, "RTX Watch", listing)

    assert "🔻" in message
    assert "GBP635.00" in message
    assert "was GBP665.00" in message
    assert "NVIDIA GeForce RTX 3090" in message


def test_format_message_stock_change_in_stock():
    """Test message formatting for stock change (back in stock)."""
    listing = {
        "title_raw": "NVIDIA GeForce RTX 3090",
        "price": "650.00",
        "currency": "GBP",
        "source": "ebay",
        "url": "https://example.com/item/123",
        "in_stock": True,
    }

    message = format_message(EventType.STOCK_CHANGE, "RTX Watch", listing)

    assert "📦" in message
    assert "Back in stock" in message
    assert "GBP650.00" in message


def test_format_message_stock_change_out_of_stock():
    """Test message formatting for stock change (out of stock)."""
    listing = {
        "title_raw": "NVIDIA GeForce RTX 3090",
        "price": "650.00",
        "currency": "GBP",
        "source": "ebay",
        "url": "https://example.com/item/123",
        "in_stock": False,
    }

    message = format_message(EventType.STOCK_CHANGE, "RTX Watch", listing)

    assert "📦" in message
    assert "Out of stock" in message


def test_format_message_listing_gone():
    """Test message formatting for listing gone event."""
    listing = {
        "title_raw": "NVIDIA GeForce RTX 3090",
        "url": "https://example.com/item/123",
    }

    message = format_message(EventType.LISTING_GONE, "RTX Watch", listing)

    assert "❌" in message
    assert "Listing removed" in message
    assert "NVIDIA GeForce RTX 3090" in message


@pytest.mark.asyncio
@patch("pricerecon.core.notifications._log_notification")
async def test_dispatch_notifications_webhook(mock_log):
    """Test dispatching webhook notifications."""
    with respx.mock:
        route = respx.post("https://example.com/webhook").mock(return_value=Response(200))

        watch_notifications = {
            "events": ["new_listing"],
            "channels": ["webhook"],
            "webhook_url": "https://example.com/webhook",
        }
        global_config = {}

        result = await dispatch_notifications(
            watch_id=1,
            event_id=100,
            event_type=EventType.NEW_LISTING,
            watch_name="Test Watch",
            watch_notifications=watch_notifications,
            listing={
                "title_raw": "Test Product",
                "price": "100.00",
                "currency": "GBP",
                "source": "test",
                "url": "https://example.com/item",
            },
            global_config=global_config,
        )

        assert result == ["webhook"]
        assert route.call_count == 1
        mock_log.assert_called_once()
        assert mock_log.call_args[1]["event_id"] == 100
        assert mock_log.call_args[1]["channel"] == "webhook"
        assert mock_log.call_args[1]["status"] == "sent"


@pytest.mark.asyncio
@patch("pricerecon.core.notifications._log_notification")
async def test_dispatch_notifications_telegram(mock_log):
    """Test dispatching Telegram notifications."""
    with respx.mock:
        route = respx.post("https://api.telegram.org/bot123:ABC/sendMessage").mock(
            return_value=Response(200, json={"ok": True})
        )

        watch_notifications = {
            "events": ["new_listing"],
            "channels": ["telegram"],
        }
        global_config = {
            "telegram_bot_token": "123:ABC",
            "telegram_chat_id": "7957100664",
        }

        result = await dispatch_notifications(
            watch_id=1,
            event_id=100,
            event_type=EventType.NEW_LISTING,
            watch_name="Test Watch",
            watch_notifications=watch_notifications,
            listing={
                "title_raw": "Test Product",
                "price": "100.00",
                "currency": "GBP",
                "source": "test",
                "url": "https://example.com/item",
            },
            global_config=global_config,
        )

        assert result == ["telegram"]
        assert route.call_count == 1


@pytest.mark.asyncio
@patch("pricerecon.core.notifications._log_notification")
async def test_dispatch_notifications_discord(mock_log):
    """Test dispatching Discord notifications."""
    with respx.mock:
        route = respx.post("https://discord.com/api/webhooks/123/test").mock(
            return_value=Response(204)
        )

        watch_notifications = {
            "events": ["new_listing"],
            "channels": ["discord"],
        }
        global_config = {
            "discord_webhook_url": "https://discord.com/api/webhooks/123/test",
        }

        result = await dispatch_notifications(
            watch_id=1,
            event_id=100,
            event_type=EventType.NEW_LISTING,
            watch_name="Test Watch",
            watch_notifications=watch_notifications,
            listing={
                "title_raw": "Test Product",
                "price": "100.00",
                "currency": "GBP",
                "source": "test",
                "url": "https://example.com/item",
            },
            global_config=global_config,
        )

        assert result == ["discord"]
        assert route.call_count == 1


@pytest.mark.asyncio
@patch("pricerecon.core.notifications._log_notification")
async def test_dispatch_notifications_missing_config(mock_log):
    """Test dispatching notifications with missing channel config."""
    watch_notifications = {
        "events": ["new_listing"],
        "channels": ["telegram"],
    }
    global_config = {}  # No telegram config

    result = await dispatch_notifications(
        watch_id=1,
        event_id=100,
        event_type=EventType.NEW_LISTING,
        watch_name="Test Watch",
        watch_notifications=watch_notifications,
        listing={
            "title_raw": "Test Product",
            "price": "100.00",
            "currency": "GBP",
            "source": "test",
            "url": "https://example.com/item",
        },
        global_config=global_config,
    )

    assert result == ["telegram"]
    mock_log.assert_called_once()
    assert mock_log.call_args[1]["status"] == "failed"
    assert "not configured" in mock_log.call_args[1]["error_message"]


@pytest.mark.asyncio
async def test_dispatch_notifications_event_not_enabled():
    """Test that notifications are not sent for disabled event types."""
    watch_notifications = {
        "events": ["price_drop"],  # Only price_drop enabled
        "channels": ["telegram"],
    }
    global_config = {}

    result = await dispatch_notifications(
        watch_id=1,
        event_id=100,
        event_type=EventType.NEW_LISTING,  # Not enabled
        watch_name="Test Watch",
        watch_notifications=watch_notifications,
        listing={
            "title_raw": "Test Product",
            "price": "100.00",
            "currency": "GBP",
            "source": "test",
            "url": "https://example.com/item",
        },
        global_config=global_config,
    )

    assert result == []  # No notifications sent


@pytest.mark.asyncio
@patch("pricerecon.core.notifications.get_global_notification_config")
@patch("pricerecon.core.notifications.dispatch_notifications")
async def test_dispatch_for_event(mock_dispatch, mock_get_config):
    """Test dispatch_for_event convenience function."""
    mock_get_config.return_value = {"defaults": []}
    mock_dispatch.return_value = ["telegram"]

    result = await dispatch_for_event(
        watch_id=1,
        event_id=100,
        event_type=EventType.NEW_LISTING,
        watch_name="Test Watch",
        watch_notifications={"events": ["new_listing"], "channels": ["telegram"]},
        listing={
            "title_raw": "Test",
            "price": "100",
            "currency": "GBP",
            "source": "test",
            "url": "https://test.com",
        },
    )

    assert result == ["telegram"]
    mock_dispatch.assert_called_once()
    call_kwargs = mock_dispatch.call_args[1]
    assert call_kwargs["watch_id"] == 1
    assert call_kwargs["event_id"] == 100
    assert call_kwargs["event_type"] == EventType.NEW_LISTING
    assert call_kwargs["watch_name"] == "Test Watch"


@pytest.mark.asyncio
@patch("pricerecon.core.notifications._log_notification")
async def test_dispatch_notifications_per_watch_override(mock_log):
    """Test per-watch override for specific event."""
    with respx.mock:
        route = respx.post("https://discord.com/api/webhooks/123/test").mock(
            return_value=Response(204)
        )

        watch_notifications = {
            "events": ["price_drop", "stock_change"],
            "channels": ["telegram"],  # Default channels
            "overrides": [
                {
                    "event": "stock_change",
                    "channels": ["discord"],  # Override for stock_change
                }
            ],
        }
        global_config = {
            "telegram_bot_token": "123:ABC",
            "telegram_chat_id": "7957100664",
            "discord_webhook_url": "https://discord.com/api/webhooks/123/test",
        }

        result = await dispatch_notifications(
            watch_id=1,
            event_id=100,
            event_type=EventType.STOCK_CHANGE,
            watch_name="Test Watch",
            watch_notifications=watch_notifications,
            listing={
                "title_raw": "Test Product",
                "price": "100.00",
                "currency": "GBP",
                "source": "test",
                "url": "https://example.com/item",
                "in_stock": True,
            },
            global_config=global_config,
        )

        assert result == ["discord"]  # Override applied
        assert route.call_count == 1  # Only Discord called, not Telegram


@pytest.mark.asyncio
@patch("pricerecon.core.notifications._log_notification")
async def test_dispatch_notifications_global_defaults(mock_log):
    """Test global defaults when watch has no channel config."""
    with respx.mock:
        route = respx.post("https://discord.com/api/webhooks/123/test").mock(
            return_value=Response(204)
        )

        watch_notifications = {
            "events": ["new_listing"],
            "channels": [],  # No channels configured
        }
        global_config = {
            "defaults": [
                {
                    "event": "new_listing",
                    "channels": ["discord"],
                }
            ],
            "discord_webhook_url": "https://discord.com/api/webhooks/123/test",
        }

        result = await dispatch_notifications(
            watch_id=1,
            event_id=100,
            event_type=EventType.NEW_LISTING,
            watch_name="Test Watch",
            watch_notifications=watch_notifications,
            listing={
                "title_raw": "Test Product",
                "price": "100.00",
                "currency": "GBP",
                "source": "test",
                "url": "https://example.com/item",
            },
            global_config=global_config,
        )

        assert result == ["discord"]
        assert route.call_count == 1
