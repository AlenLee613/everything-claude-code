from fastapi import HTTPException, status

class EphemeralKeyException(HTTPException):
    def __init__(self, status_code: int, error_code: str, message: str):
        super().__init__(
            status_code=status_code,
            detail={
                "error_code": error_code,
                "message": message
            }
        )

class KeyInvalidException(EphemeralKeyException):
    def __init__(self, message: str = "Key not found or expired"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="EPHEMERAL_KEY_INVALID",
            message=message
        )

class KeyExpiredOrLimitExceededException(EphemeralKeyException):
    def __init__(self, message: str = "Key expired or usage limit exceeded"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="EPHEMERAL_KEY_INVALID",
            message=message
        )
