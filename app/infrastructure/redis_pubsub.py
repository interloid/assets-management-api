import json

from redis.asyncio import Redis

ASSET_FILE_EVENTS_CHANNEL = "asset_file_events"


class RedisEventPublisher:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def publish(
        self,
        *,
        event: str,
        data: dict[str, str],
    ) -> None:
        payload = {
            "event": event,
            **data,
        }

        await self.redis.publish(
            ASSET_FILE_EVENTS_CHANNEL,
            json.dumps(payload),
        )
