#!/usr/bin/env python3
"""
Media Bot Example

Demonstrates sending multimedia messages (images, videos, files, voice)
using the enhanced Weixin SDK.
"""

import asyncio
import logging
from pathlib import Path

from weixin_sdk import (
    WeixinClient,
    WeixinAccountManager,
    markdown_to_plain_text,
    DEFAULT_BASE_URL,
)

# Enable logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def media_bot():
    """Media bot demonstrating multimedia message sending."""
    
    # Configuration
    TOKEN = "your-auth-token-here"
    ACCOUNT_ID = "my_account"
    
    # Initialize account manager for state persistence
    account_manager = WeixinAccountManager()
    
    # Register account if not exists
    if ACCOUNT_ID not in account_manager.list_accounts():
        account_manager.register_account(
            account_id=ACCOUNT_ID,
            base_url=DEFAULT_BASE_URL,
            token=TOKEN,
            configured=True,
        )
        logger.info(f"Registered account: {ACCOUNT_ID}")
    
    # Get account
    account = account_manager.get_account(ACCOUNT_ID)
    
    async with WeixinClient(
        base_url=account.base_url,
        token=account.token,
    ) as client:
        logger.info("Media bot started, waiting for messages...")
        
        try:
            async for message in client.poll_messages():
                user_id = message.from_user_id
                logger.info(f"Received message from {user_id}")
                
                # Get context token from persistent storage
                context_token = account_manager.get_context_token(
                    ACCOUNT_ID, user_id
                ) or message.context_token
                
                # Store context token for future use
                if message.context_token:
                    account_manager.set_context_token(
                        ACCOUNT_ID, user_id, message.context_token
                    )
                
                # Process text commands
                for item in message.item_list:
                    if item.type == 1 and item.text_item:  # TEXT
                        text = item.text_item.text
                        logger.info(f"Text: {text}")
                        
                        # Command: /image
                        if text.startswith("/image"):
                            logger.info("Sending image...")
                            try:
                                await client.send_image(
                                    to_user_id=user_id,
                                    image_path="/path/to/sample.jpg",
                                    caption="Here's an image for you!",
                                    context_token=context_token,
                                )
                                logger.info("Image sent successfully")
                            except Exception as e:
                                logger.error(f"Failed to send image: {e}")
                                await client.send_text(
                                    to_user_id=user_id,
                                    text=f"Sorry, couldn't send image: {e}",
                                    context_token=context_token,
                                )
                        
                        # Command: /video
                        elif text.startswith("/video"):
                            logger.info("Sending video...")
                            try:
                                await client.send_video(
                                    to_user_id=user_id,
                                    video_path="/path/to/sample.mp4",
                                    caption="Check out this video!",
                                    context_token=context_token,
                                )
                                logger.info("Video sent successfully")
                            except Exception as e:
                                logger.error(f"Failed to send video: {e}")
                                await client.send_text(
                                    to_user_id=user_id,
                                    text=f"Sorry, couldn't send video: {e}",
                                    context_token=context_token,
                                )
                        
                        # Command: /file
                        elif text.startswith("/file"):
                            logger.info("Sending file...")
                            try:
                                await client.send_file(
                                    to_user_id=user_id,
                                    file_path="/path/to/document.pdf",
                                    caption="Here's the document you requested.",
                                    context_token=context_token,
                                )
                                logger.info("File sent successfully")
                            except Exception as e:
                                logger.error(f"Failed to send file: {e}")
                                await client.send_text(
                                    to_user_id=user_id,
                                    text=f"Sorry, couldn't send file: {e}",
                                    context_token=context_token,
                                )
                        
                        # Command: /voice
                        elif text.startswith("/voice"):
                            logger.info("Sending voice...")
                            try:
                                await client.send_voice(
                                    to_user_id=user_id,
                                    voice_path="/path/to/voice.silk",
                                    duration_ms=5000,
                                    context_token=context_token,
                                )
                                logger.info("Voice sent successfully")
                            except Exception as e:
                                logger.error(f"Failed to send voice: {e}")
                                await client.send_text(
                                    to_user_id=user_id,
                                    text=f"Sorry, couldn't send voice: {e}",
                                    context_token=context_token,
                                )
                        
                        # Command: /markdown
                        elif text.startswith("/markdown"):
                            markdown_text = """
# Hello!

This is **bold** and *italic* text.

Check out this [link](http://example.com).

```python
print("Hello World")
```

1. Item 1
2. Item 2
3. Item 3
                            """.strip()
                            
                            # Convert markdown to plain text
                            plain_text = markdown_to_plain_text(markdown_text)
                            
                            await client.send_text(
                                to_user_id=user_id,
                                text=plain_text,
                                context_token=context_token,
                            )
                            logger.info("Markdown converted and sent")
                        
                        # Command: /help
                        elif text.startswith("/help"):
                            help_text = """
Available commands:
/image - Send a sample image
/video - Send a sample video
/file - Send a sample file
/voice - Send a sample voice message
/markdown - Convert markdown to plain text
/help - Show this help message
                            """.strip()
                            
                            await client.send_text(
                                to_user_id=user_id,
                                text=help_text,
                                context_token=context_token,
                            )
                        
                        # Default: echo
                        else:
                            await client.send_text(
                                to_user_id=user_id,
                                text=f"Echo: {text}\n\nTry /help for available commands.",
                                context_token=context_token,
                            )
                
                # Handle incoming media
                elif item.type == 2:  # IMAGE
                    logger.info("Received image")
                    await client.send_text(
                        to_user_id=user_id,
                        text="Nice image! I can send images too. Try /image",
                        context_token=context_token,
                    )
                
                elif item.type == 3:  # VOICE
                    logger.info("Received voice")
                    await client.send_text(
                        to_user_id=user_id,
                        text="Got your voice message!",
                        context_token=context_token,
                    )
                
                elif item.type == 4:  # FILE
                    logger.info("Received file")
                    await client.send_text(
                        to_user_id=user_id,
                        text="Thanks for the file!",
                        context_token=context_token,
                    )
                
                elif item.type == 5:  # VIDEO
                    logger.info("Received video")
                    await client.send_text(
                        to_user_id=user_id,
                        text="Great video!",
                        context_token=context_token,
                    )
                        
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot error: {e}")
        finally:
            # Context tokens are automatically persisted by WeixinAccountManager
            logger.info("Context tokens saved to disk")


if __name__ == "__main__":
    asyncio.run(media_bot())
