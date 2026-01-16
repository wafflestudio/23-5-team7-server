from typing import Annotated
from fastapi import Depends
from snu_toto.app.bets.repositories import BetRepositories
from snu_toto.app.bets.services import BetServices

def get_bet_service(
    bet_repositories: Annotated[BetRepositories, Depends()]
) -> BetServices:
    return BetServices(bet_repositories=bet_repositories)