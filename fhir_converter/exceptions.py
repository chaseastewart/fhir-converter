from typing import NoReturn, Optional


class RenderingError(Exception):
    """Raised when there is a rendering error"""

    def __init__(self, msg: str, cause: Optional[Exception] = None) -> None:
        super().__init__(msg)
        if cause:
            self.__cause__ = cause


def fail(e: Exception) -> NoReturn:
    """fail Raises the provided exception

    Args:
        e (Exception): the exception / failure reason

    Raises:
        Exception: The provided exception
    """
    raise e
