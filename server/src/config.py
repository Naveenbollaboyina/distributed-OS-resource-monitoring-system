import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database Configuration
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DB_HOST: str
    DB_PORT: int
    
    # RabbitMQ Configuration
    MQ_HOST: str
    MQ_USER: str
    MQ_PASSWORD: str
    
    # API Security
    AGENT_API_KEY: str

    # Get the database connection string
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # Get the RabbitMQ connection string
    @property
    def RABBITMQ_URL(self) -> str:
        return f"amqp://{self.MQ_USER}:{self.MQ_PASSWORD}@{self.MQ_HOST}/"

    class Config:
        # This tells Pydantic to load from a .env file
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
        env_file_encoding = 'utf-8'

# Create a single, importable instance of the settings
settings = Settings()