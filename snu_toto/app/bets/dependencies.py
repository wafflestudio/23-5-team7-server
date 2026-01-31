from typing import Annotated
from fastapi import Depends
from snu_toto.app.bets.repositories import BetRepositories
from snu_toto.app.bets.services import BetServices
from snu_toto.app.events.dependencies import get_event_service
from snu_toto.app.events.services import EventServices

def get_bet_service(
    bet_repositories: Annotated[BetRepositories, Depends()],
    event_service: Annotated[EventServices, Depends(get_event_service)]
) -> BetServices:
    return BetServices(
        bet_repositories=bet_repositories,
        event_service=event_service
    )