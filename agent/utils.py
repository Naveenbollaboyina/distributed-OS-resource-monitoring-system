import os
import uuid
from config import AGENT_ID_FILE

def get_or_create_agent_id():
    """
    Reads a unique agent ID from a local file.
    If the file doesn't exist, it generates a new UUID,
    saves it, and returns it.
    """
    if os.path.exists(AGENT_ID_FILE):
        try:
            with open(AGENT_ID_FILE, 'r') as f:
                agent_id = f.read().strip()
                if agent_id:
                    return agent_id
        except IOError as e:
            print(f"Error reading agent ID file: {e}")
            
    # File doesn't exist or was empty, create a new ID
    agent_id = str(uuid.uuid4())
    try:
        with open(AGENT_ID_FILE, 'w') as f:
            f.write(agent_id)
    except IOError as e:
        print(f"Error writing new agent ID file: {e}")
        
    return agent_id