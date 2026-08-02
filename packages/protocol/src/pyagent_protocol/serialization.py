"""
CBOR serialization for the agent protocol.

Uses cbor2 for compact binary serialization, matching pi-mono's use of CBOR
in packages/protocol. Falls back to JSON when cbor2 is unavailable.
"""

from __future__ import annotations

from typing import Any

try:
    import cbor2

    _HAS_CBOR = True
except ImportError:
    _HAS_CBOR = False


def serialize(obj: Any) -> bytes:
    """Serialize a Pydantic model or dict to CBOR bytes."""
    if hasattr(obj, "model_dump"):
        data = obj.model_dump(mode="python")
    elif isinstance(obj, dict):
        data = obj
    else:
        data = obj

    if _HAS_CBOR:
        return cbor2.dumps(data)
    else:
        import json

        return json.dumps(data, default=str).encode("utf-8")


def deserialize(data: bytes, model_cls: type | None = None) -> Any:
    """Deserialize CBOR bytes. Optionally coerce into a Pydantic model."""
    if _HAS_CBOR:
        result = cbor2.loads(data)
    else:
        import json

        result = json.loads(data.decode("utf-8"))

    if model_cls is not None and hasattr(model_cls, "model_validate"):
        return model_cls.model_validate(result)
    return result
