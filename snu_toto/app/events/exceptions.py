from app.common.exceptions import SnutotoException

class EventNotFoundError(SnutotoException):
    def __init__(self) -> None:
        super().__init__(status_code=404, error_code="ERR_009", error_msg="EVENT NOT FOUND")