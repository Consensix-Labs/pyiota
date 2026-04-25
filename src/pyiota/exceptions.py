"""pyiota exception hierarchy.

All SDK exceptions inherit from IotaError so callers can catch broadly
or narrowly as needed.
"""


class IotaError(Exception):
    """Base exception for all pyiota errors."""


class RpcError(IotaError):
    """The JSON-RPC endpoint returned an error response."""

    def __init__(self, code: int, message: str, data: object = None) -> None:
        self.code = code
        self.rpc_message = message
        self.data = data
        super().__init__(f"RPC error {code}: {message}")


class TransactionError(IotaError):
    """Transaction execution failed on-chain."""


class SigningError(IotaError):
    """Signature creation or verification failed."""


class SerializationError(IotaError):
    """BCS encoding or decoding failed."""


class ObjectNotFoundError(IotaError):
    """Requested object does not exist on-chain."""

    def __init__(self, object_id: str) -> None:
        self.object_id = object_id
        super().__init__(f"Object not found: {object_id}")
