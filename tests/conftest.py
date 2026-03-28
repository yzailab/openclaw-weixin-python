"""
Pytest configuration and shared fixtures.
"""

import asyncio
import pytest
import tempfile
from pathlib import Path

from weixin_sdk import WeixinClient, WeixinAccountManager


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def temp_dir():
    """Provide a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
async def mock_client():
    """Create a mock WeixinClient for testing."""
    client = WeixinClient(
        base_url="https://test.example.com",
        token="test-token",
    )
    yield client
    await client.close()


@pytest.fixture
async def account_manager(temp_dir):
    """Create a WeixinAccountManager with temp directory."""
    manager = WeixinAccountManager(state_dir=temp_dir)
    yield manager


@pytest.fixture
def sample_account_config():
    """Provide sample account configuration."""
    return {
        "account_id": "test_account",
        "name": "Test Account",
        "token": "test-token-123",
        "base_url": "https://test.example.com",
        "configured": True,
        "enabled": True,
    }


@pytest.fixture
def sample_message():
    """Provide a sample WeixinMessage."""
    from weixin_sdk import (
        WeixinMessage,
        MessageItem,
        TextItem,
        MessageType,
        MessageState,
        MessageItemType,
    )

    return WeixinMessage(
        message_id=12345,
        from_user_id="user@im.wechat",
        to_user_id="bot@im.wechat",
        message_type=MessageType.USER,
        message_state=MessageState.FINISH,
        item_list=[
            MessageItem(
                type=MessageItemType.TEXT,
                text_item=TextItem(text="Hello, bot!"),
            )
        ],
        context_token="ctx_token_abc123",
    )
