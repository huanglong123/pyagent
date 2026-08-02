"""
SQLite session store — CRUD operations for agent sessions.

Provides a SessionStore class that wraps SQLModel for persisting and
retrieving agent sessions. Mirrors pi-mono's SessionStore in
packages/storage.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, SQLModel, create_engine, select

from pyagent_storage.models import SessionRecord, MessageRecord, ToolResultRecord


class SessionStore:
    """SQLite-backed session store.

    Usage:
        store = SessionStore("sessions.db")
        store.save_session(session_id, messages=[...])
        messages = store.load_session(session_id)
    """

    def __init__(self, db_path: str | None = None) -> None:
        if db_path is None:
            db_path = os.environ.get("PYAGENT_DB_PATH", ".pyagent/sessions.db")

        # Ensure directory exists
        dirname = os.path.dirname(db_path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)

        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        SQLModel.metadata.create_all(self.engine)

    def save_session(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
        system_prompt: str | None = None,
        model_provider: str = "openai",
        model_name: str = "gpt-4o-mini",
        temperature: float = 0.7,
    ) -> None:
        """Save or update a session with all messages."""
        with Session(self.engine) as session:
            # Check if session exists
            existing = session.get(SessionRecord, session_id)
            if existing:
                # Delete old messages
                old_msgs = session.exec(
                    select(MessageRecord).where(MessageRecord.session_id == session_id)
                ).all()
                for msg in old_msgs:
                    session.delete(msg)
                existing.updated_at = datetime.now(timezone.utc)
                session.add(existing)
            else:
                record = SessionRecord(
                    id=session_id,
                    system_prompt=system_prompt,
                    model_provider=model_provider,
                    model_name=model_name,
                    temperature=temperature,
                )
                session.add(record)

            # Insert messages
            for seq, msg in enumerate(messages):
                msg_record = MessageRecord(
                    session_id=session_id,
                    role=msg.get("role", "user"),
                    content=msg.get("content", ""),
                    name=msg.get("name"),
                    tool_call_id=msg.get("tool_call_id"),
                    seq=seq,
                )
                session.add(msg_record)

            session.commit()

    def load_session(self, session_id: str) -> list[dict[str, Any]]:
        """Load all messages for a session, ordered by sequence."""
        with Session(self.engine) as session:
            records = session.exec(
                select(MessageRecord)
                .where(MessageRecord.session_id == session_id)
                .order_by(MessageRecord.seq)
            ).all()

            messages = []
            for rec in records:
                msg: dict[str, Any] = {
                    "role": rec.role,
                    "content": rec.content,
                }
                if rec.name:
                    msg["name"] = rec.name
                if rec.tool_call_id:
                    msg["tool_call_id"] = rec.tool_call_id
                messages.append(msg)

            return messages

    def list_sessions(self) -> list[SessionRecord]:
        """List all stored sessions."""
        with Session(self.engine) as session:
            return list(session.exec(select(SessionRecord)).all())

    def delete_session(self, session_id: str) -> None:
        """Delete a session and all its messages."""
        with Session(self.engine) as session:
            record = session.get(SessionRecord, session_id)
            if record:
                session.delete(record)

            msgs = session.exec(
                select(MessageRecord).where(MessageRecord.session_id == session_id)
            ).all()
            for msg in msgs:
                session.delete(msg)

            results = session.exec(
                select(ToolResultRecord).where(ToolResultRecord.session_id == session_id)
            ).all()
            for result in results:
                session.delete(result)

            session.commit()

    def save_tool_result(
        self,
        session_id: str,
        tool_call_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        result: str,
        is_error: bool = False,
    ) -> None:
        """Save a tool execution result."""
        with Session(self.engine) as session:
            record = ToolResultRecord(
                session_id=session_id,
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                arguments=json.dumps(arguments),
                result=result,
                is_error=is_error,
            )
            session.add(record)
            session.commit()
