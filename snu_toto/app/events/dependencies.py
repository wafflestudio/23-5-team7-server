from typing import Annotated
from fastapi import Depends
from redis.asyncio import Redis
from snu_toto.app.auth.dependencies import get_redis
from snu_toto.app.events.repositories import EventRepositories
from snu_toto.app.events.services import EventServices

def get_event_service(
    repo: Annotated[EventRepositories, Depends()],
    redis: Annotated[Redis, Depends(get_redis)]
) -> EventServices:
    return EventServices(repo, redis)