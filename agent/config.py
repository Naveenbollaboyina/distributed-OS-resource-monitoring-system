import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Server Config ---
SERVER_URL = os.getenv("SERVER_URL")
API_KEY = os.getenv("API_KEY")

# --- Agent Config ---
# Get intervals, with sensible defaults
HIGH_FREQ_INTERVAL = int(os.getenv("HIGH_FREQ_INTERVAL", 10))
LOW_FREQ_INTERVAL = int(os.getenv("LOW_FREQ_INTERVAL", 300))

# --- NEW: Fast Reporting Config ---
# The faster interval when a threshold is breached (in seconds)
FAST_FREQ_INTERVAL = int(os.getenv("FAST_FREQ_INTERVAL", 5))

# The metric thresholds that trigger fast reporting
CPU_THRESHOLD = float(os.getenv("CPU_THRESHOLD", 85.0))
RAM_THRESHOLD = float(os.getenv("RAM_THRESHOLD", 85.0))
# You can also add a disk threshold if you like
# DISK_THRESHOLD = float(os.getenv("DISK_THRESHOLD", 90.0))


# --- Local Agent Files ---
AGENT_ID_FILE = os.getenv("AGENT_ID_FILE", ".agent_id")