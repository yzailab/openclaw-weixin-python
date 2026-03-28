"""
Tests for WeixinClient
"""

import pytest
import aiohttp
from unittest.mock import patch, AsyncMock, MagicMock

from weixin_sdk import (
    WeixinClient,
    WeixinMessage,
    SendMessageReq,
    GetUpdatesReq,
    MessageItem,
    MessageItemType,
    TextItem,
    MessageType,
    MessageState,
)
from weixin_sdk.exceptions import (
    WeixinAPIError,
    WeixinAuthError,
    WeixinTimeoutError,
    WeixinSessionExpiredError,
)


@pytest.fixture
async def client():
    """Create a test client."""
    client = WeixinClient(
        base_url="https://test.example.com",
        token="test-token",
    )
    yield client
    await client.close()


class TestWeixinClient:
    """Test WeixinClient functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test client initialization."""
        client = WeixinClient(
            base_url="https://api.example.com",
            token="my-token",
            timeout_ms=20000,
            long_poll_timeout_ms=40000,
        )

        assert client.base_url == "https://api.example.com/"
        assert client.token == "my-token"
        assert client.timeout_ms == 20000
        assert client.long_poll_timeout_ms == 40000

        await client.close()

    @pytest.mark.asyncio
    async def test_get_updates_success(self, client):
        """Test successful get_updates call."""
        mock_response = {
            "ret": 0,
            "msgs": [
                {
                    "message_id": 123,
                    "from_user_id": "user_001",
                    "to_user_id": "bot_001",
                    "item_list": [
                        {
                            "type": 1,
                            "text_item": {"text": "Hello!"},
                        }
                    ],
                    "context_token": "ctx_abc123",
                }
            ],
            "get_updates_buf": "next_cursor_xyz",
            "longpolling_timeout_ms": 35000,
        }

        with patch.object(client, "_api_fetch", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = json.dumps(mock_response)

            resp = await client.get_updates("")

            assert resp.ret == 0
            assert len(resp.msgs) == 1
            assert resp.msgs[0].from_user_id == "user_001"
            assert resp.get_updates_buf == "next_cursor_xyz"

    @pytest.mark.asyncio
    async def test_get_updates_session_expired(self, client):
        """Test session expired error handling."""
        mock_response = {
            "ret": -1,
            "errcode": -14,
            "errmsg": "Session expired",
        }

        with patch.object(client, "_api_fetch", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = json.dumps(mock_response)

            with pytest.raises(WeixinSessionExpiredError):
                await client.get_updates("")

    @pytest.mark.asyncio
    async def test_send_text(self, client):
        """Test sending text message."""
        with patch.object(client, "send_message", new_callable=AsyncMock) as mock_send:
            client_id = await client.send_text(
                to_user_id="user_123",
                text="Hello, World!",
                context_token="ctx_abc",
            )

            # Verify send_message was called
            assert mock_send.called

            # Verify the request structure
            call_args = mock_send.call_args[0][0]
            assert call_args.msg.to_user_id == "user_123"
            assert call_args.msg.context_token == "ctx_abc"
            assert len(call_args.msg.item_list) == 1
            assert call_args.msg.item_list[0].text_item.text == "Hello, World!"

    @pytest.mark.asyncio
    async def test_context_token_management(self, client):
        """Test context token store."""
        # Set token
        client.set_context_token("account_1", "user_1", "token_abc")

        # Get token
        token = client.get_context_token("account_1", "user_1")
        assert token == "token_abc"

        # Get non-existent token
        token = client.get_context_token("account_1", "user_2")
        assert token is None

        # Clear tokens for account
        client.set_context_token("account_1", "user_2", "token_def")
        client.clear_context_tokens("account_1")

        assert client.get_context_token("account_1", "user_1") is None
        assert client.get_context_token("account_1", "user_2") is None

    @pytest.mark.asyncio
    async def test_poll_messages(self, client):
        """Test message polling generator."""
        responses = [
            {
                "ret": 0,
                "msgs": [{"message_id": 1, "from_user_id": "user_1"}],
                "get_updates_buf": "cursor_1",
            },
            {
                "ret": 0,
                "msgs": [{"message_id": 2, "from_user_id": "user_2"}],
                "get_updates_buf": "cursor_2",
            },
        ]

        call_count = 0

        async def mock_get_updates(cursor):
            nonlocal call_count
            if call_count < len(responses):
                data = responses[call_count]
                call_count += 1
                from weixin_sdk.types import GetUpdatesResp, WeixinMessage

                return GetUpdatesResp(
                    ret=data["ret"],
                    msgs=[WeixinMessage(**m) for m in data["msgs"]],
                    get_updates_buf=data["get_updates_buf"],
                )
            else:
                # Stop after 2 calls
                raise asyncio.CancelledError()

        with patch.object(client, "get_updates", side_effect=mock_get_updates):
            messages = []
            try:
                async for msg in client.poll_messages():
                    messages.append(msg)
            except asyncio.CancelledError:
                pass

            assert len(messages) == 2
            assert messages[0].message_id == 1
            assert messages[1].message_id == 2


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_auth_error(self, client):
        """Test 401 authentication error."""
        mock_response = MagicMock()
        mock_response.status = 401
        mock_response.text = AsyncMock(return_value="Unauthorized")

        with pytest.raises(WeixinAuthError):
            with patch("aiohttp.ClientSession.post") as mock_post:
                mock_post.return_value.__aenter__ = AsyncMock(
                    return_value=mock_response
                )
                await client.get_updates("")

    @pytest.mark.asyncio
    async def test_timeout_error(self, client):
        """Test timeout error."""
        with pytest.raises(WeixinTimeoutError):
            with patch(
                "aiohttp.ClientSession.post", side_effect=asyncio.TimeoutError()
            ):
                await client.get_updates("")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
