"""Test repository implementations"""

import pytest

from rotkehlchen.db.orm.models import (
    BlockchainAccount,
    DBSettings,
    ManualBalance,
    Tag,
)
from rotkehlchen.fval import FVal


class TestSettingsRepository:
    """Test settings repository"""
    
    def test_set_and_get_setting(self, test_repos):
        """Test setting and getting values"""
        # Set a setting
        test_repos.settings.set_setting("test_key", "test_value")
        
        # Get the setting
        value = test_repos.settings.get_setting("test_key")
        assert value == "test_value"
    
    def test_get_nonexistent_setting(self, test_repos):
        """Test getting non-existent setting returns None"""
        value = test_repos.settings.get_setting("nonexistent")
        assert value is None
    
    def test_update_setting(self, test_repos):
        """Test updating existing setting"""
        # Set initial value
        test_repos.settings.set_setting("update_test", "initial")
        
        # Update value
        test_repos.settings.set_setting("update_test", "updated")
        
        # Verify update
        value = test_repos.settings.get_setting("update_test")
        assert value == "updated"
    
    def test_delete_setting(self, test_repos):
        """Test deleting setting"""
        # Set a setting
        test_repos.settings.set_setting("delete_test", "value")
        
        # Delete it
        success = test_repos.settings.delete_setting("delete_test")
        assert success is True
        
        # Verify deletion
        value = test_repos.settings.get_setting("delete_test")
        assert value is None
    
    def test_get_all_settings(self, test_repos):
        """Test getting all settings"""
        # Set multiple settings
        test_repos.settings.set_setting("key1", "value1")
        test_repos.settings.set_setting("key2", "value2")
        test_repos.settings.set_setting("key3", "value3")
        
        # Get all settings
        all_settings = test_repos.settings.get_all_settings()
        
        assert len(all_settings) == 3
        assert all_settings["key1"] == "value1"
        assert all_settings["key2"] == "value2"
        assert all_settings["key3"] == "value3"


class TestTagRepository:
    """Test tag repository"""
    
    def test_add_tag(self, test_repos):
        """Test adding a tag"""
        tag = test_repos.tags.add_tag(
            name="test_tag",
            description="Test description",
            background_color="000000",
            foreground_color="FFFFFF",
        )
        
        assert tag.name == "test_tag"
        assert tag.description == "Test description"
        assert tag.background_color == "000000"
        assert tag.foreground_color == "FFFFFF"
    
    def test_get_tag(self, test_repos):
        """Test getting tag by name"""
        # Add a tag
        test_repos.tags.add_tag(
            name="get_test",
            description="Get test",
            background_color="FF0000",
            foreground_color="00FF00",
        )
        
        # Get the tag
        tag = test_repos.tags.get_tag("get_test")
        assert tag is not None
        assert tag.name == "get_test"
        assert tag.description == "Get test"
    
    def test_update_tag(self, test_repos):
        """Test updating tag"""
        # Add a tag
        test_repos.tags.add_tag(
            name="update_test",
            description="Initial",
            background_color="000000",
            foreground_color="FFFFFF",
        )
        
        # Update it
        updated = test_repos.tags.update_tag(
            name="update_test",
            description="Updated",
            background_color="FFFFFF",
        )
        
        assert updated is not None
        assert updated.description == "Updated"
        assert updated.background_color == "FFFFFF"
        assert updated.foreground_color == "FFFFFF"  # Unchanged
    
    def test_delete_tag(self, test_repos):
        """Test deleting tag"""
        # Add a tag
        test_repos.tags.add_tag(
            name="delete_test",
            description="To delete",
            background_color="000000",
            foreground_color="FFFFFF",
        )
        
        # Delete it
        success = test_repos.tags.delete_tag("delete_test")
        assert success is True
        
        # Verify deletion
        tag = test_repos.tags.get_tag("delete_test")
        assert tag is None
    
    def test_tag_mappings(self, test_repos):
        """Test tag to account mappings"""
        # Add a tag
        tag = test_repos.tags.add_tag(
            name="mapping_test",
            description="Mapping test",
            background_color="000000",
            foreground_color="FFFFFF",
        )
        
        # Add mappings
        test_repos.tags.add_tag_mapping("mapping_test", "0x123", "ethereum")
        test_repos.tags.add_tag_mapping("mapping_test", "0x456", "ethereum")
        
        # Get mappings
        mappings = test_repos.tags.get_tag_mappings("mapping_test")
        assert len(mappings) == 2
        
        # Get accounts for tag
        accounts = test_repos.tags.get_accounts_for_tag("mapping_test")
        assert len(accounts) == 2
        assert ("0x123", "ethereum") in accounts
        assert ("0x456", "ethereum") in accounts


class TestBlockchainAccountRepository:
    """Test blockchain account repository"""
    
    def test_add_account(self, test_repos):
        """Test adding blockchain account"""
        account = test_repos.accounts.add_account(
            blockchain="ethereum",
            address="0x1234567890abcdef",
            label="Test Account",
        )
        
        assert account.blockchain == "ethereum"
        assert account.account == "0x1234567890abcdef"
        assert account.label == "Test Account"
    
    def test_get_account(self, test_repos):
        """Test getting account"""
        # Add account
        test_repos.accounts.add_account(
            blockchain="bitcoin",
            address="1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        )
        
        # Get account
        account = test_repos.accounts.get_account(
            blockchain="bitcoin",
            address="1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        )
        
        assert account is not None
        assert account.blockchain == "bitcoin"
        assert account.account == "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
    
    def test_get_accounts_by_blockchain(self, test_repos):
        """Test getting accounts by blockchain"""
        # Add multiple accounts
        test_repos.accounts.add_account("ethereum", "0x111")
        test_repos.accounts.add_account("ethereum", "0x222")
        test_repos.accounts.add_account("bitcoin", "1BTC")
        
        # Get Ethereum accounts
        eth_accounts = test_repos.accounts.get_accounts_by_blockchain("ethereum")
        assert len(eth_accounts) == 2
        
        # Get Bitcoin accounts
        btc_accounts = test_repos.accounts.get_accounts_by_blockchain("bitcoin")
        assert len(btc_accounts) == 1
    
    def test_delete_account(self, test_repos):
        """Test deleting account"""
        # Add account
        test_repos.accounts.add_account(
            blockchain="ethereum",
            address="0xdelete",
        )
        
        # Delete it
        success = test_repos.accounts.delete_account("ethereum", "0xdelete")
        assert success is True
        
        # Verify deletion
        account = test_repos.accounts.get_account("ethereum", "0xdelete")
        assert account is None


class TestManualBalanceRepository:
    """Test manual balance repository"""
    
    def test_add_balance(self, test_repos):
        """Test adding manual balance"""
        balance = test_repos.manual_balances.add_balance(
            asset="ETH",
            label="Cold Storage",
            amount="10.5",
            location="O",  # Offline
            tags=["cold", "hodl"],
        )
        
        assert balance.asset == "ETH"
        assert balance.label == "Cold Storage"
        assert balance.amount == "10.5"
        assert balance.location == "O"
    
    def test_get_balance_with_tags(self, test_repos):
        """Test getting balance with tags"""
        # First add tags
        test_repos.tags.add_tag("tag1", "Tag 1", "000000", "FFFFFF")
        test_repos.tags.add_tag("tag2", "Tag 2", "FFFFFF", "000000")
        
        # Add balance with tags
        balance = test_repos.manual_balances.add_balance(
            asset="BTC",
            label="Hardware Wallet",
            amount="1.5",
            location="O",
            tags=["tag1", "tag2"],
        )
        
        # Get balance tags
        tags = test_repos.manual_balances.get_balance_tags(balance.identifier)
        assert len(tags) == 2
        assert "tag1" in tags
        assert "tag2" in tags
    
    def test_update_balance(self, test_repos):
        """Test updating balance"""
        # Add balance
        balance = test_repos.manual_balances.add_balance(
            asset="DAI",
            label="DeFi Yield",
            amount="1000",
            location="B",  # Blockchain
        )
        
        # Update amount
        updated = test_repos.manual_balances.update_balance(
            identifier=balance.identifier,
            amount="1500",
        )
        
        assert updated is not None
        assert updated.amount == "1500"
        assert updated.label == "DeFi Yield"  # Unchanged
    
    def test_get_balances_by_asset(self, test_repos):
        """Test getting balances by asset"""
        # Add multiple balances
        test_repos.manual_balances.add_balance("ETH", "Wallet 1", "5", "B")
        test_repos.manual_balances.add_balance("ETH", "Wallet 2", "3", "B")
        test_repos.manual_balances.add_balance("BTC", "Wallet 3", "1", "B")
        
        # Get ETH balances
        eth_balances = test_repos.manual_balances.get_balances_by_asset("ETH")
        assert len(eth_balances) == 2
        
        # Calculate total
        total = sum(FVal(b.amount) for b in eth_balances)
        assert total == FVal("8")