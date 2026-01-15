from snu_toto.app.common.exceptions import SnutotoException

# 이벤트를 찾을 수 없는 경우
class EventNotFoundError(SnutotoException):
    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            error_code="ERR_010",
            error_msg="EVENT NOT FOUND"
        )

# 사용자의 잔액이 부족한 경우
class InsufficientBalanceError(SnutotoException):
    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            error_code="ERR_011",
            error_msg="INSUFFICIENT BALANCE"
        )

# 선택한 옵션을 찾을 수 없는 경우
class OptionNotFoundError(SnutotoException):
    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            error_code="ERR_012",
            error_msg="OPTION NOT FOUND"
        )

# 이벤트가 OPEN 상태가 아닌 경우
class EventNotOpenError(SnutotoException):
    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            error_code="ERR_013",
            error_msg="EVENT NOT OPEN"
        )

# 사용자가 이미 해당 이벤트에 베팅한 경우
class DuplicateBetError(SnutotoException):
    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            error_code="ERR_014",
            error_msg="DUPLICATE BET"
        )