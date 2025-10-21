"""Generic application monitoring framework for Android TV Box Integration."""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

_LOGGER = logging.getLogger(__name__)


@dataclass
class AppHealthData:
    """Health data for a monitored application."""
    health_status: str = "unknown"
    is_running: bool = False
    memory_usage_mb: float = 0.0
    memory_percentage: float = 0.0
    cpu_usage: float = 0.0
    crash_detected: bool = False
    anr_detected: bool = False
    last_check: Optional[datetime] = None
    restart_count: int = 0
    last_restart_time: Optional[datetime] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)


class AppMonitor(ABC):
    """Abstract base class for application monitoring."""
    
    def __init__(self, package_name: str, adb_manager):
        """Initialize app monitor.
        
        Args:
            package_name: The Android package name to monitor
            adb_manager: ADBManager instance for executing commands
        """
        self.package_name = package_name
        self.adb_manager = adb_manager
        self._logger = _LOGGER.getChild(package_name)
        self._health_data = AppHealthData()
    
    @abstractmethod
    async def check_process_status(self) -> bool:
        """Check if the application process is running.
        
        Returns:
            bool: True if the process is running, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_memory_usage(self) -> tuple[Optional[float], Optional[float]]:
        """Get memory usage of the application.
        
        Returns:
            tuple: (memory_mb, memory_percentage)
        """
        pass
    
    @abstractmethod
    async def get_cpu_usage(self) -> Optional[float]:
        """Get CPU usage of the application.
        
        Returns:
            float: CPU usage percentage, or None if unavailable
        """
        pass
    
    @abstractmethod
    async def get_health_status(self) -> AppHealthData:
        """Perform comprehensive health check.
        
        Returns:
            AppHealthData: Health status and metrics
        """
        pass
    
    @abstractmethod
    async def restart_app(self) -> bool:
        """Restart the application.
        
        Returns:
            bool: True if restart successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def force_stop_app(self) -> bool:
        """Force stop the application.
        
        Returns:
            bool: True if stop successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def force_start_app(self) -> bool:
        """Force start the application.
        
        Returns:
            bool: True if start successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def clear_cache(self) -> bool:
        """Clear application cache.
        
        Returns:
            bool: True if cache cleared successfully, False otherwise
        """
        pass
    
    async def get_app_logs(self, lines: int = 50) -> List[str]:
        """Get application logs.
        
        Args:
            lines: Number of log lines to retrieve
            
        Returns:
            list: Log lines
        """
        # Generic implementation using logcat
        cmd = f"logcat -s {self.package_name}:* -v time -t {lines}"
        result = await self.adb_manager.execute_command(cmd)
        if result.success and result.stdout:
            return result.stdout.split('\n')
        return []
    
    async def get_crash_logs(self) -> List[str]:
        """Get crash logs for the application.
        
        Returns:
            list: Crash log lines
        """
        # Generic implementation
        cmd = "logcat -b crash -v time -t 25"
        result = await self.adb_manager.execute_command(cmd)
        if result.success and result.stdout:
            # Filter for this app's package name
            lines = result.stdout.split('\n')
            return [line for line in lines if self.package_name in line]
        return []
    
    def get_health_data(self) -> AppHealthData:
        """Get current health data.
        
        Returns:
            AppHealthData: Current health status
        """
        return self._health_data
    
    def should_restart(
        self, 
        memory_threshold: float = 80.0, 
        cpu_threshold: float = 90.0,
        max_restart_attempts: int = 3
    ) -> bool:
        """Determine if app should be restarted based on health metrics.
        
        Args:
            memory_threshold: Memory usage percentage threshold
            cpu_threshold: CPU usage percentage threshold
            max_restart_attempts: Maximum number of restart attempts
            
        Returns:
            bool: True if restart is recommended
        """
        # Don't restart if too many recent attempts
        if self._health_data.restart_count >= max_restart_attempts:
            return False
        
        # Restart if not running
        if not self._health_data.is_running:
            return True
        
        # Restart if unhealthy and resource usage is high
        if self._health_data.health_status in ["unhealthy", "crashed"]:
            if (self._health_data.memory_percentage > memory_threshold or
                self._health_data.cpu_usage > cpu_threshold):
                return True
        
        # Restart if crashed
        if self._health_data.crash_detected:
            return True
        
        return False

