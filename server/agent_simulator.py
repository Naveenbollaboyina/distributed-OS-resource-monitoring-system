import requests
import time
import random
import uuid
import multiprocessing
import os
from dotenv import load_dotenv

# --- Configuration ---
# Load config from central-server/.env
load_dotenv('.env') 

# <-- SET HOW MANY AGENTS TO SIMULATE
NUM_AGENTS = 5  

# Construct the server URL. Assumes the server is running on localhost:8000
# You can override this by setting SERVER_URL in your .env file
SERVER_URL = f"{os.getenv('SERVER_URL', 'http://localhost:8000')}/v1/data/ingest"
API_KEY = os.getenv('AGENT_API_KEY')

# Intervals from agent config
HIGH_FREQ_INTERVAL = 10
FAST_FREQ_INTERVAL = 5
LOW_FREQ_INTERVAL = 300

# Thresholds from agent config
CPU_THRESHOLD = 85.0
RAM_THRESHOLD = 85.0

# --- Fake Data Generators ---

def get_fake_static_data(agent_id, hostname):
    """Generates a fake static data payload."""
    return {
        "agent_id": str(agent_id),
        "hostname": hostname,
        "group_name": "Simulated College",
        "sub_group_name": f"Lab {random.randint(1, 5)}",
        "os": "Linux-Simulated-x86_64",
        "cpu_cores_physical": 8,
        "cpu_cores_logical": 16,
        "ram_total_gb": 15.6,
        "partitions": [{"device": "/dev/sda1", "mountpoint": "/", "fstype": "ext4"}]
    }

def get_fake_high_freq_data(agent_id):
    """Generates fake high-frequency metrics."""
    # 1 in 10 chance to breach threshold
    breached = random.randint(0, 10) > 8 
    
    return {
        "agent_id": str(agent_id),
        "cpu_percent_overall": random.uniform(86.0, 95.0) if breached else random.uniform(10.0, 50.0),
        "ram_percent_used": random.uniform(86.0, 95.0) if breached else random.uniform(20.0, 60.0),
        "swap_percent_used": 0.0,
        "network_io": {
            "bytes_sent_per_sec": random.randint(1000, 50000),
            "bytes_recv_per_sec": random.randint(10000, 500000)
        },
        "disk_io": {
            "read_bytes_per_sec": random.randint(0, 100000),
            "write_bytes_per_sec": random.randint(50000, 1000000)
        },
        # Only send top_5 if breached (to be realistic)
        "top_5_processes": [
            {"pid": 123, "name": "chrome", "username": "sim", "cpu_percent": 45.1, "memory_percent": 10.2}
        ] if breached else []
    }

def get_fake_low_freq_data(agent_id):
    """Generates fake disk usage."""
    return {
        "agent_id": str(agent_id),
        "disk_usage": [
            {
                "mountpoint": "/",
                "percent_used": random.uniform(20.0, 90.0),
                "total_gb": 467.0,
                "used_gb": 200.0
            }
        ]
    }

def run_agent_simulation(agent_num):
    """Main loop for a single simulated agent."""
    agent_id = uuid.uuid4()
    hostname = f"simulated-pc-{agent_num}"
    print(f"[Agent {hostname}]: Starting...")
    
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {API_KEY}"})

    # --- 1. Send Static Data ---
    try:
        static_data = {"type": "static", "payload": get_fake_static_data(agent_id, hostname)}
        session.post(SERVER_URL, json=static_data, timeout=5)
        print(f"[Agent {hostname}]: Sent static data.")
    except Exception as e:
        print(f"Error sending static data for {hostname}: {e}")
        return # Exit if static fails

    # --- 2. Main Loop ---
    last_low_freq_time = 0
    current_interval = HIGH_FREQ_INTERVAL
    
    while True:
        loop_start_time = time.time()
        
        # --- High-Frequency ---
        try:
            high_freq_data = get_fake_high_freq_data(agent_id)
            payload = {"type": "high_freq", "payload": high_freq_data}
            session.post(SERVER_URL, json=payload, timeout=2)
            
            # Check thresholds
            if high_freq_data['cpu_percent_overall'] > CPU_THRESHOLD:
                current_interval = FAST_FREQ_INTERVAL
            else:
                current_interval = HIGH_FREQ_INTERVAL

        except Exception as e:
            print(f"Error sending high_freq for {hostname}: {e}")

        # --- Low-Frequency ---
        if (loop_start_time - last_low_freq_time) >= LOW_FREQ_INTERVAL:
            try:
                low_freq_data = get_fake_low_freq_data(agent_id)
                payload = {"type": "low_freq", "payload": low_freq_data}
                session.post(SERVER_URL, json=payload, timeout=2)
                print(f"[Agent {hostname}]: Sent low_freq data.")
                last_low_freq_time = loop_start_time
            except Exception as e:
                print(f"Error sending low_freq for {hostname}: {e}")
        
        # --- Sleep ---
        time_spent = time.time() - loop_start_time
        sleep_time = max(0, current_interval - time_spent)
        time.sleep(sleep_time)


if __name__ == "__main__":
    print(f"--- Starting Agent Simulator with {NUM_AGENTS} Agents ---")
    print(f"--- Sending data to {SERVER_URL} ---")
    
    # Install host libraries if needed
    try:
        import requests
        from dotenv import load_dotenv
    except ImportError:
        print("Please install required libraries on your host: pip install requests python-dotenv")
        exit()

    # Create a pool of worker processes
    with multiprocessing.Pool(processes=NUM_AGENTS) as pool:
        pool.map(run_agent_simulation, range(NUM_AGENTS))