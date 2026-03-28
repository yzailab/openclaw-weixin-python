"""
Tests for media upload and sending functionality.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from pathlib import Path

from weixin_sdk.media import (
    MediaUploader,
    MediaSender,
    send_image,
    send_video,
    send_file,
    send_voice,
)
from weixin_sdk.types import (
    MessageItemType,
    UploadMediaType,
    CDNMedia,
)
from weixin_sdk.exceptions import WeixinError, WeixinAPIError


class TestMediaUploader:
    """Test MediaUploader class."""

    @pytest.mark.asyncio
    async def test_upload_file_success(self, mock_client, temp_dir):
        """Test successful file upload."""
        # Create a test file
        test_file = temp_dir / "test.txt"
        test_file.write_text("Hello, World!")

        # Mock client methods
        mock_response = MagicMock()
        mock_response.upload_param = "https://cdn.example.com/upload/123"
        mock_client.get_upload_url = AsyncMock(return_value=mock_response)

        uploader = MediaUploader(mock_client)

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_session_class.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_response_obj = MagicMock()
            mock_response_obj.status = 200
            mock_session.post = MagicMock(
                return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_response_obj),
                    __aexit__=AsyncMock(return_value=False),
                )
            )

            result = await uploader.upload_file(
                str(test_file),
                "user@im.wechat",
                UploadMediaType.FILE,
            )

        assert "filekey" in result
        assert "aeskey" in result
        assert result["file_size"] == len("Hello, World!")

    @pytest.mark.asyncio
    async def test_upload_file_not_found(self, mock_client, temp_dir):
        """Test upload with non-existent file."""
        uploader = MediaUploader(mock_client)

        with pytest.raises(WeixinError) as exc_info:
            await uploader.upload_file(
                "/nonexistent/file.txt",
                "user@im.wechat",
            )

        assert "File not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_upload_image(self, mock_client, temp_dir):
        """Test image upload convenience method."""
        test_image = temp_dir / "test.jpg"
        test_image.write_bytes(b"fake_image_data")

        uploader = MediaUploader(mock_client)

        with patch.object(uploader, "upload_file") as mock_upload:
            mock_upload.return_value = {
                "filekey": "img_123",
                "aeskey": b"key123",
                "file_size": 100,
            }

            result = await uploader.upload_image(
                str(test_image),
                "user@im.wechat",
            )

        mock_upload.assert_called_once_with(
            str(test_image),
            "user@im.wechat",
            UploadMediaType.IMAGE,
        )
        assert result["filekey"] == "img_123"


class TestMediaSender:
    """Test MediaSender class."""

    @pytest.mark.asyncio
    async def test_send_image(self, mock_client, temp_dir):
        """Test sending image message."""
        test_image = temp_dir / "photo.jpg"
        test_image.write_bytes(b"fake_image")

        sender = MediaSender(mock_client)

        with patch.object(sender.uploader, "upload_image") as mock_upload:
            mock_upload.return_value = {
                "filekey": "img_123",
                "aeskey": b"aes_key_123",
                "file_size": 1000,
                "file_size_ciphertext": 1024,
                "download_param": "https://cdn.example.com/img/123",
            }

            mock_client.send_message = AsyncMock()

            result = await sender.send_image(
                to_user_id="user@im.wechat",
                image_path=str(test_image),
                caption="Check this out!",
            )

        assert result  # Should return message ID
        mock_upload.assert_called_once()
        mock_client.send_message.assert_called()

    @pytest.mark.asyncio
    async def test_send_video(self, mock_client, temp_dir):
        """Test sending video message."""
        test_video = temp_dir / "video.mp4"
        test_video.write_bytes(b"fake_video_data")

        sender = MediaSender(mock_client)

        with patch.object(sender.uploader, "upload_video") as mock_upload:
            mock_upload.return_value = {
                "filekey": "vid_123",
                "aeskey": b"aes_key_123",
                "file_size_ciphertext": 5000,
                "download_param": "https://cdn.example.com/vid/123",
            }

            mock_client.send_message = AsyncMock()

            result = await sender.send_video(
                to_user_id="user@im.wechat",
                video_path=str(test_video),
                caption="Cool video!",
            )

        assert result
        mock_upload.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_file(self, mock_client, temp_dir):
        """Test sending file message."""
        test_file = temp_dir / "document.pdf"
        test_file.write_bytes(b"fake_pdf_content")

        sender = MediaSender(mock_client)

        with patch.object(sender.uploader, "upload_file") as mock_upload:
            mock_upload.return_value = {
                "filekey": "file_123",
                "aeskey": b"aes_key_123",
                "file_size": 2000,
                "file_size_ciphertext": 2048,
                "download_param": "https://cdn.example.com/file/123",
            }

            mock_client.send_message = AsyncMock()

            result = await sender.send_file(
                to_user_id="user@im.wechat",
                file_path=str(test_file),
                caption="Here's the document",
            )

        assert result
        mock_upload.assert_called_once_with(
            str(test_file),
            "user@im.wechat",
            UploadMediaType.FILE,
        )

    @pytest.mark.asyncio
    async def test_send_voice(self, mock_client, temp_dir):
        """Test sending voice message."""
        test_voice = temp_dir / "voice.silk"
        test_voice.write_bytes(b"fake_silk_data")

        sender = MediaSender(mock_client)

        with patch.object(sender.uploader, "upload_file") as mock_upload:
            mock_upload.return_value = {
                "filekey": "voice_123",
                "aeskey": b"aes_key_123",
                "file_size": 500,
                "download_param": "https://cdn.example.com/voice/123",
            }

            mock_client.send_message = AsyncMock()

            result = await sender.send_voice(
                to_user_id="user@im.wechat",
                voice_path=str(test_voice),
                duration_ms=5000,
            )

        assert result
        mock_upload.assert_called_once_with(
            str(test_voice),
            "user@im.wechat",
            UploadMediaType.VOICE,
        )


class TestStandaloneFunctions:
    """Test standalone media sending functions."""

    @pytest.mark.asyncio
    async def test_send_image_standalone(self, mock_client, temp_dir):
        """Test standalone send_image function."""
        test_image = temp_dir / "test.jpg"
        test_image.write_bytes(b"image_data")

        with patch("weixin_sdk.media.MediaSender") as MockSender:
            mock_sender = MagicMock()
            mock_sender.send_image = AsyncMock(return_value="msg_123")
            MockSender.return_value = mock_sender

            result = await send_image(
                mock_client,
                "user@im.wechat",
                str(test_image),
                caption="Test",
            )

        assert result == "msg_123"
        mock_sender.send_image.assert_called_once_with(
            "user@im.wechat",
            str(test_image),
            "Test",
            None,
        )


class TestErrorHandling:
    """Test error handling in media operations."""

    @pytest.mark.asyncio
    async def test_upload_cdn_failure(self, mock_client, temp_dir):
        """Test handling of CDN upload failure."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("content")

        mock_response = MagicMock()
        mock_response.upload_param = "https://cdn.example.com/upload"
        mock_client.get_upload_url = AsyncMock(return_value=mock_response)

        uploader = MediaUploader(mock_client)

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_session_class.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_response_obj = MagicMock()
            mock_response_obj.status = 500
            mock_session.post = MagicMock(
                return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_response_obj),
                    __aexit__=AsyncMock(return_value=False),
                )
            )

            with pytest.raises(WeixinAPIError) as exc_info:
                await uploader.upload_file(
                    str(test_file),
                    "user@im.wechat",
                )

            assert exc_info.value.code == 500
