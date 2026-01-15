"""
Message Consumer - Processes incoming interactions from the message queue
"""

import asyncio
import json
from typing import Optional
from uuid import UUID

import aio_pika
import structlog
from aio_pika.abc import AbstractIncomingMessage

from src.config import settings
from src.core.agent_manager import AgentManager

logger = structlog.get_logger()


class MessageConsumer:
    """
    Consumes messages from RabbitMQ and routes them to the appropriate agent.
    """

    def __init__(self, agent_manager: AgentManager):
        self.agent_manager = agent_manager
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.queue: Optional[aio_pika.Queue] = None
        self._running = False

    async def start(self):
        """Start consuming messages"""
        logger.info("Starting message consumer")

        try:
            # Connect to RabbitMQ
            self.connection = await aio_pika.connect_robust(
                settings.rabbitmq_url,
                loop=asyncio.get_event_loop()
            )

            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=10)

            # Declare queue
            self.queue = await self.channel.declare_queue(
                "agent_interactions",
                durable=True
            )

            # Declare exchange
            exchange = await self.channel.declare_exchange(
                "vibber_events",
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )

            # Bind queue to exchange
            await self.queue.bind(exchange, routing_key="interaction.*")

            self._running = True

            # Start consuming
            async with self.queue.iterator() as queue_iter:
                async for message in queue_iter:
                    if not self._running:
                        break
                    await self._process_message(message)

        except Exception as e:
            logger.error(f"Message consumer error: {e}")
            raise

    async def stop(self):
        """Stop consuming messages"""
        logger.info("Stopping message consumer")
        self._running = False

        if self.connection:
            await self.connection.close()

    async def _process_message(self, message: AbstractIncomingMessage):
        """Process a single message"""
        async with message.process():
            try:
                # Parse message body
                body = json.loads(message.body.decode())

                logger.info(
                    "Processing message",
                    message_id=message.message_id,
                    routing_key=message.routing_key
                )

                # Extract agent and user IDs
                agent_id = UUID(body.get("agent_id"))
                user_id = UUID(body.get("user_id"))

                # Build interaction data
                interaction_data = {
                    "provider": body.get("provider"),
                    "interaction_type": body.get("interaction_type"),
                    "input_data": body.get("input_data", {}),
                    "integration_id": body.get("integration_id"),
                    "external_ref": body.get("external_ref")
                }

                # Process through agent manager
                result = await self.agent_manager.process_interaction(
                    agent_id=agent_id,
                    user_id=user_id,
                    interaction_data=interaction_data
                )

                # Publish result
                await self._publish_result(body, result)

                logger.info(
                    "Message processed",
                    message_id=message.message_id,
                    status=result.get("status")
                )

            except Exception as e:
                logger.error(
                    f"Failed to process message: {e}",
                    message_id=message.message_id
                )
                # Message will be requeued due to exception

    async def _publish_result(self, original: dict, result: dict):
        """Publish processing result back to the queue"""
        if not self.channel:
            return

        exchange = await self.channel.declare_exchange(
            "vibber_events",
            aio_pika.ExchangeType.TOPIC,
            durable=True
        )

        result_message = {
            "interaction_id": original.get("id"),
            "agent_id": original.get("agent_id"),
            "result": result
        }

        routing_key = f"result.{result.get('status', 'unknown')}"

        await exchange.publish(
            aio_pika.Message(
                body=json.dumps(result_message).encode(),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=routing_key
        )


class RedisMessageConsumer:
    """
    Alternative consumer using Redis pub/sub for simpler deployments.
    """

    def __init__(self, agent_manager: AgentManager):
        self.agent_manager = agent_manager
        self._running = False

    async def start(self):
        """Start consuming from Redis pub/sub"""
        import redis.asyncio as redis

        logger.info("Starting Redis message consumer")

        client = redis.from_url(settings.redis_url)
        pubsub = client.pubsub()

        await pubsub.subscribe("agent:interactions")

        self._running = True

        while self._running:
            try:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0
                )

                if message and message["type"] == "message":
                    await self._process_redis_message(message["data"])

            except Exception as e:
                logger.error(f"Redis consumer error: {e}")
                await asyncio.sleep(1)

        await pubsub.unsubscribe("agent:interactions")
        await client.close()

    async def stop(self):
        """Stop consuming"""
        self._running = False

    async def _process_redis_message(self, data: bytes):
        """Process message from Redis"""
        try:
            body = json.loads(data.decode())

            agent_id = UUID(body.get("agent_id"))
            user_id = UUID(body.get("user_id"))

            interaction_data = {
                "provider": body.get("provider"),
                "interaction_type": body.get("interaction_type"),
                "input_data": body.get("input_data", {})
            }

            result = await self.agent_manager.process_interaction(
                agent_id=agent_id,
                user_id=user_id,
                interaction_data=interaction_data
            )

            logger.info("Redis message processed", status=result.get("status"))

        except Exception as e:
            logger.error(f"Failed to process Redis message: {e}")
