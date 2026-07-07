from services.database import db
from services.models import DocumentSession, DocumentFile, CodeSession, ChatSession, ProjectSession, ChatMessage

class DocumentSessionRepository:
    @staticmethod
    def get_by_id(session_id):
        return DocumentSession.query.get(session_id)

    @staticmethod
    def save(session):
        db.session.add(session)
        db.session.commit()
        return session

    @staticmethod
    def get_files_by_session_id(session_id):
        return DocumentFile.query.filter_by(session_id=session_id).all()

    @staticmethod
    def save_file(doc_file):
        db.session.add(doc_file)
        db.session.commit()
        return doc_file

class CodeSessionRepository:
    @staticmethod
    def get_by_id(session_id):
        return CodeSession.query.get(session_id)

    @staticmethod
    def save(session):
        db.session.add(session)
        db.session.commit()
        return session

class ChatSessionRepository:
    @staticmethod
    def get_by_id(session_id):
        return ChatSession.query.get(session_id)

    @staticmethod
    def save(session):
        db.session.add(session)
        db.session.commit()
        return session

class ProjectSessionRepository:
    @staticmethod
    def get_by_id(session_id):
        return ProjectSession.query.get(session_id)

    @staticmethod
    def save(session):
        db.session.add(session)
        db.session.commit()
        return session

class ChatMessageRepository:
    @staticmethod
    def get_by_id(message_id):
        return ChatMessage.query.get(message_id)

    @staticmethod
    def get_messages_by_session_id(session_id, limit=None):
        query = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.created_at.asc())
        if limit:
            # We fetch all, and take the slice since order_by is ascending and we want the *last* limit elements.
            # Using chat_history[-limit:] is the current code pattern.
            return query.all()
        return query.all()

    @staticmethod
    def save(message):
        db.session.add(message)
        db.session.commit()
        return message

    @staticmethod
    def delete_messages(session_id, exclude_message_id=None):
        query = ChatMessage.query.filter(ChatMessage.session_id == session_id)
        if exclude_message_id is not None:
            query = query.filter(ChatMessage.id != exclude_message_id)
        query.delete()
        db.session.commit()
