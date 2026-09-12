from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from backend.app.models.models import (
    TimeWindow, MockOAVariant, MockOAAttempt, QuestionBank, generate_uuid, utc_now
)

class MockOAAgent:
    """
    Agent 3: Mock OA Engine.
    Enforces rolling 7-day time windows and canonical (company, role, time_window_id, attempt_number)
    isolation so all candidates on attempt #N in the same window get identical OA test papers.
    """

    @classmethod
    def get_or_create_active_window(
        cls, db: Session, company: str, role: str, window_days: int = 7
    ) -> TimeWindow:
        now = datetime.now(timezone.utc)
        window = db.query(TimeWindow).filter(
            TimeWindow.company == company,
            TimeWindow.role == role,
            TimeWindow.status == "ACTIVE",
            TimeWindow.window_end > now
        ).first()

        if not window:
            window = TimeWindow(
                id=generate_uuid(),
                company=company,
                role=role,
                window_length_days=window_days,
                window_start=now,
                window_end=now + timedelta(days=window_days),
                status="ACTIVE"
            )
            db.add(window)
            db.commit()
            db.refresh(window)

        return window

    @classmethod
    def start_mock_oa(
        cls, db: Session, user_id: str, company: str, role: str
    ) -> Tuple[MockOAVariant, MockOAAttempt, int]:
        company_clean = company.strip().title()
        role_clean = role.strip().title()

        # 1. Get active time window
        window = cls.get_or_create_active_window(db, company_clean, role_clean)

        # 2. Count user's prior attempts in this window
        prior_attempts = db.query(MockOAAttempt).join(MockOAVariant).filter(
            MockOAAttempt.user_id == user_id,
            MockOAVariant.company == company_clean,
            MockOAVariant.role == role_clean,
            MockOAVariant.time_window_id == window.id
        ).count()

        current_attempt_number = prior_attempts + 1

        # 3. Look up canonical Mock OA Variant for (company, role, time_window_id, attempt_number)
        variant = db.query(MockOAVariant).filter(
            MockOAVariant.company == company_clean,
            MockOAVariant.role == role_clean,
            MockOAVariant.time_window_id == window.id,
            MockOAVariant.attempt_number == current_attempt_number
        ).first()

        if not variant:
            # Generate canonical variant with balanced mix
            variant = cls._generate_canonical_variant(
                db, company_clean, role_clean, window.id, current_attempt_number
            )

        # 4. Create user attempt session
        attempt = MockOAAttempt(
            id=generate_uuid(),
            user_id=user_id,
            mock_oa_variant_id=variant.id,
            user_attempt_count=current_attempt_number,
            started_at=utc_now(),
            answers_json={},
            evaluation_json={},
            score=0.0
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)

        # Compute days remaining in window
        end_dt = window.window_end
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)
        now_dt = datetime.now(timezone.utc)
        days_remaining = max(1, (end_dt - now_dt).days)

        return variant, attempt, days_remaining

    @classmethod
    def _generate_canonical_variant(
        cls, db: Session, company: str, role: str, window_id: str, attempt_num: int
    ) -> MockOAVariant:
        # Categorize and sort questions deterministically by ID
        questions = db.query(QuestionBank).filter(QuestionBank.status == "PUBLISHED").all()

        dsa_qs = sorted([q for q in questions if q.question_type.upper() in ["DSA", "CODING"]], key=lambda x: x.id)
        sql_qs = sorted([q for q in questions if q.question_type.upper() == "SQL"], key=lambda x: x.id)
        other_qs = sorted([q for q in questions if q.question_type.upper() in ["MCQ", "MSQ", "SYSTEM DESIGN"]], key=lambda x: x.id)

        selected_ids = []

        # Attempt-based rotational selection guarantees distinct question sets per attempt:
        # Attempt 1 gets Set A, Attempt 2 gets Set B, Attempt 3 gets Set C.
        if dsa_qs:
            shift = ((attempt_num - 1) * 2) % len(dsa_qs)
            rotated_dsa = dsa_qs[shift:] + dsa_qs[:shift]
            for q in rotated_dsa[:2]:
                if q.id not in selected_ids:
                    selected_ids.append(q.id)

        if sql_qs:
            shift = (attempt_num - 1) % len(sql_qs)
            rotated_sql = sql_qs[shift:] + sql_qs[:shift]
            for q in rotated_sql[:1]:
                if q.id not in selected_ids:
                    selected_ids.append(q.id)

        if other_qs:
            shift = ((attempt_num - 1) * 2) % len(other_qs)
            rotated_other = other_qs[shift:] + other_qs[:shift]
            for q in rotated_other[:2]:
                if q.id not in selected_ids:
                    selected_ids.append(q.id)

        # If not enough specific types, fill from whatever is published
        if len(selected_ids) < 5 and questions:
            for q in questions:
                if q.id not in selected_ids:
                    selected_ids.append(q.id)
                if len(selected_ids) >= 5:
                    break

        variant = MockOAVariant(
            id=generate_uuid(),
            company=company,
            role=role,
            time_window_id=window_id,
            attempt_number=attempt_num,
            question_ids=selected_ids,
            duration_minutes=60,
            answer_key_json={q.id: q.solution for q in questions if q.id in selected_ids},
            status="PUBLISHED",
            created_at=utc_now()
        )
        db.add(variant)
        db.commit()
        db.refresh(variant)
        return variant
