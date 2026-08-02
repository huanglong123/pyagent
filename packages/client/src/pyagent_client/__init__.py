"""
pyagent-client: Async remote session client (httpx).

Mirrors pi-mono's packages/client — provides an HTTP client for
communicating with a remote pyagent-server instance.
"""

from pyagent_client.session import RemoteSession

__all__ = ["RemoteSession"]
