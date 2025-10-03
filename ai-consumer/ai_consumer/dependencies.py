from kafka import KafkaConsumer, KafkaProducer
from openai import OpenAI
from ai_consumer.config import settings

class AIConsumer:
    def __init__(self):
        self.consumer: KafkaConsumer | None = None
        self.producer: KafkaProducer | None = None
        self.openai_client = OpenAI(api_key=settings.openai_api_key)
