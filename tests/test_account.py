"""
Tests for account management and state persistence.
"""

import pytest
import json
from pathlib import Path

from weixin_sdk.account import (
    WeixinAccount,
    WeixinAccountManager,
    get_default_account_manager,
)
from weixin_sdk.exceptions import WeixinError


class TestWeixinAccount:
    """Test WeixinAccount dataclass."""

    def test_account_creation(self):
        """Test creating a WeixinAccount."""
        account = WeixinAccount(
            account_id="test123",
            name="Test Bot",
            token="secret-token",
            configured=True,
        )

        assert account.account_id == "test123"
        assert account.name == "Test Bot"
        assert account.token == "secret-token"
        assert account.configured is True
        assert account.enabled is True
        assert account.base_url == "https://ilinkai.weixin.qq.com"

    def test_account_defaults(self):
        """Test WeixinAccount default values."""
        account = WeixinAccount(account_id="test")

        assert account.name is None
        assert account.enabled is True
        assert account.configured is False
        assert account.token is None

    def test_account_to_dict(self):
        """Test converting account to dictionary."""
        account = WeixinAccount(
            account_id="test",
            name="Test",
            token="token123",
        )

        data = account.to_dict()

        assert data["account_id"] == "test"
        assert data["name"] == "Test"
        assert data["token"] == "token123"

    def test_account_from_dict(self):
        """Test creating account from dictionary."""
        data = {
            "account_id": "test",
            "name": "Test",
            "token": "token123",
            "enabled": False,
            "configured": True,
        }

        account = WeixinAccount.from_dict(data)

        assert account.account_id == "test"
        assert account.name == "Test"
        assert account.enabled is False
        assert account.configured is True


class TestWeixinAccountManager:
    """Test WeixinAccountManager functionality."""

    def test_initialization(self, temp_dir):
        """Test manager initialization."""
        manager = WeixinAccountManager(state_dir=temp_dir)

        assert manager.state_dir == temp_dir
        assert manager.list_accounts() == []
        assert temp_dir.exists()

    def test_register_account(self, temp_dir):
        """Test registering an account."""
        manager = WeixinAccountManager(state_dir=temp_dir)

        manager.register_account("bot1")

        assert "bot1" in manager.list_accounts()
        account = manager.get_account("bot1")
        assert account is not None
        assert account.account_id == "bot1"

    def test_register_with_account_object(self, temp_dir):
        """Test registering with custom account object."""
        manager = WeixinAccountManager(state_dir=temp_dir)

        account = WeixinAccount(
            account_id="bot1",
            name="My Bot",
            token="secret123",
            configured=True,
        )

        manager.register_account("bot1", account)

        retrieved = manager.get_account("bot1")
        assert retrieved.name == "My Bot"
        assert retrieved.token == "secret123"
        assert retrieved.configured is True

    def test_unregister_account(self, temp_dir):
        """Test unregistering an account."""
        manager = WeixinAccountManager(state_dir=temp_dir)
        manager.register_account("bot1")

        manager.unregister_account("bot1")

        assert "bot1" not in manager.list_accounts()
        assert manager.get_account("bot1") is None

    def test_update_account(self, temp_dir):
        """Test updating account configuration."""
        manager = WeixinAccountManager(state_dir=temp_dir)
        manager.register_account("bot1")

        manager.update_account("bot1", name="Updated Bot", token="new_token")

        account = manager.get_account("bot1")
        assert account.name == "Updated Bot"
        assert account.token == "new_token"

    def test_update_nonexistent_account(self, temp_dir):
        """Test updating non-existent account raises error."""
        manager = WeixinAccountManager(state_dir=temp_dir)

        with pytest.raises(WeixinError) as exc_info:
            manager.update_account("nonexistent", name="Test")

        assert "Account not found" in str(exc_info.value)

    def test_resolve_account(self, temp_dir):
        """Test resolving account."""
        manager = WeixinAccountManager(state_dir=temp_dir)

        account = WeixinAccount(
            account_id="bot1",
            token="token",
            configured=True,
            enabled=True,
        )
        manager.register_account("bot1", account)

        # Resolve by ID
        resolved = manager.resolve_account("bot1")
        assert resolved.account_id == "bot1"

        # Resolve first configured
        resolved = manager.resolve_account()
        assert resolved.account_id == "bot1"

    def test_resolve_no_accounts(self, temp_dir):
        """Test resolving with no accounts raises error."""
        manager = WeixinAccountManager(state_dir=temp_dir)

        with pytest.raises(WeixinError) as exc_info:
            manager.resolve_account()

        assert "No accounts registered" in str(exc_info.value)


class TestContextTokenManagement:
    """Test context token persistence."""

    def test_set_and_get_context_token(self, temp_dir):
        """Test setting and getting context tokens."""
        manager = WeixinAccountManager(state_dir=temp_dir)

        manager.set_context_token("bot1", "user@im.wechat", "token_abc")

        token = manager.get_context_token("bot1", "user@im.wechat")
        assert token == "token_abc"

    def test_context_token_persistence(self, temp_dir):
        """Test that tokens are persisted to disk."""
        # Create manager and set token
        manager1 = WeixinAccountManager(state_dir=temp_dir)
        manager1.set_context_token("bot1", "user@im.wechat", "persisted_token")

        # Create new manager instance (simulates restart)
        manager2 = WeixinAccountManager(state_dir=temp_dir)

        token = manager2.get_context_token("bot1", "user@im.wechat")
        assert token == "persisted_token"

    def test_find_accounts_by_context_token(self, temp_dir):
        """Test finding accounts by context token."""
        manager = WeixinAccountManager(state_dir=temp_dir)

        manager.set_context_token("bot1", "user@im.wechat", "token1")
        manager.set_context_token("bot2", "user@im.wechat", "token2")
        manager.set_context_token("bot1", "other@im.wechat", "token3")

        accounts = manager.find_accounts_by_context_token("user@im.wechat")

        assert len(accounts) == 2
        assert "bot1" in accounts
        assert "bot2" in accounts

    def test_clear_context_tokens(self, temp_dir):
        """Test clearing context tokens for an account."""
        manager = WeixinAccountManager(state_dir=temp_dir)

        manager.set_context_token("bot1", "user1@im.wechat", "token1")
        manager.set_context_token("bot1", "user2@im.wechat", "token2")
        manager.set_context_token("bot2", "user1@im.wechat", "token3")

        manager.clear_context_tokens("bot1")

        assert manager.get_context_token("bot1", "user1@im.wechat") is None
        assert manager.get_context_token("bot1", "user2@im.wechat") is None
        assert manager.get_context_token("bot2", "user1@im.wechat") == "token3"


class TestPersistence:
    """Test data persistence to disk."""

    def test_accounts_persisted(self, temp_dir):
        """Test that accounts are saved to disk."""
        manager = WeixinAccountManager(state_dir=temp_dir)
        manager.register_account(
            "bot1",
            WeixinAccount(
                account_id="bot1",
                name="Test Bot",
                token="secret",
                configured=True,
            ),
        )

        accounts_file = temp_dir / "accounts.json"
        assert accounts_file.exists()

        data = json.loads(accounts_file.read_text())
        assert "bot1" in data
        assert data["bot1"]["name"] == "Test Bot"

    def test_load_existing_accounts(self, temp_dir):
        """Test loading accounts from existing file."""
        # Create accounts file manually
        accounts_data = {
            "bot1": {
                "account_id": "bot1",
                "name": "Loaded Bot",
                "token": "loaded_token",
                "enabled": True,
                "configured": True,
                "base_url": "https://custom.example.com",
            }
        }
        accounts_file = temp_dir / "accounts.json"
        accounts_file.write_text(json.dumps(accounts_data))

        manager = WeixinAccountManager(state_dir=temp_dir)

        assert "bot1" in manager.list_accounts()
        account = manager.get_account("bot1")
        assert account.name == "Loaded Bot"
        assert account.base_url == "https://custom.example.com"

    def test_context_tokens_persisted(self, temp_dir):
        """Test that context tokens are saved to disk."""
        manager = WeixinAccountManager(state_dir=temp_dir)
        manager.set_context_token("bot1", "user@im.wechat", "secret_token")

        tokens_file = temp_dir / "accounts" / "bot1.tokens.json"
        assert tokens_file.exists()

        data = json.loads(tokens_file.read_text())
        assert data["user@im.wechat"] == "secret_token"


class TestGetDefaultManager:
    """Test get_default_account_manager function."""

    def test_returns_manager(self):
        """Test that function returns a manager instance."""
        manager = get_default_account_manager()

        assert isinstance(manager, WeixinAccountManager)
