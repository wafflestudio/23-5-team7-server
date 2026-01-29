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

class CommentNotFoundException(SnutotoException):
    """댓글을 찾을 수 없을 때"""
    def __init__(self):
        super().__init__(
            status_code=404,
            error_code="ERR_049",
            error_msg="COMMENT NOT FOUND"
        )

class NotCommentOwnerException(SnutotoException):
    """댓글 작성자가 아닐 때"""
    def __init__(self):
        super().__init__(
            status_code=403,
            error_code="ERR_050",
            error_msg="NOT COMMENT OWNER"
        )
