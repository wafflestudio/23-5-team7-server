from snu_toto.app.common.exceptions import SnutotoException

class EventNotFoundError(SnutotoException):
    def __init__(self) -> None:
        super().__init__(status_code=404, error_code="ERR_009", error_msg="EVENT NOT FOUND")

class InsufficientBalanceError(SnutotoException):
    def __init__(self) -> None:
        super().__init__(status_code=400, error_code="ERR_038", error_msg="INSUFFICIENT BALANCE")

class OptionNotFoundError(SnutotoException):
    def __init__(self) -> None:
        super().__init__(status_code=404, error_code="ERR_039", error_msg="OPTION NOT FOUND")

class EventNotOpenError(SnutotoException):
    def __init__(self) -> None:
        super().__init__(status_code=409, error_code="ERR_040", error_msg="EVENT NOT OPEN")

class DuplicateBetError(SnutotoException):
    def __init__(self) -> None:
        super().__init__(status_code=409, error_code="ERR_041", error_msg="DUPLICATE BET")