import http
import logging

logger = logging.getLogger('uvicorn.error')


class SnutotoException(Exception):
    def __init__(
        self,
        status_code: int = 500,
        error_code: str = "ERR_000",
        error_msg: str = "Unexpected error occurred",
        payload: dict = None,
        detail: dict = None
    ):
        if not isinstance(status_code, int) or status_code not in http.HTTPStatus.__members__.values():
            logger.critical(f"Invalid status_code {status_code} provided to SnutotoException, defaulting to 500")
            self.status_code = 500
        else:
            self.status_code = status_code
            
        if not isinstance(error_code, str):
            logger.critical(f"Invalid error_code {str(error_code)} provided to SnutotoException,"
                            " defaulting to 'ERROR_000'")
            self.error_code = "ERR_000"
        else:
            self.error_code = error_code

        if not isinstance(error_msg, str):
            self.error_msg = http.HTTPStatus(self.status_code).description
            logger.critical(f"Invalid error_msg {str(error_msg)} provided to SnutotoException,"
                            f" defaulting to '{self.error_msg}'")
        else:
            self.error_msg = error_msg
        
        if payload is not None and not isinstance(payload, dict):
            logger.error(f"Invalid payload type {type(payload)} provided, expected dict. Defaulting to empty dict.")
            self.payload = {}
        else:
            self.payload = payload or {} # None이면 빈 딕셔너리로 초기화
        
        if detail is not None and not isinstance(detail, dict):
            logger.error(f"Invalid detail type {type(detail)} provided, expected dict. Defaulting to empty dict.")
            self.detail = {}
        else:
            self.detail = detail or {} # None이면 빈 딕셔너리로 초기화


class MissingRequiredFieldException(SnutotoException):
    def __init__(self):
        super().__init__(
            status_code=400,
            error_code="ERR_001",
            error_msg="MISSING REQUIRED FIELDS"
        )

class InvalidFormatException(SnutotoException):
    def __init__(self):
        super().__init__(
            status_code=400,
            error_code="ERR_002",
            error_msg="INVALID FIELD FORMAT"
        )