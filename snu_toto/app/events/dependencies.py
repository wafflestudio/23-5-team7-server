from typing import Annotated
from fastapi import Depends
from snu_toto.app.events.repositories import EventRepositories
from snu_toto.app.events.services import EventServices

def get_event_service(
    repo: Annotated[EventRepositories, Depends()]
) -> EventServices:
    return EventServices(repo)