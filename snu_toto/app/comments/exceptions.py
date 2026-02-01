from snu_toto.app.common.exceptions import SnutotoException


class CommentNotFoundError(SnutotoException):
    """댓글을 찾을 수 없음"""
    def __init__(self) -> None:
        super().__init__(status_code=404, error_code="ERR_040", error_msg="COMMENT NOT FOUND")


class CommentPermissionDeniedError(SnutotoException):
    """댓글 수정/삭제 권한 없음"""
    def __init__(self) -> None:
        super().__init__(status_code=403, error_code="ERR_041", error_msg="COMMENT PERMISSION DENIED")


class EmptyCommentContentError(SnutotoException):
    """댓글 내용이 공백만으로 구성됨"""
    def __init__(self) -> None:
        super().__init__(status_code=400, error_code="ERR_048", error_msg="EMPTY COMMENT CONTENT")


class InvalidCursorError(SnutotoException):
    """유효하지 않은 커서"""
    def __init__(self) -> None:
        super().__init__(status_code=404, error_code="ERR_037", error_msg="INVALID_CURSOR")


class CommentNotFoundForUpdateError(SnutotoException):
    """댓글을 찾을 수 없음 (수정/삭제용)"""
    def __init__(self) -> None:
        super().__init__(status_code=404, error_code="ERR_049", error_msg="COMMENT NOT FOUND")


class NotCommentOwnerError(SnutotoException):
    """댓글 작성자가 아님"""
    def __init__(self) -> None:
        super().__init__(status_code=403, error_code="ERR_050", error_msg="NOT COMMENT OWNER")
