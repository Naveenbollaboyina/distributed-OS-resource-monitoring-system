import requests
import threading
import queue
import time
import json
from config import SERVER_URL, API_KEY

class DataSender:
    def __init__(self):
        self.data_queue = queue.Queue()
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        })
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()

    def send_data(self, data_type, payload):
        """
        Public method to add data to the queue.
        This is non-blocking.
        """
        try:
            item = {"type": data_type, "payload": payload, "timestamp": time.time()}
            self.data_queue.put(item)
        except Exception as e:
            print(f"Error adding to queue: {e}")

    def _worker(self):
        """
        Internal worker thread that processes the queue.
        This is where all risk mitigation happens.
        """
        while True:
            try:
                # Get item from queue; this blocks until an item is available
                item = self.data_queue.get()
                
                # Convert payload to JSON
                json_payload = json.dumps(item)

                response = self.session.post(SERVER_URL, data=json_payload, timeout=5)

                if response.status_code == 200:
                    print(f"Successfully sent {item['type']} data.")
                else:
                    # Server error, log it
                    print(f"Server error {response.status_code}: {response.text}")
                    # You could re-queue here, but be careful of infinite loops
                    # For now, we'll just drop it to avoid old data flooding

            except requests.exceptions.ConnectionError:
                # --- This handles Network Congestion / Reliability ---
                print("Network Error: Server unreachable. Retrying in 30s...")
                # Put the item back in the queue to retry
                self.data_queue.put(item)
                # Wait before retrying to avoid spamming
                time.sleep(30) 
            except requests.exceptions.Timeout:
                print("Network Error: Request timed out. Retrying in 30s...")
                self.data_queue.put(item)
                time.sleep(30)
            except Exception as e:
                print(f"Unhandled error in sender worker: {e}")
                # Don't re-queue unknown errors, just log and continue
            
            finally:
                # Signal to the queue that this task is done
                self.data_queue.task_done()