#!/usr/bin/env python3
"""
Echo Bot Example

A simple Weixin bot that echoes back text messages.
"""

import asyncio
import logging
from weixin_sdk import WeixinClient, MessageItemType

# Enable logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def echo_bot():
    """Simple echo bot implementation."""

    # Configuration
    BASE_URL = "https://your-weixin-api.example.com"
    TOKEN = "your-auth-token-here"

    async with WeixinClient(
        base_url=BASE_URL,
        token=TOKEN,
    ) as client:
        logger.info("Echo bot started, waiting for messages...")

        try:
            async for message in client.poll_messages():
                logger.info(f"Received message from {message.from_user_id}")

                # Process each item in the message
                for item in message.item_list:
                    # Handle text messages
                    if item.type == MessageItemType.TEXT and item.text_item:
                        text = item.text_item.text
                        logger.info(f"Text: {text}")

                        # Echo back
                        reply = f"Echo: {text}"
                        await client.send_text(
                            to_user_id=message.from_user_id,
                            text=reply,
                            context_token=message.context_token,
                        )
                        logger.info(f"Sent: {reply}")

                    # Handle images
                    elif item.type == MessageItemType.IMAGE:
                        logger.info("Received image")
                        await client.send_text(
                            to_user_id=message.from_user_id,
                            text="Nice image!",
                            context_token=message.context_token,
                        )

                    # Handle voice
                    elif item.type == MessageItemType.VOICE:
                        logger.info("Received voice message")
                        await client.send_text(
                            to_user_id=message.from_user_id,
                            text="I received your voice message!",
                            context_token=message.context_token,
                        )

        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot error: {e}")


if __name__ == "__main__":
    asyncio.run(echo_bot())
