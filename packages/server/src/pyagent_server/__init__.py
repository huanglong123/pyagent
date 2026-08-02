"""
pyagent-server: FastAPI session server.

Mirrors pi-mono's packages/server — provides an HTTP server that
manages agent sessions, exposes REST endpoints for creating and
continuing sessions, and supports streaming responses.
"""

from pyagent_server.app import create_app, app

__all__ = ["create_app", "app"]
