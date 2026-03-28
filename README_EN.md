# OpenClaw Weixin Python SDK

Easy-to-use Python SDK to connect OpenClaw with WeChat apps.

> **Official Repository:** https://github.com/yzailab/openclaw-weixin-python

## Features

- **Async/Await**: Built on asyncio and aiohttp for high performance
- **Type Hints**: Full type annotation support
- **Long Polling**: Efficient message receiving via long-polling
- **Media Support**: Send/receive text, images, voice, video, and files
- **Context Tokens**: Automatic session management
- **Resilience**: Retry with exponential backoff and circuit breaker patterns
- **Rate Limiting**: Token bucket and sliding window rate limiters
- **CLI Tool**: Command-line interface for account management

## Installation

### From PyPI

```bash
pip install openclaw-weixin-python
```

### From Source

```bash
git clone https://github.com/yzailab/openclaw-weixin-python.git
cd openclaw-weixin-python
pip install -e ".[dev]"
```

### Optional Dependencies

For voice message transcoding:

```bash
# Pure Python (recommended)
pip install pysilk-python
```

## Quick Start

### Basic Usage

```python
import asyncio
from weixin_sdk import WeixinClient, DEFAULT_BASE_URL

async def main():
    # Create client
    async with WeixinClient(
        base_url=DEFAULT_BASE_URL,  # Official API: https://ilinkai.weixin.qq.com
        token="your-auth-token",
    ) as client:
        # Receive messages
        async for message in client.poll_messages():
            print(f"From: {message.from_user_id}")

            # Get text content
            for item in message.item_list:
                if item.text_item:
                    print(f"Text: {item.text_item.text}")

                    # Echo back
                    await client.send_text(
                        to_user_id=message.from_user_id,
                        text=f"Echo: {item.text_item.text}",
                        context_token=message.context_token,
                    )

if __name__ == "__main__":
    asyncio.run(main())
```

### Send Media

```python
from weixin_sdk import WeixinClient

async def send_media_example(client: WeixinClient, user_id: str):
    # Send image (supports local file path)
    await client.send_image(
        to_user_id=user_id,
        image_path="/path/to/image.jpg",
        caption="Image caption",
    )
    
    # Send video
    await client.send_video(
        to_user_id=user_id,
        video_path="/path/to/video.mp4",
        caption="Video caption",
    )
    
    # Send file
    await client.send_file(
        to_user_id=user_id,
        file_path="/path/to/document.pdf",
    )
    
    # Send voice
    await client.send_voice(
        to_user_id=user_id,
        voice_path="/path/to/audio.mp3",
    )
```

## CLI Usage

```bash
# List all accounts
weixin list

# Add a new account
weixin add bot1 --token abc123 --name "My Bot"

# Show account details
weixin show bot1

# Update account
weixin update bot1 --name "New Name" --token new-token

# Enable/disable account
weixin enable bot1
weixin disable bot1

# Remove account
weixin remove bot1

# Test account configuration
weixin test bot1
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `WEIXIN_SDK_STATE_DIR` | Override default state directory (default: `~/.weixin_sdk`) |
| `WEIXIN_LOG_UPLOAD_URL` | Log upload endpoint URL |

## Related Projects

- **WeChat Official TypeScript/JS SDK**: [@tencent-weixin/openclaw-weixin-cli](https://www.npmjs.com/package/@tencent-weixin/openclaw-weixin-cli)
  ```bash
  npx -y @tencent-weixin/openclaw-weixin-cli@latest install
  ```

## License

MIT License - see LICENSE file for details.
