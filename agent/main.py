import time
import random
import sys
import config  # Make sure this import is here
from config import (
    HIGH_FREQ_INTERVAL, LOW_FREQ_INTERVAL, 
    FAST_FREQ_INTERVAL, CPU_THRESHOLD, RAM_THRESHOLD
)
from metrics import MetricsCollector
from sender import DataSender

def check_thresholds(metrics_data):
    """
    Checks if any metrics have breached their thresholds.
    Returns True if a threshold is breached, False otherwise.
    """
    if metrics_data['cpu_percent_overall'] > CPU_THRESHOLD:
        return True
    if metrics_data['ram_percent_used'] > RAM_THRESHOLD:
        return True
    
    # You could also add a disk check here:
    # for disk in metrics_data.get('disk_usage', []):
    #     if disk['percent_used'] > DISK_THRESHOLD:
    #         return True
            
    return False

def main():
    print("--- Distributed Monitoring Agent ---")
    
    # --- Handle "Thundering Herd" ---
    jitter = random.uniform(0, 10)
    print(f"Applying startup jitter: waiting {jitter:.2f} seconds...")
    time.sleep(jitter)
    
    # Initialize components
    try:
        metrics = MetricsCollector()
        sender = DataSender()
    except Exception as e:
        print(f"Critical error on init: {e}")
        sys.exit(1)
        
    print(f"Agent ID: {metrics.agent_id}")
    print(f"Sending data to: {config.SERVER_URL}")
    print(f"Standard Interval: {HIGH_FREQ_INTERVAL}s | Fast Interval: {FAST_FREQ_INTERVAL}s")
    print(f"Thresholds: CPU > {CPU_THRESHOLD}% | RAM > {RAM_THRESHOLD}%")

    # --- Send Static Data (Once on Start) ---
    print("Sending initial static data...")
    sender.send_data("static", metrics.get_static_data())
    
    # --- Main Loop ---
    last_low_freq_time = 0
    current_interval = HIGH_FREQ_INTERVAL # Start at the normal interval
    
    # Initialize CPU % collection before loop
    psutil.cpu_percent(interval=None)
    time.sleep(0.5) # Let it establish a baseline
    
    try:
        while True:
            loop_start_time = time.time()
            
            # --- High-Frequency Task ---
            try:
                high_freq_data = metrics.get_high_freq_data()
                sender.send_data("high_freq", high_freq_data)
                
                # --- NEW THRESHOLD LOGIC ---
                if check_thresholds(high_freq_data):
                    if current_interval != FAST_FREQ_INTERVAL:
                        print(f"Threshold breached! Switching to {FAST_FREQ_INTERVAL}s interval.")
                    current_interval = FAST_FREQ_INTERVAL
                else:
                    if current_interval != HIGH_FREQ_INTERVAL:
                        print(f"Metrics normal. Returning to {HIGH_FREQ_INTERVAL}s interval.")
                    current_interval = HIGH_FREQ_INTERVAL
                # --- END NEW LOGIC ---

                print(f"Sent high_freq data (CPU: {high_freq_data['cpu_percent_overall']}%)")
                
            except Exception as e:
                print(f"Error collecting high-freq data: {e}")

            # --- Low-Frequency Task ---
            # This task is independent of the high-freq interval
            if (loop_start_time - last_low_freq_time) >= LOW_FREQ_INTERVAL:
                try:
                    print("Collecting low-freq data...")
                    low_freq_data = metrics.get_low_freq_data()
                    sender.send_data("low_freq", low_freq_data)
                    print("Sent low_freq data.")
                    last_low_freq_time = loop_start_time
                except Exception as e:
                    print(f"Error collecting low-freq data: {e}")
            
            # --- Sleep ---
            # Calculate sleep time based on the *current_interval*
            time_spent = time.time() - loop_start_time
            sleep_time = max(0, current_interval - time_spent)
            time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        print("\nAgent shutting down...")
    except Exception as e:
        print(f"CRITICAL ERROR in main loop: {e}")
    finally:
        print("Agent stopped.")

if __name__ == "__main__":
    # This import is needed here for the CPU init
    import psutil 
    main()