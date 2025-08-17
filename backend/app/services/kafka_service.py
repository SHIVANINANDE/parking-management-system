from kafka import KafkaProducer, KafkaConsumer
import json
from app.core.config import settings

class KafkaService:
    def __init__(self):
        self.producer = None
        self.consumer = None
    
    def get_producer(self):
        if not self.producer:
            self.producer = KafkaProducer(
                bootstrap_servers=[settings.KAFKA_BOOTSTRAP_SERVERS],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None
            )
        return self.producer
    
    def get_consumer(self, topics, group_id):
        return KafkaConsumer(
            *topics,
            bootstrap_servers=[settings.KAFKA_BOOTSTRAP_SERVERS],
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest'
        )
    
    async def send_message(self, topic: str, message: dict, key: str = None):
        producer = self.get_producer()
        future = producer.send(topic, value=message, key=key)
        producer.flush()
        return future
    
    def close_producer(self):
        if self.producer:
            self.producer.close()

kafka_service = KafkaService()