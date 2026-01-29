from snu_toto.app.common.exceptions import SnutotoException

class EmailAlreadyExistsException(SnutotoException):
    def __init__(self):
        super().__init__(
            status_code=409,
            error_code="ERR_006",
            error_msg="EMAIL ALREADY EXISTS"
        )

class NicknameAlreadyExistsException(SnutotoException):
    def __init__(self):
        super().__init__(
            status_code=409,
            error_code="ERR_007",
            error_msg="NICKNAME ALREADY EXISTS"
        )

class OnlySnuEmailAllowedException(SnutotoException):
    def __init__(self):
        super().__init__(
            status_code=403,
            error_code="ERR_010", 
            error_msg="ONLY SNU EMAIL ALLOWED"
        )

class MissingPasswordException(SnutotoException):
    def __init__(self):
        super().__init__(
            status_code=400,
            error_code="ERR_016",
            error_msg="PASSWORD IS REQUIRED FOR LOCAL SIGNUP"
        )

class MissingSocialIdException(SnutotoException):
    def __init__(self):
        super().__init__(
            status_code=400,
            error_code="ERR_017",
            error_msg="SOCIAL ID IS REQUIRED FOR SOCIAL SIGNUP"
        )

class SocialIdAlreadyExistsException(SnutotoException):
    def __init__(self):
        super().__init__(
            status_code=409,
            error_code="ERR_018",
            error_msg="SOCIAL ID ALREADY EXISTS"
        )

class ForbiddenException(SnutotoException):
    def __init__(self):
        super().__init__(
            status_code=403,
            error_code="ERR_030",
            error_msg="NOT ADMIN"
        )

class UserNotFoundError(SnutotoException):
    def __init__(self):
        super().__init__(
            status_code=404,
            error_code="ERR_042",
            error_msg="USER NOT FOUND"
        )
    
class ReRegistrationLimitException(SnutotoException):
    def __init__(self, remaining_days: int):
        super().__init__(
            status_code=409,
            error_code="ERR_051",
            error_msg="WITHDRAWAL COOLDOWN PERIOD",
            detail= {
                "remaining_days": remaining_days
            }
        )