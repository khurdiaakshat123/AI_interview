import hashlib
import json
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.models.models import PracticeSession, QuestionBank, RoleTopicProfile, generate_uuid, utc_now

class PracticeAgent:
    """
    Agent 2: Practice Question Engine.
    Generates personalized or role-profile practice sessions with strict SHA256 key determinism.
    Provides hint, approach, and solution.
    """

    @classmethod
    def compute_generation_key(
        cls,
        company: str,
        role: str,
        time_window_id: str,
        selected_topics: List[str],
        proficiency_vector: Dict[str, str],
        total_questions: int,
        allocation_mode: str,
        question_bank_level: str,
        version: int = 1
    ) -> str:
        canonical_dict = {
            "company": company.strip().lower(),
            "role": role.strip().lower(),
            "time_window_id": time_window_id or "default-window",
            "selected_topics": sorted(selected_topics),
            "proficiency_vector": sorted(proficiency_vector.items()),
            "total_questions": total_questions,
            "allocation_mode": allocation_mode,
            "question_bank_level": question_bank_level,
            "version": version
        }
        serialized = json.dumps(canonical_dict, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @classmethod
    def get_or_create_practice_session(
        cls,
        db: Session,
        user_id: str,
        company: str,
        role: str,
        time_window_id: str,
        selected_topics: List[str],
        proficiency_vector: Dict[str, str],
        total_questions: int = 5,
        allocation_mode: str = "auto",
        question_bank_level: str = "adaptive",
        role_profile_id: str = None
    ) -> PracticeSession:
        gen_key = cls.compute_generation_key(
            company=company,
            role=role,
            time_window_id=time_window_id,
            selected_topics=selected_topics,
            proficiency_vector=proficiency_vector,
            total_questions=total_questions,
            allocation_mode=allocation_mode,
            question_bank_level=question_bank_level
        )

        # Check if canonical practice set already exists
        existing = db.query(PracticeSession).filter(
            PracticeSession.practice_generation_key == gen_key
        ).first()

        if existing:
            return existing

        # Select questions matching criteria
        question_ids = cls._select_questions(
            db=db,
            selected_topics=selected_topics,
            proficiency_vector=proficiency_vector,
            total_questions=total_questions,
            allocation_mode=allocation_mode,
            question_bank_level=question_bank_level
        )

        session = PracticeSession(
            id=generate_uuid(),
            user_id=user_id,
            practice_generation_key=gen_key,
            company=company,
            role=role,
            time_window_id=time_window_id,
            selected_topics_json=selected_topics,
            proficiency_vector_json=proficiency_vector,
            total_questions=total_questions,
            allocation_mode=allocation_mode,
            question_bank_level=question_bank_level,
            question_generator_version=1,
            question_ids=question_ids,
            created_at=utc_now()
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    @classmethod
    def _select_questions(
        cls,
        db: Session,
        selected_topics: List[str],
        proficiency_vector: Dict[str, str],
        total_questions: int,
        allocation_mode: str,
        question_bank_level: str
    ) -> List[str]:
        # Query published questions from question bank
        query = db.query(QuestionBank).filter(QuestionBank.status == "PUBLISHED")
        all_published = query.all()

        if not all_published:
            return []

        # Filter by topics if specified
        matching = []
        if selected_topics:
            matching = [
                q for q in all_published
                if any(t.lower() in q.topic.lower() or q.topic.lower() in t.lower() for t in selected_topics)
            ]

        if not matching:
            matching = all_published

        # Sort and take top total_questions
        selected = matching[:total_questions]
        return [q.id for q in selected]
