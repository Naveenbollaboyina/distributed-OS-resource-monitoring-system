import psutil
import platform
import socket
from utils import get_or_create_agent_id

class MetricsCollector:
    def __init__(self):
        # Store the agent's unique ID
        self.agent_id = get_or_create_agent_id()
        
        # Initialize last I/O counters to calculate deltas
        self.last_net_io = psutil.net_io_counters()
        self.last_disk_io = psutil.disk_io_counters()


    def get_static_data(self):
        """
        Gathers one-time static data about the machine.
        This now filters out virtual filesystems like 'squashfs' (snaps).
        """
        
        # Define a list of filesystem types to ignore
        FSTYPES_TO_IGNORE = ['squashfs']
        
        filtered_partitions = []
        for p in psutil.disk_partitions():
            # Skip any filesystem type we don't care about
            # or any mountpoint that is clearly a snap mount.
            if p.fstype in FSTYPES_TO_IGNORE or p.mountpoint.startswith('/snap/'):
                continue
            
            filtered_partitions.append({
                "device": p.device, 
                "mountpoint": p.mountpoint, 
                "fstype": p.fstype
            })

        return {
            "agent_id": self.agent_id,
            "hostname": socket.gethostname(),
            "os": platform.platform(),
            "cpu_cores_physical": psutil.cpu_count(logical=False),
            "cpu_cores_logical": psutil.cpu_count(logical=True),
            "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "partitions": filtered_partitions # This list is now filtered
        }


    def get_low_freq_data(self):
        """
        Gathers data that doesn't change as often.
        """
        disk_usage = []
        
        # Define a list of filesystem types to ignore
        # 'squashfs' is used by snap packages
        FSTYPES_TO_IGNORE = ['squashfs']

        for p in psutil.disk_partitions():
            
            # --- ADD THIS FILTER ---
            # Skip any filesystem type we don't care about
            # or any mountpoint that is clearly a snap mount.
            if p.fstype in FSTYPES_TO_IGNORE or p.mountpoint.startswith('/snap/'):
                continue 
            # --- END OF FILTER ---
            
            try:
                usage = psutil.disk_usage(p.mountpoint)
                disk_usage.append({
                    "mountpoint": p.mountpoint,
                    "percent_used": usage.percent,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2)
                })
            except (FileNotFoundError, PermissionError):
                continue # Skip inaccessible drives (e.g., CD-ROM)

        return {
            "agent_id": self.agent_id,
            "boot_time_timestamp": psutil.boot_time(),
            "logged_in_users": [user.name for user in psutil.users()],
            "disk_usage": disk_usage  # This list will now be clean!
        }

    def get_high_freq_data(self):
        """
        Gathers rapidly changing performance metrics.
        """
        # --- I/O Deltas ---
        # Network
        current_net_io = psutil.net_io_counters()
        net_io = {
            "bytes_sent_per_sec": (current_net_io.bytes_sent - self.last_net_io.bytes_sent),
            "bytes_recv_per_sec": (current_net_io.bytes_recv - self.last_net_io.bytes_recv)
        }
        self.last_net_io = current_net_io
        
        # Disk
        current_disk_io = psutil.disk_io_counters()
        disk_io = {
            "read_bytes_per_sec": (current_disk_io.read_bytes - self.last_disk_io.read_bytes),
            "write_bytes_per_sec": (current_disk_io.write_bytes - self.last_disk_io.write_bytes)
        }
        self.last_disk_io = current_disk_io
        
        # --- Top 5 Processes ---
        # Get all processes' info
        processes = []
        # Calling cpu_percent(None) here starts the interval counter
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent']):
            try:
                # cpu_percent(None) returns the value since last call
                proc.info['cpu_percent'] = proc.cpu_percent(interval=None) 
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Sort by CPU and get top 5
        top_5_cpu = sorted(processes, key=lambda p: p['cpu_percent'], reverse=True)[:5]
        
        # --- Final Payload ---
        return {
            "agent_id": self.agent_id,
            "cpu_percent_overall": psutil.cpu_percent(interval=None),
            "cpu_percent_per_core": psutil.cpu_percent(interval=None, percpu=True),
            "ram_percent_used": psutil.virtual_memory().percent,
            "swap_percent_used": psutil.swap_memory().percent,
            "network_io": net_io,
            "disk_io": disk_io,
            "top_5_processes": top_5_cpu
        }