from snu_toto.app.common.exceptions import SnutotoException

class EventNotFoundError(SnutotoException):
    def __init__(self) -> None:
        super().__init__(status_code=404, error_code="ERR_009", error_msg="EVENT NOT FOUND")

class InvalidDateError(SnutotoException):
    def __init__(self) -> None:
        super().__init__(status_code=400, error_code="ERR_023", error_msg="INVALID DATE")

class InvalidOptionCountError(SnutotoException):
    def __init__(self) -> None:
        super().__init__(status_code=400, error_code="ERR_024", error_msg="INSUFFICIENT/TOO MANY OPTIONS")

class InvalidOptionNameError(SnutotoException):
    def __init__(self) -> None:
        super().__init__(status_code=400, error_code="ERR_025", error_msg="INVALID OPTION NAME")

class DuplicateOptionNameError(SnutotoException):
    def __init__(self) -> None:
        super().__init__(status_code=409, error_code="ERR_028", error_msg="DUPLICATE OPTION NAME")

class InvalidStatusTransitionError(SnutotoException):
    def __init__(self) -> None:
        super().__init__(status_code=400, error_code="ERR_029", error_msg="INVALID STATUS TRANSITION")

class NotAdminError(SnutotoException):
    def __init__(self) -> None:
        super().__init__(status_code=403, error_code="ERR_030", error_msg="NOT ADMIN")

# --- 이미지 관련 ---
class ImageTooLargeError(SnutotoException):
    def __init__(self) -> None:
        super().__init__(status_code=413, error_code="ERR_026", error_msg="IMAGE TOO LARGE")

class ImageUploadFailedError(SnutotoException):
    def __init__(self) -> None:
        super().__init__(status_code=500, error_code="ERR_027", error_msg="FAILED TO UPLOAD IMAGE")

class InvalidContentTypeError(SnutotoException):
    def __init__(self) -> None:
        super().__init__(status_code=415, error_code="ERR_033", error_msg="INVALID CONTENT TYPE")

class ImageIndexOutOfBoundsError(SnutotoException):
    def __init__(self) -> None:
        super().__init__(status_code=400, error_code="ERR_034", error_msg="IMAGE INDEX OUT OF BOUNDS")

class InvalidImageFormatError(SnutotoException):
    def __init__(self) -> None:
        super().__init__(status_code=415, error_code="ERR_035", error_msg="INVALID IMAGE FORMAT")

class OutOfRangeError(SnutotoException):
    def __init__(self) -> None:
        super().__init__(status_code=422, error_code="ERR_036", error_msg="OUT_OF_RANGE")

class InvalidCursorError(SnutotoException):
    def __init__(self) -> None:
        super().__init__(status_code=404, error_code="ERR_037", error_msg="INVALID_CURSOR")