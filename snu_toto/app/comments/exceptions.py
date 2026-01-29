from snu_toto.app.common.exceptions import SnutotoException

class EmptyCommentContentException(SnutotoException):
    """댓글 내용이 공백만으로 구성됨"""
    def __init__(self):
        super().__init__(
            status_code=400,
            error_code="ERR_048",
            error_msg="EMPTY COMMENT CONTENT"
        )

class InvalidCursorException(SnutotoException):
    """유효하지 않은 커서 형식"""
    def __init__(self):
        super().__init__(
            status_code=404,
            error_code="ERR_037",
            error_msg="INVALID_CURSOR"
        )
