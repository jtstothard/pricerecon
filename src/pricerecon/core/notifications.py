"""Notification dispatcher module.

Sends notifications via webhook, Telegram, and Discord channels.
Logs all sent notifications in the notifications table.
"""

import httpx
import sqlite3
from datetime import datetime
from typing import Any, Optional

from pricerecon.db.schema import DB_PATH
from pricerecon.models import EventType


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================================
# Channel implementations
# ============================================================================


async def send_webhook(url: str, payload: dict[str, Any]) -> bool:
    """Send JSON POST to webhook URL.

    Args:
        url: Webhook URL
        payload: JSON payload to send

    Returns:
        True if successful, False otherwise
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return True
    except Exception as e:
        print(f"Webhook send failed: {e}")
        return False


async def send_telegram(
    bot_token: str, chat_id: str, message: str
) -> bool:
    """Send message to Telegram chat.

    Args:
        bot_token: Telegram bot token
        chat_id: Telegram chat ID
        message: Message text

    Returns:
        True if successful, False otherwise
    """
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return True
    except Exception as e:
        print(f"Telegram send failed: {e}")
        return False


async def send_discord(webhook_url: str, message: str) -> bool:
    """Send message to Discord webhook.

    Args:
        webhook_url: Discord webhook URL
        message: Message text

    Returns:
        True if successful, False otherwise
    """
    try:
        payload = {
            "content": message,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
            return True
    except Exception as e:
        print(f"Discord send failed: {e}")
        return False


# ============================================================================
# Message formatting
# ============================================================================


def format_message(
    event_type: EventType,
    watch_name: str,
    listing: dict[str, Any],
) -> str:
    """Format a notification message for an event.

    Args:
        event_type: Type of event
        watch_name: Name of the watch
        listing: Listing data

    Returns:
        Formatted message string
    """
    emoji_by_event = {
        EventType.NEW_LISTING: "🆕",
        EventType.PRICE_DROP: "🔻",
        EventType.PRICE_INCREASE: "📈",
        EventType.STOCK_CHANGE: "📦",
        EventType.LISTING_GONE: "❌",
    }
    emoji = emoji_by_event.get(event_type, "📢")

    title = listing.get("title_raw", "Unknown product")
    price = listing.get("price", "N/A")
    currency = listing.get("currency", "GBP")
    source = listing.get("source", "Unknown")
    url = listing.get("url", "")

    if event_type == EventType.PRICE_DROP:
        previous_price = listing.get("previous_price")
        if previous_price:
            message = f"{emoji} {currency}{price} (was {currency}{previous_price}) · {title}\n"
        else:
            message = f"{emoji} {currency}{price} · {title}\n"
    elif event_type == EventType.STOCK_CHANGE:
        in_stock = listing.get("in_stock", True)
        status = "Back in stock" if in_stock else "Out of stock"
        message = f"{emoji} {status} · {title} ({currency}{price})\n"
    elif event_type == EventType.LISTING_GONE:
        message = f"{emoji} Listing removed · {title}\n"
    else:  # NEW_LISTING or default
        message = f"{emoji} {currency}{price} · {title}\n"

    message += f"   {source} · {url}"
    return message


# ============================================================================
# Main dispatcher
# ============================================================================


async def dispatch_notifications(
    watch_id: int,
    event_id: int,
    event_type: EventType,
    watch_name: str,
    watch_notifications: dict[str, Any],
    listing: dict[str, Any],
    global_config: dict[str, Any],
) -> list[str]:
    """Dispatch notifications for an event.

    Determines which channels to send to based on global defaults
    and per-watch overrides, formats the message, sends the notification,
    and logs the result in the notifications table.

    Args:
        watch_id: Watch ID
        event_id: Event ID
        event_type: Type of event
        watch_name: Name of the watch
        watch_notifications: Watch notification config
        listing: Listing data
        global_config: Global notification config

    Returns:
        List of channels that were attempted (success or failure)
    """
    from datetime import timezone

    # Determine channels to use
    # Per-watch overrides take precedence over global defaults
    watch_events = watch_notifications.get("events", [])
    watch_channels = watch_notifications.get("channels", [])
    overrides = watch_notifications.get("overrides", [])

    # Check if this event type is enabled for this watch
    event_type_str = event_type.value
    if event_type_str not in watch_events:
        return []

    # Check for per-event overrides
    channels_to_send = watch_channels
    for override in overrides:
        if override.get("event") == event_type_str:
            channels_to_send = override.get("channels", watch_channels)
            break

    # Apply global defaults if watch has no channel config
    if not channels_to_send:
        global_defaults = global_config.get("defaults", [])
        for default in global_defaults:
            if default.get("event") == event_type_str:
                channels_to_send = default.get("channels", [])
                break

    if not channels_to_send:
        return []

    # Format the message
    message = format_message(event_type, watch_name, listing)

    # Send to each channel
    attempted_channels = []
    for channel in channels_to_send:
        success = False
        error_message = None

        try:
            if channel == "webhook":
                webhook_url = watch_notifications.get("webhook_url") or global_config.get("webhook_url")
                if webhook_url:
                    payload = {
                        "watch_id": watch_id,
                        "event_type": event_type_str,
                        "watch_name": watch_name,
                        "listing": listing,
                        "message": message,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    success = await send_webhook(webhook_url, payload)
                else:
                    error_message = "No webhook URL configured"

            elif channel == "telegram":
                bot_token = watch_notifications.get("telegram_bot_token") or global_config.get("telegram_bot_token")
                chat_id = watch_notifications.get("telegram_chat_id") or global_config.get("telegram_chat_id")
                if bot_token and chat_id:
                    success = await send_telegram(bot_token, chat_id, message)
                else:
                    error_message = "Telegram bot token or chat ID not configured"

            elif channel == "discord":
                webhook_url = watch_notifications.get("discord_webhook_url") or global_config.get("discord_webhook_url")
                if webhook_url:
                    success = await send_discord(webhook_url, message)
                else:
                    error_message = "Discord webhook URL not configured"

            else:
                error_message = f"Unknown channel: {channel}"

        except Exception as e:
            error_message = str(e)

        # Log the notification attempt
        _log_notification(
            event_id=event_id,
            channel=channel,
            status="sent" if success else "failed",
            message=message,
            error_message=error_message,
        )

        attempted_channels.append(channel)

    return attempted_channels


def _log_notification(
    event_id: int,
    channel: str,
    status: str,
    message: Optional[str] = None,
    error_message: Optional[str] = None,
) -> None:
    """Log a notification to the notifications table.

    Args:
        event_id: Event ID
        channel: Channel name
        status: Status ('sent' or 'failed')
        message: Message text (optional)
        error_message: Error message if failed (optional)
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO notifications (event_id, channel, status, message, error_message)
           VALUES (?, ?, ?, ?, ?)""",
        (event_id, channel, status, message, error_message),
    )
    conn.commit()
    conn.close()


def get_global_notification_config() -> dict[str, Any]:
    """Get global notification configuration from config.yml.

    Returns:
        Global notification config dict
    """
    from pricerecon.config import load_config

    config = load_config()
    return config.get("notifications", {})


async def dispatch_for_event(
    watch_id: int,
    event_id: int,
    event_type: EventType,
    watch_name: str,
    watch_notifications: dict[str, Any],
    listing: dict[str, Any],
) -> list[str]:
    """Convenience function to dispatch notifications for an event.

    Loads global config and calls dispatch_notifications.

    Args:
        watch_id: Watch ID
        event_id: Event ID
        event_type: Type of event
        watch_name: Name of the watch
        watch_notifications: Watch notification config
        listing: Listing data

    Returns:
        List of channels that were attempted
    """
    global_config = get_global_notification_config()
    return await dispatch_notifications(
        watch_id=watch_id,
        event_id=event_id,
        event_type=event_type,
        watch_name=watch_name,
        watch_notifications=watch_notifications,
        listing=listing,
        global_config=global_config,
    )