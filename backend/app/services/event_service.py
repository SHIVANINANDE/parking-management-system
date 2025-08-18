"""
Real-time Event Service
Implements comprehensive event streaming architecture with Kafka, event sourcing, 
and CQRS pattern for parking management system.
"""

import json
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from concurrent.futures import ThreadPoolExecutor

from kafka import KafkaProducer, KafkaConsumer
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError

from app.core.config import settings
from app.db.database import get_db
from app.db.redis import get_redis_client

logger = logging.getLogger(__name__)

class EventType(Enum):
    # Parking Spot Events
    SPOT_STATUS_CHANGED = "spot_status_changed"
    SPOT_OCCUPIED = "spot_occupied"
    SPOT_VACATED = "spot_vacated"
    SPOT_RESERVED = "spot_reserved"
    SPOT_MAINTENANCE = "spot_maintenance"
    
    # Reservation Events
    RESERVATION_CREATED = "reservation_created"
    RESERVATION_CONFIRMED = "reservation_confirmed"
    RESERVATION_STARTED = "reservation_started"
    RESERVATION_EXTENDED = "reservation_extended"
    RESERVATION_COMPLETED = "reservation_completed"
    RESERVATION_CANCELLED = "reservation_cancelled"
    RESERVATION_EXPIRED = "reservation_expired"
    RESERVATION_NO_SHOW = "reservation_no_show"
    
    # Payment Events
    PAYMENT_INITIATED = "payment_initiated"
    PAYMENT_COMPLETED = "payment_completed"
    PAYMENT_FAILED = "payment_failed"
    PAYMENT_REFUNDED = "payment_refunded"
    
    # User Events
    USER_ARRIVED = "user_arrived"
    USER_DEPARTED = "user_departed"
    USER_CHECK_IN = "user_check_in"
    USER_CHECK_OUT = "user_check_out"
    
    # System Events
    SYSTEM_ALERT = "system_alert"
    CAPACITY_THRESHOLD = "capacity_threshold"
    SENSOR_UPDATE = "sensor_update"
    NOTIFICATION_SENT = "notification_sent"

class EventPriority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class Event:
    """Base event structure for event sourcing"""
    event_id: str
    event_type: EventType
    aggregate_id: str  # ID of the entity (parking_spot_id, reservation_id, etc.)
    aggregate_type: str  # Type of entity (parking_spot, reservation, etc.)
    event_data: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: datetime
    version: int = 1
    priority: EventPriority = EventPriority.NORMAL
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "event_data": self.event_data,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            "priority": self.priority.value,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        return cls(
            event_id=data["event_id"],
            event_type=EventType(data["event_type"]),
            aggregate_id=data["aggregate_id"],
            aggregate_type=data["aggregate_type"],
            event_data=data["event_data"],
            metadata=data["metadata"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            version=data.get("version", 1),
            priority=EventPriority(data.get("priority", "normal")),
            correlation_id=data.get("correlation_id"),
            causation_id=data.get("causation_id")
        )

class KafkaTopics:
    """Kafka topic configuration"""
    PARKING_SPOTS = "parking-spots"
    RESERVATIONS = "reservations"
    PAYMENTS = "payments"
    NOTIFICATIONS = "notifications"
    USER_ACTIONS = "user-actions"
    SYSTEM_EVENTS = "system-events"
    DEAD_LETTER = "dead-letter-queue"
    
    @classmethod
    def get_all_topics(cls) -> List[str]:
        return [
            cls.PARKING_SPOTS,
            cls.RESERVATIONS,
            cls.PAYMENTS,
            cls.NOTIFICATIONS,
            cls.USER_ACTIONS,
            cls.SYSTEM_EVENTS,
            cls.DEAD_LETTER
        ]

class EventStore:
    """Event store for event sourcing implementation"""
    
    def __init__(self):
        self.redis_client = get_redis_client()
    
    async def append_event(self, event: Event) -> bool:
        """Append event to the event store"""
        try:
            # Store in Redis with TTL
            key = f"events:{event.aggregate_type}:{event.aggregate_id}"
            event_data = json.dumps(event.to_dict())
            
            # Use Redis streams for ordered event storage
            stream_key = f"event_stream:{event.aggregate_type}:{event.aggregate_id}"
            await self.redis_client.xadd(stream_key, event.to_dict())
            
            # Also store latest version for quick lookup
            version_key = f"version:{event.aggregate_type}:{event.aggregate_id}"
            await self.redis_client.set(version_key, event.version)
            
            # Index by event type for efficient querying
            type_key = f"events_by_type:{event.event_type.value}"
            await self.redis_client.lpush(type_key, event.event_id)
            
            return True
        except Exception as e:
            logger.error(f"Failed to append event {event.event_id}: {e}")
            return False
    
    async def get_events(self, aggregate_type: str, aggregate_id: str, 
                        from_version: int = 0) -> List[Event]:
        """Get events for an aggregate from a specific version"""
        try:
            stream_key = f"event_stream:{aggregate_type}:{aggregate_id}"
            events = await self.redis_client.xrange(stream_key)
            
            result = []
            for event_id, fields in events:
                if fields.get("version", 0) > from_version:
                    event = Event.from_dict(fields)
                    result.append(event)
            
            return sorted(result, key=lambda x: x.version)
        except Exception as e:
            logger.error(f"Failed to get events for {aggregate_type}:{aggregate_id}: {e}")
            return []
    
    async def get_current_version(self, aggregate_type: str, aggregate_id: str) -> int:
        """Get current version of an aggregate"""
        try:
            version_key = f"version:{aggregate_type}:{aggregate_id}"
            version = await self.redis_client.get(version_key)
            return int(version) if version else 0
        except Exception as e:
            logger.error(f"Failed to get version for {aggregate_type}:{aggregate_id}: {e}")
            return 0

class EventBus:
    """Event bus for publishing and subscribing to events"""
    
    def __init__(self):
        self.producer = None
        self.consumers = {}
        self.event_handlers = {}
        self.admin_client = None
        self.executor = ThreadPoolExecutor(max_workers=10)
        
    def _get_producer(self) -> KafkaProducer:
        """Get Kafka producer instance"""
        if not self.producer:
            self.producer = KafkaProducer(
                bootstrap_servers=[settings.KAFKA_BOOTSTRAP_SERVERS],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',  # Wait for all replicas
                retries=3,
                max_in_flight_requests_per_connection=1,  # Ensure ordering
                enable_idempotence=True  # Prevent duplicate events
            )
        return self.producer
    
    def _get_admin_client(self) -> KafkaAdminClient:
        """Get Kafka admin client"""
        if not self.admin_client:
            self.admin_client = KafkaAdminClient(
                bootstrap_servers=[settings.KAFKA_BOOTSTRAP_SERVERS]
            )
        return self.admin_client
    
    async def initialize_topics(self):
        """Initialize Kafka topics"""
        try:
            admin = self._get_admin_client()
            topic_list = []
            
            for topic_name in KafkaTopics.get_all_topics():
                topic_list.append(NewTopic(
                    name=topic_name,
                    num_partitions=3,
                    replication_factor=1
                ))
            
            admin.create_topics(topic_list, validate_only=False)
            logger.info("Kafka topics initialized successfully")
        except TopicAlreadyExistsError:
            logger.info("Kafka topics already exist")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka topics: {e}")
    
    def _get_topic_for_event(self, event_type: EventType) -> str:
        """Map event type to Kafka topic"""
        topic_mapping = {
            EventType.SPOT_STATUS_CHANGED: KafkaTopics.PARKING_SPOTS,
            EventType.SPOT_OCCUPIED: KafkaTopics.PARKING_SPOTS,
            EventType.SPOT_VACATED: KafkaTopics.PARKING_SPOTS,
            EventType.SPOT_RESERVED: KafkaTopics.PARKING_SPOTS,
            EventType.SPOT_MAINTENANCE: KafkaTopics.PARKING_SPOTS,
            
            EventType.RESERVATION_CREATED: KafkaTopics.RESERVATIONS,
            EventType.RESERVATION_CONFIRMED: KafkaTopics.RESERVATIONS,
            EventType.RESERVATION_STARTED: KafkaTopics.RESERVATIONS,
            EventType.RESERVATION_EXTENDED: KafkaTopics.RESERVATIONS,
            EventType.RESERVATION_COMPLETED: KafkaTopics.RESERVATIONS,
            EventType.RESERVATION_CANCELLED: KafkaTopics.RESERVATIONS,
            EventType.RESERVATION_EXPIRED: KafkaTopics.RESERVATIONS,
            EventType.RESERVATION_NO_SHOW: KafkaTopics.RESERVATIONS,
            
            EventType.PAYMENT_INITIATED: KafkaTopics.PAYMENTS,
            EventType.PAYMENT_COMPLETED: KafkaTopics.PAYMENTS,
            EventType.PAYMENT_FAILED: KafkaTopics.PAYMENTS,
            EventType.PAYMENT_REFUNDED: KafkaTopics.PAYMENTS,
            
            EventType.USER_ARRIVED: KafkaTopics.USER_ACTIONS,
            EventType.USER_DEPARTED: KafkaTopics.USER_ACTIONS,
            EventType.USER_CHECK_IN: KafkaTopics.USER_ACTIONS,
            EventType.USER_CHECK_OUT: KafkaTopics.USER_ACTIONS,
            
            EventType.SYSTEM_ALERT: KafkaTopics.SYSTEM_EVENTS,
            EventType.CAPACITY_THRESHOLD: KafkaTopics.SYSTEM_EVENTS,
            EventType.SENSOR_UPDATE: KafkaTopics.SYSTEM_EVENTS,
            EventType.NOTIFICATION_SENT: KafkaTopics.NOTIFICATIONS,
        }
        
        return topic_mapping.get(event_type, KafkaTopics.SYSTEM_EVENTS)
    
    async def publish_event(self, event: Event) -> bool:
        """Publish event to Kafka topic"""
        try:
            producer = self._get_producer()
            topic = self._get_topic_for_event(event.event_type)
            
            # Use aggregate_id as key for partitioning
            key = f"{event.aggregate_type}:{event.aggregate_id}"
            
            future = producer.send(
                topic,
                value=event.to_dict(),
                key=key
            )
            
            # Wait for acknowledgment
            producer.flush()
            
            logger.info(f"Published event {event.event_id} to topic {topic}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish event {event.event_id}: {e}")
            return False
    
    def register_handler(self, event_type: EventType, handler: Callable):
        """Register event handler for specific event type"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    async def start_consumer(self, topics: List[str], group_id: str):
        """Start Kafka consumer for specified topics"""
        try:
            consumer = KafkaConsumer(
                *topics,
                bootstrap_servers=[settings.KAFKA_BOOTSTRAP_SERVERS],
                group_id=group_id,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                auto_commit_interval_ms=1000
            )
            
            self.consumers[group_id] = consumer
            
            # Start consuming in background
            loop = asyncio.get_event_loop()
            loop.run_in_executor(self.executor, self._consume_messages, consumer)
            
            logger.info(f"Started consumer for topics {topics} with group {group_id}")
            
        except Exception as e:
            logger.error(f"Failed to start consumer: {e}")
    
    def _consume_messages(self, consumer: KafkaConsumer):
        """Consume messages from Kafka"""
        try:
            for message in consumer:
                try:
                    event_data = message.value
                    event = Event.from_dict(event_data)
                    
                    # Execute event handlers
                    if event.event_type in self.event_handlers:
                        for handler in self.event_handlers[event.event_type]:
                            try:
                                asyncio.run(handler(event))
                            except Exception as e:
                                logger.error(f"Event handler failed for {event.event_id}: {e}")
                
                except Exception as e:
                    logger.error(f"Failed to process message: {e}")
                    # Send to dead letter queue
                    self._send_to_dead_letter_queue(message.value, str(e))
        
        except Exception as e:
            logger.error(f"Consumer error: {e}")
    
    def _send_to_dead_letter_queue(self, message: Dict[str, Any], error: str):
        """Send failed message to dead letter queue"""
        try:
            producer = self._get_producer()
            dead_letter_message = {
                "original_message": message,
                "error": error,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "retry_count": 0
            }
            
            producer.send(KafkaTopics.DEAD_LETTER, value=dead_letter_message)
            producer.flush()
            
        except Exception as e:
            logger.error(f"Failed to send to dead letter queue: {e}")
    
    def close(self):
        """Close all connections"""
        if self.producer:
            self.producer.close()
        
        for consumer in self.consumers.values():
            consumer.close()
        
        self.executor.shutdown(wait=True)

class EventService:
    """Main event service orchestrating event sourcing and streaming"""
    
    def __init__(self):
        self.event_store = EventStore()
        self.event_bus = EventBus()
        self.redis_client = get_redis_client()
    
    async def initialize(self):
        """Initialize event service"""
        await self.event_bus.initialize_topics()
        
        # Start consumers for different services
        await self.event_bus.start_consumer(
            [KafkaTopics.PARKING_SPOTS, KafkaTopics.RESERVATIONS],
            "parking-service"
        )
        
        await self.event_bus.start_consumer(
            [KafkaTopics.NOTIFICATIONS],
            "notification-service"
        )
        
        await self.event_bus.start_consumer(
            [KafkaTopics.PAYMENTS],
            "payment-service"
        )
    
    async def publish_event(self, event_type: EventType, aggregate_type: str,
                          aggregate_id: str, event_data: Dict[str, Any],
                          metadata: Optional[Dict[str, Any]] = None,
                          priority: EventPriority = EventPriority.NORMAL,
                          correlation_id: Optional[str] = None,
                          causation_id: Optional[str] = None) -> Event:
        """Publish a new event"""
        
        # Get current version and increment
        current_version = await self.event_store.get_current_version(
            aggregate_type, aggregate_id
        )
        new_version = current_version + 1
        
        # Create event
        event = Event(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            event_data=event_data,
            metadata=metadata or {},
            timestamp=datetime.now(timezone.utc),
            version=new_version,
            priority=priority,
            correlation_id=correlation_id,
            causation_id=causation_id
        )
        
        # Store in event store
        success = await self.event_store.append_event(event)
        if not success:
            raise Exception(f"Failed to store event {event.event_id}")
        
        # Publish to event bus
        publish_success = await self.event_bus.publish_event(event)
        if not publish_success:
            logger.warning(f"Failed to publish event {event.event_id} to Kafka")
        
        return event
    
    async def get_aggregate_events(self, aggregate_type: str, aggregate_id: str,
                                 from_version: int = 0) -> List[Event]:
        """Get all events for an aggregate"""
        return await self.event_store.get_events(aggregate_type, aggregate_id, from_version)
    
    def register_event_handler(self, event_type: EventType, handler: Callable):
        """Register event handler"""
        self.event_bus.register_handler(event_type, handler)
    
    async def replay_events(self, aggregate_type: str, aggregate_id: str,
                          to_version: Optional[int] = None) -> Dict[str, Any]:
        """Replay events to reconstruct aggregate state"""
        events = await self.event_store.get_events(aggregate_type, aggregate_id)
        
        if to_version:
            events = [e for e in events if e.version <= to_version]
        
        # This would be implemented by specific aggregate handlers
        # For now, just return the events
        return {
            "aggregate_type": aggregate_type,
            "aggregate_id": aggregate_id,
            "events": [e.to_dict() for e in events],
            "current_version": events[-1].version if events else 0
        }
    
    async def get_event_statistics(self) -> Dict[str, Any]:
        """Get event processing statistics"""
        try:
            stats = {}
            
            # Get count by event type
            for event_type in EventType:
                type_key = f"events_by_type:{event_type.value}"
                count = await self.redis_client.llen(type_key)
                stats[event_type.value] = count
            
            # Get total events processed today
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            daily_key = f"events_daily:{today}"
            daily_count = await self.redis_client.get(daily_key) or 0
            stats["daily_total"] = int(daily_count)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get event statistics: {e}")
            return {}
    
    def close(self):
        """Close event service"""
        self.event_bus.close()

# Global event service instance
event_service = EventService()
