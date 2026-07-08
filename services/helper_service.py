import os
import json
import config
from services.models import ChatMessage
from services.repositories import ChatMessageRepository

def get_lang_instruction(language):
    return "Respond in English." if language == "en" else "Respond in Vietnamese."

def format_sse_event(event_type, **kwargs):
    payload = json.dumps({'type': event_type, **kwargs})
    padding = ":" + " " * 1024 + "\n"
    return f"data: {payload}\n\n{padding}"

def retrieve_chat_history(session_id, limit, skip_first=False):
    """Retrieve the last N chat messages for a session."""
    if skip_first:
        first_msg = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.created_at.asc()).first()
        if not first_msg:
            return []
        first_id = first_msg.id
        
        # Fetch limit + 1 messages to ensure we get up to `limit` messages after skipping the first one
        recent = ChatMessageRepository.get_messages_by_session_id(session_id, limit=limit + 1)
        recent = [msg for msg in recent if msg.id != first_id][-limit:]
    else:
        recent = ChatMessageRepository.get_messages_by_session_id(session_id, limit=limit)
        
    return [{"role": msg.role, "content": msg.content} for msg in recent]

def save_chat_message(session_id, role, content):
    """Helper to save a message in the database."""
    msg = ChatMessage(session_id=session_id, role=role, content=content)
    return ChatMessageRepository.save(msg)

def safe_join_project_path(base_path: str, relative_path: str) -> str:
    """Joins base_path and relative_path and verifies that the resulting path is inside base_path."""
    if not relative_path:
        raise ValueError("Relative path is empty")
    base_abs = os.path.abspath(base_path)
    joined_path = os.path.join(base_abs, relative_path)
    target_abs = os.path.abspath(joined_path)
    
    prefix = base_abs if base_abs.endswith(os.path.sep) else base_abs + os.path.sep
    if not target_abs.startswith(prefix) and target_abs != base_abs:
        raise ValueError("Invalid path: Path traversal detected")
        
    return target_abs


