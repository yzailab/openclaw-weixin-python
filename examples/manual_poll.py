#!/usr/bin/env python3
"""
Manual Polling Example

Shows how to manually handle long-polling with cursor management.
"""

import asyncio
import json
import logging
from weixin_sdk import (
    WeixinClient,
    WeixinTimeoutError,
    WeixinSessionExpiredError,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def manual_poll_example():
    """Example of manual polling with cursor persistence."""

    client = WeixinClient(
        base_url="https://your-weixin-api.example.com",
        token="your-auth-token",
    )

    # Try to load previous cursor
    cursor_file = ".weixin_cursor.json"
    cursor = ""
    try:
        with open(cursor_file, "r") as f:
            data = json.load(f)
            cursor = data.get("cursor", "")
            logger.info(f"Loaded cursor: {cursor[:20]}...")
    except FileNotFoundError:
        logger.info("No cursor file, starting fresh")

    try:
        while True:
            try:
                # Single long-poll request
                logger.info("Polling for messages...")
                resp = await client.get_updates(cursor)

                # Process messages
                if resp.msgs:
                    logger.info(f"Received {len(resp.msgs)} messages")
                    for msg in resp.msgs:
                        logger.info(f"Message: {msg}")
                else:
                    logger.info("No new messages (timeout)")

                # Save cursor for next request
                cursor = resp.get_updates_buf or ""
                with open(cursor_file, "w") as f:
                    json.dump({"cursor": cursor}, f)

                # Update timeout if server suggests
                if resp.longpolling_timeout_ms:
                    client.long_poll_timeout_ms = resp.longpolling_timeout_ms

            except WeixinTimeoutError:
                # Normal for long-polling
                logger.debug("Long-poll timeout, retrying...")
                continue

            except WeixinSessionExpiredError:
                logger.error("Session expired! Please re-login.")
                break

    except KeyboardInterrupt:
        logger.info("Stopped by user")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(manual_poll_example())
