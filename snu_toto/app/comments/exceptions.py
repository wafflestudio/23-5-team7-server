from snu_toto.app.common.exceptions import SnutotoException

class EmptyCommentContentException(SnutotoException):
    """댓글 내용이 공백만으로 구성됨"""
    def __init__(self):
        super().__init__(
            status_code=400,
            error_code="ERR_048",
            error_msg="EMPTY COMMENT CONTENT"
        )
