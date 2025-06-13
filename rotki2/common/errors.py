"""Common error types for rotki2"""


class Rotki2Error(Exception):
    """Base exception for all rotki2 errors"""
    pass


class AuthenticationError(Rotki2Error):
    """Authentication related errors"""
    pass


class InputError(Rotki2Error):
    """Invalid input errors"""
    pass


class RemoteError(Rotki2Error):
    """Remote API/service errors"""
    pass


class PriceError(Rotki2Error):
    """Price query errors"""
    pass


class NoPriceError(PriceError):
    """No price found error"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class AccountingError(Rotki2Error):
    """Accounting related errors"""
    pass


class DatabaseError(Rotki2Error):
    """Database operation errors"""
    pass