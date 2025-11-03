import time
import json
import psutil
from metrics import MetricsCollector

# --- IMPORTANT ---
# This initializes the CPU interval counter for psutil.
# It MUST be called once before the loop.
psutil.cpu_percent(interval=None)
# Give it a moment to establish a baseline before the first read
time.sleep(0.5) 
# ---

print("--- Local Metrics Tester ---")
print("Initializing metrics collector...")

try:
    collector = MetricsCollector()
except Exception as e:
    print(f"Failed to initialize collector: {e}")
    exit()

# --- 1. Print Static Data (Once) ---
# This is the data that would normally be sent on agent start.
print("\n" + "="*30)
print(" STATIC DATA (Collected Once) ")
print("="*30)
try:
    static_data = collector.get_static_data()
    print(json.dumps(static_data, indent=4))
except Exception as e:
    print(f"Error getting static data: {e}")


print("\n" + "="*30)
print(" LIVE METRICS (Updating every 10s) ")
print(" Press CTRL+C to stop")
print("="*30)

# --- 2. Loop and Print Dynamic Data ---
# This loop will print all other metrics every 10 seconds.
try:
    while True:
        print(f"\n--- Collecting metrics at {time.strftime('%Y-%m-%d %H:%M:%S')} ---")
        
        # Get both low and high frequency data
        low_freq_data = collector.get_low_freq_data()
        high_freq_data = collector.get_high_freq_data()
        
        # Combine them into a single dictionary for this test print
        combined_data = {
            "agent_id": collector.agent_id,
            "low_frequency_data": low_freq_data,
            "high_frequency_data": high_freq_data
        }
        
        # Print as formatted JSON
        print(json.dumps(combined_data, indent=4))
        
        # Wait for 10 seconds
        time.sleep(10)

except KeyboardInterrupt:
    print("\nStopping local metrics test.")
except Exception as e:
    print(f"\nAn error occurred during loop: {e}")