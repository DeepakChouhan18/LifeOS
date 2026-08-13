"""
ORM-based CRUD operations for the Study module.
Includes full Create, Read, Update, Delete (CRUD) capabilities.
"""

from datetime import datetime, date, timezone
from database.models import Subject, StudyTask, StudySession
from utils import validation


def get_or_create_subject(session, user_id: int, name: str, color: str = "#4A90D9") -> Subject:
    subject = (
        session.query(Subject)
        .filter_by(user_id=user_id, name=name)
        .first()
    )
    if subject:
        return subject
    subject = Subject(user_id=user_id, name=name, color=color)
    session.add(subject)
    session.commit()
    return subject


def add_subject(session, user_id: int, name: str, color: str = "#4A90D9") -> Subject:
    return get_or_create_subject(session, user_id, name, color)


def delete_subject(session, subject_id: int):
    subject = session.get(Subject, subject_id)
    if subject:
        session.delete(subject)
        session.commit()
        return True
    return False


def list_subjects(session, user_id: int):
    return session.query(Subject).filter_by(user_id=user_id).order_by(Subject.name).all()


# --- Tasks ---

def add_task(
    session, user_id: int, title: str, subject_id: int = None,
    due_date: date = None, priority: str = "medium", topic: str = None
) -> StudyTask:
    validation.validate_nonempty_string(title, "Task title")
    task = StudyTask(
        user_id=user_id,
        subject_id=subject_id,
        title=title,
        priority=priority or "medium",
        topic=topic,
        due_date=due_date,
        is_completed=False,
    )
    session.add(task)
    session.commit()
    return task


def update_task(
    session, task_id: int, title: str = None, subject_id: int = None,
    due_date: date = None, priority: str = None, topic: str = None
) -> StudyTask:
    task = session.get(StudyTask, task_id)
    if task:
        if title is not None:
            task.title = title
        if subject_id is not None:
            task.subject_id = subject_id
        if due_date is not None:
            task.due_date = due_date
        if priority is not None:
            task.priority = priority
        if topic is not None:
            task.topic = topic
        session.commit()
    return task


def complete_task(session, task_id: int):
    task = session.get(StudyTask, task_id)
    if task:
        task.is_completed = True
        task.completed_at = datetime.now(timezone.utc)
        session.commit()
    return task


def uncomplete_task(session, task_id: int):
    task = session.get(StudyTask, task_id)
    if task:
        task.is_completed = False
        task.completed_at = None
        session.commit()
    return task


def delete_task(session, task_id: int) -> bool:
    task = session.get(StudyTask, task_id)
    if task:
        session.delete(task)
        session.commit()
        return True
    return False


def list_tasks(session, user_id: int, include_completed: bool = True):
    query = session.query(StudyTask).filter_by(user_id=user_id)
    if not include_completed:
        query = query.filter_by(is_completed=False)
    return query.order_by(StudyTask.is_completed.asc(), StudyTask.due_date.asc().nullslast()).all()


# --- Sessions ---

def log_session(
    session, user_id: int, subject_id: int, duration_minutes: int,
    session_date: date = None, topic: str = None, notes: str = None
) -> StudySession:
    validation.validate_duration_minutes(duration_minutes, "Session duration")
    validation.validate_not_future_date(session_date, "Session date")
    study_session = StudySession(
        user_id=user_id,
        subject_id=subject_id,
        session_date=session_date or date.today(),
        duration_minutes=duration_minutes,
        topic=topic,
        notes=notes,
    )
    session.add(study_session)
    session.commit()
    return study_session


def update_session(
    session, session_id: int, subject_id: int = None,
    duration_minutes: int = None, session_date: date = None,
    topic: str = None, notes: str = None
) -> StudySession:
    s = session.get(StudySession, session_id)
    if s:
        if subject_id is not None:
            s.subject_id = subject_id
        if duration_minutes is not None:
            s.duration_minutes = duration_minutes
        if session_date is not None:
            s.session_date = session_date
        if topic is not None:
            s.topic = topic
        if notes is not None:
            s.notes = notes
        session.commit()
    return s


def delete_session(session, session_id: int) -> bool:
    s = session.get(StudySession, session_id)
    if s:
        session.delete(s)
        session.commit()
        return True
    return False


def list_sessions(session, user_id: int, limit: int = 100):
    return (
        session.query(StudySession)
        .filter_by(user_id=user_id)
        .order_by(StudySession.session_date.desc())
        .limit(limit)
        .all()
    )
