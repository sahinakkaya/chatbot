import logging
import json
from kafka import KafkaProducer, KafkaConsumer

logger = logging.getLogger(__name__)


class KafkaHelper:
    def __init__(self, settings):
        self.producer: KafkaProducer | None = None
        self.consumer: KafkaConsumer | None = None
        self.settings = settings

    def initialize(self, producer_args={}, consumer_args={}):
        if self.settings.produce_topic:
            self.producer = KafkaProducer(
                bootstrap_servers=self.settings.kafka_bootstrap_servers.split(","),
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                **producer_args,
            )
            logger.info(f"Kafka producer initialized for {self.settings.app_name}")
        if self.settings.consume_topic:
            self.consumer = KafkaConsumer(
                self.settings.consume_topic,
                bootstrap_servers=self.settings.kafka_bootstrap_servers.split(","),
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                **consumer_args,
            )
            logger.info(
                f"Kafka consumer initialized for {self.settings.app_name} on topic {self.settings.consume_topic}"
            )

    def publish(self, topic: str, message: dict):
        if self.producer is None:
            raise RuntimeError("Kafka producer not initialized")

        try:
            self.producer.send(topic, message)
            logger.info(f"Published to Kafka {topic=} user_id={message.get('userid')}")
        except Exception as e:
            logger.error(
                f"Kafka publish failed error={str(e)}",
                extra={"topic": topic, "error": str(e)},
            )

    def teardown(self):
        if self.producer:
            self.producer.close()
            logger.info(f"Kafka producer closed for {self.settings.app_name}")

        if self.consumer:
            self.consumer.close()
            logger.info(f"Kafka consumer closed for {self.settings.app_name}")
