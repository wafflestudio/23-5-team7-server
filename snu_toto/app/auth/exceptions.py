from snu_toto.app.common.exceptions import SnutotoException

class MissingCodeException(SnutotoException):
    def __init__(self):
        super().__init__(
            status_code=400,
            error_code="ERR_019",
            error_msg="INVALID CALLBACK REQUEST"
        )


class GoogleAuthFailedException(SnutotoException):
    def __init__(self):
        super().__init__(
            status_code=400,
            error_code="ERR_020",
            error_msg="GOOGLE AUTH FAILED"
        )
