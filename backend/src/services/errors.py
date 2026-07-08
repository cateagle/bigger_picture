class ConflictError(Exception):
    """Raised by a service create_* function when db.flush() hits a uniqueness/FK violation."""


class SameDiveError(Exception):
    """Raised when the two images passed to a pair/candidate service don't share a dive."""
