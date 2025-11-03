from pydantic import BaseModel, UUID4, Field
from typing import List, Optional, Any

# --- Models for High-Frequency Data ---

class NetworkIO(BaseModel):
    bytes_sent_per_sec: int
    bytes_recv_per_sec: int

class DiskIO(BaseModel):
    read_bytes_per_sec: int
    write_bytes_per_sec: int

class Process(BaseModel):
    pid: int
    name: str
    username: str
    cpu_percent: float
    memory_percent: float

class HighFreqPayload(BaseModel):
    agent_id: UUID4
    cpu_percent_overall: float
    cpu_percent_per_core: List[float] # We get this, but won't store it for now
    ram_percent_used: float
    swap_percent_used: float
    network_io: NetworkIO
    disk_io: DiskIO
    top_5_processes: List[Process] = Field(default_factory=list)

# --- Models for Low-Frequency Data ---

class DiskUsage(BaseModel):
    mountpoint: str
    percent_used: float
    total_gb: float
    used_gb: float

class LowFreqPayload(BaseModel):
    agent_id: UUID4
    boot_time_timestamp: float
    logged_in_users: List[str]
    disk_usage: List[DiskUsage]

# --- Models for Static Data ---

class Partition(BaseModel):
    device: str
    mountpoint: str
    fstype: str

class StaticPayload(BaseModel):
    agent_id: UUID4
    hostname: str
    os: str
    cpu_cores_physical: int
    cpu_cores_logical: int
    ram_total_gb: float
    partitions: List[Partition]
    
    # These are the optional hierarchy fields
    group_name: Optional[str] = None
    sub_group_name: Optional[str] = None

# --- Main Ingestion Model ---
# This is the wrapper object our API will receive

class IngestData(BaseModel):
    type: str  # "static", "high_freq", or "low_freq"
    payload: Any # We will validate this payload in the endpoint