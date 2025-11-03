import pika
import json
import sys
import time
from .config import settings
from .database import get_db_connection, release_db_connection
from .models import StaticPayload, HighFreqPayload, LowFreqPayload
from .mq_client import METRICS_QUEUE_NAME
from pydantic import ValidationError

# --- Database Handler Functions ---

def process_static_data(payload: dict):
    """
    Validates and 'upserts' static agent data into the 'agents' table.
    """
    try:
        # 1. Validate the payload
        data = StaticPayload(**payload)
        
        # 2. Get DB connection and write
        conn = get_db_connection()
        if not conn:
            print("Worker: No DB connection. Retrying...")
            return False
            
        with conn.cursor() as cur:
            # This is an "UPSERT" command.
            # If agent_id exists, it updates it.
            # If not, it inserts a new row.
            cur.execute(
                """
                INSERT INTO agents (
                    agent_id, hostname, os, cpu_cores_physical, cpu_cores_logical,
                    ram_total_gb, partitions, group_name, sub_group_name, last_seen
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (agent_id) DO UPDATE SET
                    hostname = EXCLUDED.hostname,
                    os = EXCLUDED.os,
                    cpu_cores_physical = EXCLUDED.cpu_cores_physical,
                    cpu_cores_logical = EXCLUDED.cpu_cores_logical,
                    ram_total_gb = EXCLUDED.ram_total_gb,
                    partitions = EXCLUDED.partitions,
                    group_name = EXCLUDED.group_name,
                    sub_group_name = EXCLUDED.sub_group_name,
                    last_seen = NOW();
                """,
                (
                    str(data.agent_id), data.hostname, data.os, data.cpu_cores_physical,
                    data.cpu_cores_logical, data.ram_total_gb, 
                    json.dumps([p.model_dump() for p in data.partitions]), # Store partitions as JSON
                    data.group_name, data.sub_group_name
                )
            )
        conn.commit()
        print(f"Successfully processed static data for agent {data.agent_id}")
        return True
        
    except ValidationError as e:
        print(f"WORKER: Invalid static data format: {e}")
        return True # Acknowledge message, don't retry bad data
    except Exception as e:
        print(f"WORKER: Error processing static data: {e}")
        return False # Do not acknowledge, retry
    finally:
        release_db_connection(conn)

def process_high_freq_data(payload: dict):
    """
    Validates and inserts high-frequency metrics into the database.
    Also updates the 'last_seen' status for the agent.
    """
    conn = None
    try:
        # 1. Validate payload
        data = HighFreqPayload(**payload)
        
        # 2. Get DB connection
        conn = get_db_connection()
        if not conn:
            print("Worker: No DB connection. Retrying...")
            return False
        
        with conn.cursor() as cur:
            # 3. Insert into the main metrics hypertable
            cur.execute(
                """
                INSERT INTO metrics_high_freq (
                    "timestamp", agent_id, cpu_percent_overall, ram_percent_used,
                    swap_percent_used, disk_read_bytes_per_sec, disk_write_bytes_per_sec,
                    net_bytes_sent_per_sec, net_bytes_recv_per_sec
                )
                VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s, %s);
                """,
                (
                    str(data.agent_id), data.cpu_percent_overall, data.ram_percent_used,
                    data.swap_percent_used, data.disk_io.read_bytes_per_sec,
                    data.disk_io.write_bytes_per_sec, data.network_io.bytes_sent_per_sec,
                    data.network_io.bytes_recv_per_sec
                )
            )
            
            # 4. Insert process data IF it exists (sent on threshold breach)
            if data.top_5_processes:
                for proc in data.top_5_processes:
                    cur.execute(
                        """
                        INSERT INTO metrics_processes (
                            "timestamp", agent_id, pid, name, username, 
                            cpu_percent, memory_percent
                        )
                        VALUES (NOW(), %s, %s, %s, %s, %s, %s);
                        """,
                        (str(data.agent_id), proc.pid, proc.name, proc.username,
                         proc.cpu_percent, proc.memory_percent)
                    )
            
            # 5. Update the agent's 'last_seen' timestamp
            cur.execute(
                "UPDATE agents SET last_seen = NOW() WHERE agent_id = %s;",
                (str(data.agent_id),)
            )
            
        conn.commit()
        print(f"Processed high_freq data for agent {data.agent_id}")
        return True

    except ValidationError as e:
        print(f"WORKER: Invalid high_freq data format: {e}")
        return True # Acknowledge, don't retry bad data
    except Exception as e:
        print(f"WORKER: Error processing high_freq data: {e}")
        return False # Do not acknowledge, retry
    finally:
        release_db_connection(conn)

def process_low_freq_data(payload: dict):
    """
    Validates and inserts low-frequency (disk) metrics.
    """
    conn = None
    try:
        # 1. Validate payload
        data = LowFreqPayload(**payload)
        
        # 2. Get DB connection
        conn = get_db_connection()
        if not conn:
            print("Worker: No DB connection. Retrying...")
            return False

        with conn.cursor() as cur:
            # 3. Loop and insert each disk partition
            for disk in data.disk_usage:
                cur.execute(
                    """
                    INSERT INTO metrics_low_freq_disk (
                        "timestamp", agent_id, mountpoint, percent_used,
                        total_gb, used_gb
                    )
                    VALUES (NOW(), %s, %s, %s, %s, %s);
                    """,
                    (str(data.agent_id), disk.mountpoint, disk.percent_used,
                     disk.total_gb, disk.used_gb)
                )
        
        conn.commit()
        print(f"Processed low_freq (disk) data for agent {data.agent_id}")
        return True

    except ValidationError as e:
        print(f"WORKER: Invalid low_freq data format: {e}")
        return True # Acknowledge, don't retry
    except Exception as e:
        print(f"WORKER: Error processing low_freq data: {e}")
        return False # Do not acknowledge, retry
    finally:
        release_db_connection(conn)

# --- Main Worker Loop ---

def mq_callback(ch, method, properties, body):
    """
    This function is called for every message received from the queue.
    """
    print("\nWORKER: Received new message. Processing...")
    
    try:
        data = json.loads(body)
        msg_type = data.get("type")
        payload = data.get("payload")

        if not msg_type or not payload:
            print("WORKER: Invalid message structure. Discarding.")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # Route the message to the correct processor
        if msg_type == "static":
            success = process_static_data(payload)
        elif msg_type == "high_freq":
            success = process_high_freq_data(payload)
        elif msg_type == "low_freq":
            success = process_low_freq_data(payload)
        else:
            print(f"WORKER: Unknown message type '{msg_type}'. Discarding.")
            success = True # Acknowledge and discard

        # Acknowledge or reject the message
        if success:
            ch.basic_ack(delivery_tag=method.delivery_tag)
            print("WORKER: Message processed and acknowledged.")
        else:
            # Re-queue the message to be retried
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            print("WORKET: Message processing failed. Re-queuing.")

    except json.JSONDecodeError:
        print("WORKER: Failed to decode JSON. Discarding message.")
        ch.basic_ack(delivery_tag=method.delivery_tag) # Discard bad JSON
    except Exception as e:
        print(f"WORKER: Unhandled error in callback: {e}. Discarding.")
        ch.basic_ack(delivery_tag=method.delivery_tag) # Discard


def main():
    """
Main function to start the worker.
    Connects to RabbitMQ and starts consuming messages.
    """
    print("--- Starting Database Worker ---")
    while True:
        try:
            print("Connecting to RabbitMQ...")
            creds = pika.PlainCredentials(settings.MQ_USER, settings.MQ_PASSWORD)
            params = pika.ConnectionParameters(host=settings.MQ_HOST, credentials=creds)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()

            channel.queue_declare(queue=METRICS_QUEUE_NAME, durable=True)
            
            # Only fetch one message at a time
            channel.basic_qos(prefetch_count=1) 
            
            channel.basic_consume(
                queue=METRICS_QUEUE_NAME,
                on_message_callback=mq_callback
            )

            print("Worker is now waiting for messages. To exit press CTRL+C")
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError as e:
            print(f"Failed to connect to RabbitMQ: {e}. Retrying in 5s...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("Worker shutting down.")
            if 'connection' in locals() and connection.is_open:
                connection.close()
            sys.exit(0)
        except Exception as e:
            print(f"An unexpected error occurred: {e}. Restarting in 10s...")
            time.sleep(10)

if __name__ == "__main__":
    main()