"""ISG application monitoring for Android TV Box Integration."""
import logging
import re
from datetime import datetime
from typing import Optional

from .app_monitor import AppHealthData, AppMonitor

_LOGGER = logging.getLogger(__name__)

# ISG health status constants
ISG_HEALTH_HEALTHY = "healthy"
ISG_HEALTH_UNHEALTHY = "unhealthy"
ISG_HEALTH_CRASHED = "crashed"
ISG_HEALTH_NOT_RUNNING = "not_running"
ISG_HEALTH_UNKNOWN = "unknown"


class ISGMonitor(AppMonitor):
    """ISG-specific application monitor."""
    
    def __init__(self, adb_manager):
        """Initialize ISG monitor.
        
        Args:
            adb_manager: ADBManager instance for executing commands
        """
        super().__init__("com.linknlink.app.device.isg", adb_manager)
        self.main_activity = "com.linknlink.app.device.isg/.MainActivity"
    
    async def check_process_status(self) -> bool:
        """Check if ISG process is running."""
        cmd = f"ps | grep {self.package_name}"
        result = await self.adb_manager.execute_command(cmd)
        return result.success and self.package_name in result.stdout
    
    async def get_memory_usage(self) -> tuple[Optional[float], Optional[float]]:
        """Get ISG memory usage."""
        cmd = f"dumpsys meminfo {self.package_name} | head -20"
        result = await self.adb_manager.execute_command(cmd)
        if result.success and result.stdout:
            # Parse memory info
            for line in result.stdout.split('\n'):
                if 'TOTAL' in line:
                    match = re.search(r'(\d+)', line)
                    if match:
                        memory_kb = int(match.group(1))
                        memory_mb = memory_kb / 1024
                        # Rough percentage calculation (assuming 1GB total memory)
                        memory_pct = (memory_mb / 1024) * 100
                        return memory_mb, memory_pct
        return None, None
    
    async def get_cpu_usage(self) -> Optional[float]:
        """Get ISG CPU usage."""
        cmd = f"top -p $(pidof {self.package_name}) -n 1"
        result = await self.adb_manager.execute_command(cmd)
        if result.success and result.stdout:
            # Parse top output for CPU usage
            match = re.search(r'(\d+\.?\d*)%', result.stdout)
            if match:
                return float(match.group(1))
        return None
    
    async def get_health_status(self) -> AppHealthData:
        """Perform comprehensive ISG health check."""
        health_data = AppHealthData(
            health_status=ISG_HEALTH_UNKNOWN,
            is_running=False,
            memory_usage_mb=0.0,
            cpu_usage=0.0,
            crash_detected=False,
            anr_detected=False,
            last_check=datetime.now(),
        )
        
        # Check if process is running
        is_running = await self.check_process_status()
        health_data.is_running = is_running
        
        if not is_running:
            health_data.health_status = ISG_HEALTH_NOT_RUNNING
            self._health_data = health_data
            return health_data
        
        # Get performance metrics
        memory_mb, memory_pct = await self.get_memory_usage()
        if memory_mb:
            health_data.memory_usage_mb = memory_mb
        if memory_pct:
            health_data.memory_percentage = memory_pct
        
        cpu_usage = await self.get_cpu_usage()
        if cpu_usage:
            health_data.cpu_usage = cpu_usage
        
        # Check for crashes
        crash_logs = await self.get_crash_logs()
        health_data.crash_detected = len(crash_logs) > 0
        
        # Check for ANRs (Application Not Responding)
        anr_logs = await self._get_anr_logs()
        health_data.anr_detected = len(anr_logs) > 0
        
        # Determine health status
        if health_data.crash_detected:
            health_data.health_status = ISG_HEALTH_CRASHED
        elif (memory_pct and memory_pct > 80) or (cpu_usage and cpu_usage > 90):
            health_data.health_status = ISG_HEALTH_UNHEALTHY
        else:
            health_data.health_status = ISG_HEALTH_HEALTHY
        
        self._health_data = health_data
        return health_data
    
    async def restart_app(self) -> bool:
        """Restart ISG application."""
        cmd = f"am force-stop {self.package_name} && sleep 2 && am start -n {self.main_activity}"
        result = await self.adb_manager.execute_command(cmd, use_cache=False)
        if result.success:
            self._health_data.restart_count += 1
            self._health_data.last_restart_time = datetime.now()
        return result.success
    
    async def force_stop_app(self) -> bool:
        """Force stop ISG application."""
        cmd = f"am force-stop {self.package_name}"
        result = await self.adb_manager.execute_command(cmd, use_cache=False)
        return result.success
    
    async def force_start_app(self) -> bool:
        """Force start ISG application."""
        cmd = f"am start -n {self.main_activity} --activity-clear-top"
        result = await self.adb_manager.execute_command(cmd, use_cache=False)
        return result.success
    
    async def clear_cache(self) -> bool:
        """Clear ISG application cache."""
        cmd = f"pm clear {self.package_name}"
        result = await self.adb_manager.execute_command(cmd, use_cache=False)
        return result.success
    
    async def _get_anr_logs(self) -> list[str]:
        """Get ANR (Application Not Responding) logs."""
        cmd = "logcat -s ActivityManager:* -v time -t 10 | grep ANR"
        result = await self.adb_manager.execute_command(cmd)
        if result.success and result.stdout:
            # Filter for this app's package name
            lines = result.stdout.split('\n')
            return [line for line in lines if self.package_name in line]
        return []

