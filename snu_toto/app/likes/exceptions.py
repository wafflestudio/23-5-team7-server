from snu_toto.app.common.exceptions import SnutotoException


class LikeAlreadyExistsException(SnutotoException):
    """이미 좋아요를 누른 경우"""
    def __init__(self):
        super().__init__(
            status_code=409,
            error_code="ERR_052",
            error_msg="LIKE ALREADY EXISTS"
        )


class LikeNotFoundException(SnutotoException):
    """좋아요를 누르지 않은 경우"""
    def __init__(self):
        super().__init__(
            status_code=404,
            error_code="ERR_053",
            error_msg="LIKE NOT FOUND"
        )
