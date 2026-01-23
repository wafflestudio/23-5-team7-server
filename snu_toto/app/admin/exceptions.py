from snu_toto.app.common.exceptions import SnutotoException

class SelfRoleChangeDeniedError(SnutotoException):
    def __init__(self):
        super().__init__(
            status_code=400,
            error_code="ERR_043",
            error_msg="SELF ROLE CHANGE DENIED"
        )

class SelfSuspensionDeniedError(SnutotoException):
    def __init__(self):
        super().__init__(
            status_code=400,
            error_code="ERR_044",
            error_msg="SELF SUSPENSION DENIED"
        )

class AlreadySuspendedError(SnutotoException):
    def __init__(self):
        super().__init__(
            status_code=400,
            error_code="ERR_045",
            error_msg="ALREADY SUSPENDED"
        )