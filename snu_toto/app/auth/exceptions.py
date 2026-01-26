from datetime import datetime
from snu_toto.app.common.exceptions import SnutotoException

class BadAuthHeaderException(SnutotoException):
    def __init__(self):
        super().__init__(
            status_code=400,
            error_code="ERR_003",
            error_msg="BAD AUTHORIZATION HEADER"
        )

class UnauthenticatedException(SnutotoException):
    def __init__(self):
        super().__init__(
            status_code=401,
            error_code="ERR_004",
            error_msg="UNAUTHENTICATED"
        )

class InvalidTokenException(SnutotoException):
    def __init__(self):
        super().__init__(
            status_code=401,
            error_code="ERR_005",
            error_msg="INVALID TOKEN"
        )

class AlreadyVerifiedException(SnutotoException):
    def __init__(self):
        super().__init__(
            status_code=400,
            error_code="ERR_011",
            error_msg="EMAIL ALREADY VERIFIED"
        )

class InvalidCodeException(SnutotoException):
    def __init__(self):
        super().__init__(
            status_code=400,
            error_code="ERR_012",
            error_msg="INVALID VERIFICATION CODE"
        )
        
class EmailSendFailedException(SnutotoException):
    def __init__(self):
        super().__init__(
            status_code=500,
            error_code="ERR_013",
            error_msg="FAILED TO SEND EMAIL"
        )

class InvalidCredentialsException(SnutotoException):
    def __init__(self):
        super().__init__(
            status_code=401,
            error_code="ERR_014",
            error_msg="INVALID CREDENTIALS"
        )

class EmailVerificationRequiredException(SnutotoException):
    def __init__(self, verification_token: str):
        super().__init__(
            status_code=403,
            error_code="ERR_015",
            error_msg="EMAIL VERIFICATION REQUIRED",
            payload={"verification_token": verification_token}
        )

class GoogleAuthFailedException(SnutotoException):
    def __init__(self):
        super().__init__(
            status_code=400,
            error_code="ERR_019",
            error_msg="GOOGLE AUTH FAILED"
        )

class MissingCodeException(SnutotoException):
    def __init__(self):
        super().__init__(
            status_code=400,
            error_code="ERR_020",
            error_msg="INVALID CALLBACK REQUEST"
        )

class RateLimitException(SnutotoException):
    def __init__(self):
        super().__init__(
            status_code=429,
            error_code="ERR_021",
            error_msg="TOO MANY REQUESTS"
        )

class SuspendedUserException(SnutotoException):
    def __init__(self, suspension_reason: str, suspended_until: datetime):
        super().__init__(
            status_code=403,
            error_code="ERR_046",
            error_msg="USER SUSPENDED",
            detail= {
                "suspension_reason": suspension_reason,
                "suspended_until": suspended_until
            }
        )
