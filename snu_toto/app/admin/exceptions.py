from snu_toto.app.common.exceptions import SnutotoException

class SelfRoleChangeDeniedError(SnutotoException):
    def __init__(self):
        super().__init__(
            status_code=400,
            error_code="ERR_043",
            error_msg="SELF ROLE CHANGE DENIED"
        )

