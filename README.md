# OpenClaw Weixin Python SDK

用于连接 OpenClaw 与微信应用的易用 Python SDK。

> **官方仓库:** https://github.com/yzailab/openclaw-weixin-python

## 功能特性

- **Async/Await**: 基于 asyncio 和 aiohttp 构建，高性能
- **类型提示**: 完整的类型注解支持
- **长轮询**: 通过长轮询高效接收消息
- **媒体支持**: 发送/接收文本、图片、语音、视频和文件
- **上下文 Token**: 自动会话管理
- **弹性模式**: 指数退避重试和熔断器模式
- **速率限制**: Token 桶和滑动窗口限流器
- **CLI 工具**: 账号管理的命令行界面

## 安装

### 从源码安装

```bash
git clone https://github.com/yzailab/openclaw-weixin-python.git
cd openclaw-weixin-python
pip install -e ".[dev]"
```

### 可选依赖

用于语音消息转码:

```bash
# 纯 Python (推荐)
pip install pysilk
```

## 快速开始

### 基本用法

```python
import asyncio
from weixin_sdk import WeixinClient, DEFAULT_BASE_URL

async def main():
    # 创建客户端
    async with WeixinClient(
        base_url=DEFAULT_BASE_URL,  # 官方 API: https://ilinkai.weixin.qq.com
        token="your-auth-token",
    ) as client:
        # 接收消息
        async for message in client.poll_messages():
            print(f"来自: {message.from_user_id}")

            # 获取文本内容
            for item in message.item_list:
                if item.text_item:
                    print(f"文本: {item.text_item.text}")

                    # 回显消息
                    await client.send_text(
                        to_user_id=message.from_user_id,
                        text=f"Echo: {item.text_item.text}",
                        context_token=message.context_token,
                    )

if __name__ == "__main__":
    asyncio.run(main())
```

### 发送媒体

```python
from weixin_sdk import WeixinClient

async def send_media_example(client: WeixinClient, user_id: str):
    # 发送图片 (支持本地文件路径)
    await client.send_image(
        to_user_id=user_id,
        image_path="/path/to/image.jpg",
        caption="图片说明",
    )
    
    # 发送视频
    await client.send_video(
        to_user_id=user_id,
        video_path="/path/to/video.mp4",
        caption="视频说明",
    )
    
    # 发送文件
    await client.send_file(
        to_user_id=user_id,
        file_path="/path/to/document.pdf",
    )
    
    # 发送语音
    await client.send_voice(
        to_user_id=user_id,
        voice_path="/path/to/audio.mp3",
    )
```

## CLI 使用

```bash
# 列出所有账号
weixin list

# 添加新账号
weixin add bot1 --token abc123 --name "My Bot"

# 显示账号详情
weixin show bot1

# 更新账号
weixin update bot1 --name "New Name" --token new-token

# 启用/禁用账号
weixin enable bot1
weixin disable bot1

# 移除账号
weixin remove bot1

# 测试账号配置
weixin test bot1
```

### 环境变量

| 变量 | 描述 |
|----------|-------------|
| `WEIXIN_SDK_STATE_DIR` | 覆盖默认状态目录 (默认: `~/.weixin_sdk`) |
| `WEIXIN_LOG_UPLOAD_URL` | 日志上传端点 URL |

## 相关项目

- **微信官方 TypeScript/JS SDK**: [@tencent-weixin/openclaw-weixin-cli](https://www.npmjs.com/package/@tencent-weixin/openclaw-weixin-cli)
  ```bash
  npx -y @tencent-weixin/openclaw-weixin-cli@latest install
  ```

## 许可证

MIT 许可证 - 详情请参见 LICENSE 文件。
