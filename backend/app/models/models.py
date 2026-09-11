import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime, Boolean, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from backend.app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True, default="google_oauth")
    name = Column(String(255), nullable=False)
    google_id = Column(String(255), unique=True, index=True, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

class TimeWindow(Base):
    __tablename__ = "time_windows"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    company = Column(String(100), index=True, nullable=False)
    role = Column(String(100), index=True, nullable=False)
    window_length_days = Column(Integer, default=7)
    window_start = Column(DateTime(timezone=True), default=utc_now)
    window_end = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), default="ACTIVE")  # ACTIVE | CLOSED

class RoleTopicProfile(Base):
    __tablename__ = "role_topic_profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    company = Column(String(100), index=True, nullable=False)
    role = Column(String(100), index=True, nullable=False)
    job_type = Column(String(50), default="Full-Time")
    experience_requirement = Column(String(50), default="1-3 years")
    required_skills = Column(JSON, default=list)  # list of strings
    time_window_id = Column(String(36), ForeignKey("time_windows.id"), nullable=True)
    subjects_json = Column(JSON, default=list)  # subjects > topics > subtopics
    evidence_json = Column(JSON, default=list)  # fact, source, trust_level, timestamp
    created_at = Column(DateTime(timezone=True), default=utc_now)
    refreshed_at = Column(DateTime(timezone=True), default=utc_now)

class QuestionBank(Base):
    __tablename__ = "question_bank"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    subject = Column(String(100), index=True, nullable=False)
    topic = Column(String(100), index=True, nullable=False)
    subtopic = Column(String(100), index=True, nullable=False)
    question_type = Column(String(50), nullable=False)  # MCQ, MSQ, DSA, SQL, System Design, Debugging
    difficulty = Column(String(20), default="medium")  # easy, medium, hard
    title = Column(String(255), nullable=True)
    prompt = Column(Text, nullable=False)
    hint = Column(Text, nullable=True)
    approach = Column(Text, nullable=True)
    solution = Column(Text, nullable=True)
    options_json = Column(JSON, nullable=True)  # for MCQ/MSQ
    test_cases_json = Column(JSON, default=list)  # visible + hidden test cases for DSA/SQL
    starter_code = Column(Text, nullable=True)
    status = Column(String(20), default="PUBLISHED")  # GENERATING | REVIEWING | PUBLISHED | FAILED
    review_report_json = Column(JSON, default=dict)  # 18-point verification results
    question_generator_version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utc_now)

class PracticeSession(Base):
    __tablename__ = "practice_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    practice_generation_key = Column(String(64), unique=True, index=True, nullable=False)
    company = Column(String(100), nullable=False)
    role = Column(String(100), nullable=False)
    time_window_id = Column(String(36), nullable=True)
    selected_topics_json = Column(JSON, default=list)
    proficiency_vector_json = Column(JSON, default=dict)
    total_questions = Column(Integer, default=5)
    allocation_mode = Column(String(20), default="auto")  # auto | manual
    question_bank_level = Column(String(20), default="adaptive")
    question_generator_version = Column(Integer, default=1)
    question_ids = Column(JSON, default=list)
    user_answers_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)

class MockOAVariant(Base):
    __tablename__ = "mock_oa_variants"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    company = Column(String(100), index=True, nullable=False)
    role = Column(String(100), index=True, nullable=False)
    time_window_id = Column(String(36), ForeignKey("time_windows.id"), nullable=False)
    attempt_number = Column(Integer, nullable=False)  # 1, 2, 3...
    question_ids = Column(JSON, default=list)
    duration_minutes = Column(Integer, default=60)
    answer_key_json = Column(JSON, default=dict)
    status = Column(String(20), default="PUBLISHED")  # PUBLISHED | STALE | FAILED
    created_at = Column(DateTime(timezone=True), default=utc_now)

class MockOAAttempt(Base):
    __tablename__ = "mock_oa_attempts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    mock_oa_variant_id = Column(String(36), ForeignKey("mock_oa_variants.id"), nullable=False)
    user_attempt_count = Column(Integer, default=1)
    started_at = Column(DateTime(timezone=True), default=utc_now)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    answers_json = Column(JSON, default=dict)
    evaluation_json = Column(JSON, default=dict)
    score = Column(Float, default=0.0)

class StructuredResume(Base):
    __tablename__ = "structured_resumes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    candidate_name = Column(String(255), default="Candidate")
    candidate_email = Column(String(255), nullable=True)
    raw_text = Column(Text, nullable=True)
    sections_json = Column(JSON, default=dict)  # Work Exp, Projects, Education, Skills, etc.
    section_weights_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)

class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    resume_id = Column(String(36), ForeignKey("structured_resumes.id"), nullable=True)
    role_topic_profile_id = Column(String(36), ForeignKey("role_topic_profiles.id"), nullable=True)
    company = Column(String(100), nullable=False)
    role = Column(String(100), nullable=False)
    job_type = Column(String(50), default="Full-Time")
    status = Column(String(30), default="INIT")  # INIT | IN_PROGRESS | COMPLETED
    current_phase = Column(String(30), default="PROJECT_DEFENSE")  # PROJECT_DEFENSE | SUBJECT_KNOWLEDGE | COMPLETED
    current_thread_id = Column(String(100), nullable=True)  # project_id or subject_topic
    current_question_id = Column(String(100), nullable=True)
    current_depth = Column(Integer, default=1)
    transcript_json = Column(JSON, default=list)  # conversation turns
    agent1_report_json = Column(JSON, default=dict)  # Resume/Project Defense Report
    agent2_report_json = Column(JSON, default=dict)  # Subject Knowledge Report
    final_report_json = Column(JSON, default=dict)  # Dual headline scores & audit
    created_at = Column(DateTime(timezone=True), default=utc_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)

class InterviewEvidence(Base):
    __tablename__ = "interview_evidence"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("interview_sessions.id"), nullable=False)
    project_id_or_topic = Column(String(100), nullable=False)
    question_id = Column(String(100), nullable=False)
    follow_up_index = Column(Integer, default=0)
    topic = Column(String(100), nullable=False)
    subtopic = Column(String(100), nullable=False)
    user_answer = Column(Text, nullable=False)
    expected_concept = Column(Text, nullable=False)
    detected_gap = Column(Text, nullable=True)
    severity = Column(String(20), default="NONE")  # NONE | MINOR | MODERATE | SEVERE
    earned_points = Column(Float, nullable=False)
    possible_points = Column(Float, nullable=False)
    evaluator_reason = Column(Text, nullable=False)
    evidence_ref = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
