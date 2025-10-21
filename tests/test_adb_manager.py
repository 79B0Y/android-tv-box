"""Tests for ADB Manager."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.android_tv_box.adb_manager import (
    ADBCommandResult,
    ADBManager,
    CommandCache,
)


class TestCommandCache:
    """Test CommandCache class."""
    
    def test_cache_initialization(self):
        """Test cache is initialized correctly."""
        cache = CommandCache()
        assert len(cache.cache) == 0
        assert cache.max_size == 100
        assert cache.hits == 0
        assert cache.misses == 0
    
    def test_cache_key_generation(self):
        """Test cache key generation."""
        cache = CommandCache()
        key = cache.get_cache_key("device123", "echo test")
        assert "device123" in key
        assert isinstance(key, str)
    
    def test_cache_set_and_get(self):
        """Test setting and getting cached values."""
        cache = CommandCache()
        result = ADBCommandResult(success=True, stdout="test output")
        
        key = cache.get_cache_key("device123", "echo test")
        cache.set_cached(key, result)
        
        cached = cache.get_cached(key)
        assert cached is not None
        assert cached.success is True
        assert cached.stdout == "test output"
        assert cache.hits == 1
        assert cache.misses == 0
    
    def test_cache_miss(self):
        """Test cache miss."""
        cache = CommandCache()
        key = cache.get_cache_key("device123", "echo test")
        
        cached = cache.get_cached(key)
        assert cached is None
        assert cache.hits == 0
        assert cache.misses == 1
    
    def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = CommandCache()
        cache.max_size = 3
        
        # Fill cache
        for i in range(3):
            key = cache.get_cache_key("device123", f"cmd{i}")
            result = ADBCommandResult(success=True, stdout=f"output{i}")
            cache.set_cached(key, result)
        
        assert len(cache.cache) == 3
        
        # Add one more - should evict oldest
        key4 = cache.get_cache_key("device123", "cmd3")
        result4 = ADBCommandResult(success=True, stdout="output3")
        cache.set_cached(key4, result4)
        
        assert len(cache.cache) == 3
        
        # First item should be evicted
        key0 = cache.get_cache_key("device123", "cmd0")
        assert not cache.is_cached(key0)
    
    def test_cache_stats(self):
        """Test cache statistics."""
        cache = CommandCache()
        result = ADBCommandResult(success=True, stdout="test")
        
        key = cache.get_cache_key("device123", "echo test")
        cache.set_cached(key, result)
        
        cache.get_cached(key)  # Hit
        cache.get_cached("nonexistent")  # Miss
        
        stats = cache.get_stats()
        assert stats["size"] == 1
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 50.0


class TestADBManager:
    """Test ADBManager class."""
    
    @pytest.mark.asyncio
    async def test_manager_initialization(self):
        """Test ADB manager initialization."""
        manager = ADBManager("192.168.1.100", 5555)
        assert manager.host == "192.168.1.100"
        assert manager.port == 5555
        assert manager.device_id == "192.168.1.100:5555"
        assert manager._connected is False
    
    @pytest.mark.asyncio
    async def test_command_execution_success(self, mock_adb_device):
        """Test successful command execution."""
        manager = ADBManager("192.168.1.100", 5555)
        manager._device = mock_adb_device
        manager._connected = True
        
        mock_adb_device.shell.return_value = "test output"
        
        result = await manager.execute_command("echo test", use_cache=False)
        
        assert result.success is True
        assert result.stdout == "test output"
    
    @pytest.mark.asyncio
    async def test_command_execution_cached(self, mock_adb_device):
        """Test cached command execution."""
        manager = ADBManager("192.168.1.100", 5555)
        manager._device = mock_adb_device
        manager._connected = True
        
        mock_adb_device.shell.return_value = "test output"
        
        # First call - should execute command
        result1 = await manager.execute_command("echo test", use_cache=True)
        assert result1.success is True
        
        # Second call - should use cache
        result2 = await manager.execute_command("echo test", use_cache=True)
        assert result2.success is True
        assert result2.stdout == "test output"
        
        # Command should only be executed once
        assert mock_adb_device.shell.call_count == 1
    
    @pytest.mark.asyncio
    async def test_command_execution_not_connected(self):
        """Test command execution when not connected."""
        manager = ADBManager("192.168.1.100", 5555)
        manager._connected = False
        
        result = await manager.execute_command("echo test")
        
        assert result.success is False
        assert result.error == "cannot_connect"
    
    @pytest.mark.asyncio
    async def test_is_connected_check(self, mock_adb_device):
        """Test connection status check."""
        manager = ADBManager("192.168.1.100", 5555)
        manager._device = mock_adb_device
        manager._connected = True
        
        mock_adb_device.shell.return_value = "ping"
        
        is_connected = await manager.is_connected()
        assert is_connected is True
    
    @pytest.mark.asyncio
    async def test_volume_state_parsing(self, mock_adb_device):
        """Test volume state parsing."""
        manager = ADBManager("192.168.1.100", 5555)
        manager._device = mock_adb_device
        manager._connected = True
        
        mock_adb_device.shell.return_value = "volume is 8 in range [0..15]"
        
        current, max_vol, is_muted = await manager.get_volume_state()
        
        assert current == 8
        assert max_vol == 15
        assert is_muted is False
    
    @pytest.mark.asyncio
    async def test_wifi_state_parsing(self, mock_adb_device):
        """Test WiFi state parsing."""
        manager = ADBManager("192.168.1.100", 5555)
        manager._device = mock_adb_device
        manager._connected = True
        
        def shell_side_effect(cmd):
            if "wifi_on" in cmd:
                return "1"
            elif "SSID" in cmd:
                return 'SSID: "TestNetwork"'
            elif "ip addr" in cmd:
                return "inet 192.168.1.100/24"
            return ""
        
        mock_adb_device.shell.side_effect = shell_side_effect
        
        enabled, ssid, ip = await manager.get_wifi_state()
        
        assert enabled is True
        assert ssid == "TestNetwork"
        assert ip == "192.168.1.100"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

