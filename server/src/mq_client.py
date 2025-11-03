import pika
import json
from .config import settings

# This is the name of the queue our worker will listen to
METRICS_QUEUE_NAME = "metrics_queue"

def get_mq_connection():
    """
    Establishes a new connection to RabbitMQ.
    """
    try:
        credentials = pika.PlainCredentials(settings.MQ_USER, settings.MQ_PASSWORD)
        params = pika.ConnectionParameters(
            host=settings.MQ_HOST,
            credentials=credentials
        )
        return pika.BlockingConnection(params)
    except pika.exceptions.AMQPConnectionError as e:
        print(f"Failed to connect to RabbitMQ: {e}")
        return None

def publish_message(message_body: dict):
    """
    Publishes a single message to the metrics queue.
    """
    connection = None
    try:
        connection = get_mq_connection()
        if not connection:
            print("Cannot publish message: No RabbitMQ connection.")
            return False
            
        channel = connection.channel()
        
        # Declare the queue. This is idempotent, meaning it's safe
        # to run every time. It will create it if it doesn't exist.
        channel.queue_declare(queue=METRICS_QUEUE_NAME, durable=True)
        
        # Publish the message
        channel.basic_publish(
            exchange='',
            routing_key=METRICS_QUEUE_NAME,
            body=json.dumps(message_body),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
            )
        )
        print("Message published to queue.")
        return True
        
    except Exception as e:
        print(f"Error publishing message: {e}")
        return False
        
    finally:
        if connection and connection.is_open:
            connection.close()