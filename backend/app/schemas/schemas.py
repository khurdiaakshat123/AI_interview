from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

# --- Auth ---
class UserSignup(BaseModel):
    name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class GoogleAuthRequest(BaseModel):
    credential: str
    user_info: Optional[Dict[str, Any]] = None

class UserOut(BaseModel):
    id: str
    name: str
    email: str
    google_id: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

# --- Role Topic Profile ---
class RoleTopicProfileCreate(BaseModel):
    company: str
    role: str
    job_type: Optional[str] = "Full-Time"
    experience_requirement: Optional[str] = "1-3 years"
    jd_text: Optional[str] = None
    trusted_sources: Optional[List[str]] = None

class SubtopicInfo(BaseModel):
    name: str
    description: Optional[str] = None

class TopicDetail(BaseModel):
    topic: str
    subtopics: List[str]
    importance_score: float = Field(..., ge=0.0, le=1.0)
    expected_question_types: List[str]
    expected_difficulty_distribution: Dict[str, float]

class SubjectDetail(BaseModel):
    subject: str
    topics: List[TopicDetail]

class ProvenanceEvidence(BaseModel):
    fact: str
    source: str
    trust_level: str
    timestamp: str

class RoleTopicProfileOut(BaseModel):
    id: str
    company: str
    role: str
    job_type: str
    experience_requirement: str
    required_skills: List[str]
    time_window_id: Optional[str]
    subjects: List[SubjectDetail]
    evidence: List[ProvenanceEvidence]
    created_at: datetime
    refreshed_at: datetime

    class Config:
        from_attributes = True

# --- Question & Practice ---
class QuestionOut(BaseModel):
    id: str
    subject: str
    topic: str
    subtopic: str
    question_type: str
    difficulty: str
    title: Optional[str] = None
    prompt: str
    options: Optional[List[str]] = None
    starter_code: Optional[str] = None
    test_cases: Optional[List[Dict[str, Any]]] = None
    hint: Optional[str] = None
    approach: Optional[str] = None

class PracticeSessionCreate(BaseModel):
    role_profile_id: Optional[str] = None
    company: str
    role: str
    selected_topics: List[str]
    proficiency_vector: Dict[str, str] = {}  # topic -> "beginner" | "intermediate" | "advanced"
    total_questions: int = 5
    allocation_mode: str = "auto"  # auto | manual
    question_bank_level: str = "adaptive"

class CheckAnswerRequest(BaseModel):
    question_id: str
    answer: Any  # string option, list of options, or code string

class TestCaseResult(BaseModel):
    test_case_index: int
    input_data: str
    expected_output: str
    actual_output: Optional[str] = None
    passed: bool
    runtime_ms: Optional[float] = None
    memory_mb: Optional[float] = None

class CheckAnswerResponse(BaseModel):
    question_id: str
    is_correct: bool
    score_fraction: float
    feedback: str
    test_case_results: Optional[List[TestCaseResult]] = None
    optimal_complexity: Optional[str] = None

class HintResponse(BaseModel):
    question_id: str
    hint: str

class ApproachResponse(BaseModel):
    question_id: str
    approach: str

class SolutionResponse(BaseModel):
    question_id: str
    solution: str
    explanation: Optional[str] = None

# --- Mock OA ---
class MockOAStartRequest(BaseModel):
    company: str
    role: str

class MockOAVariantOut(BaseModel):
    id: str
    company: str
    role: str
    time_window_id: str
    attempt_number: int
    user_attempt_count: int
    duration_minutes: int
    window_expires_in_days: int
    questions: List[QuestionOut]
    mock_oa_attempt_id: str

class MockOASubmitRequest(BaseModel):
    answers: Dict[str, Any]  # question_id -> answer
    time_spent_per_question: Optional[Dict[str, int]] = {}  # seconds
    proctoring_data: Optional[Dict[str, Any]] = None

class RunCodeRequest(BaseModel):
    question_id: str
    code: str
    language: str = "python"
    custom_input: Optional[str] = None

class RunCodeResponse(BaseModel):
    status: str  # ACCEPTED, WRONG_ANSWER, COMPILATION_ERROR, RUNTIME_ERROR, TLE
    runtime_ms: float = 0.0
    memory_mb: float = 0.0
    test_case_results: List[TestCaseResult] = []
    compiler_output: Optional[str] = None
    feedback: Optional[str] = None

class MockOAReportOut(BaseModel):
    attempt_id: str
    company: str
    role: str
    attempt_number: int
    total_score: float
    max_possible_score: float
    percentage: float
    accuracy_by_topic: Dict[str, Dict[str, Any]]
    strong_topics: List[str]
    weak_topics: List[str]
    time_spent_seconds: int
    questions_review: List[Dict[str, Any]]
    submitted_at: datetime
    proctoring_summary: Optional[Dict[str, Any]] = None

# --- Resume & Interview ---
class ResumeUploadRequest(BaseModel):
    candidate_name: str
    candidate_email: Optional[str] = None
    resume_text: str
    company: str
    role: str

class ProjectRelevance(BaseModel):
    project_id: str
    title: str
    description: str
    technologies: List[str]
    overall_relevance: float
    questioning_priority: int
    relevant_topics: List[str]
    irrelevant_topics: List[str]

class StructuredResumeOut(BaseModel):
    id: str
    candidate_name: str
    candidate_email: Optional[str]
    work_experience: List[Dict[str, Any]]
    projects: List[ProjectRelevance]
    skills: List[str]
    education: List[Dict[str, Any]]
    section_weights: Dict[str, float]

class InterviewSessionCreate(BaseModel):
    company: str
    role: str
    job_type: Optional[str] = "Full-Time"
    resume_id: Optional[str] = None
    role_topic_profile_id: Optional[str] = None
    resume_text: Optional[str] = None
    candidate_name: Optional[str] = "Candidate"

class InterviewAnswerRequest(BaseModel):
    answer: str

class CorrectTranscriptRequest(BaseModel):
    raw_text: str
    question_text: Optional[str] = None
    topic: Optional[str] = None

class CorrectTranscriptResponse(BaseModel):
    corrected_text: str
    original_text: str
    changes_made: List[str] = []
    has_corrections: bool = False

class InterviewTurnOut(BaseModel):
    session_id: str
    phase: str  # PROJECT_DEFENSE | SUBJECT_KNOWLEDGE | COMPLETED
    current_topic: str
    question_id: str
    question_text: str
    depth_level: int
    max_depth: int
    is_completed: bool
    eval_previous: Optional[Dict[str, Any]] = None
    candidate_name: Optional[str] = None

class InterviewEvidenceRecord(BaseModel):
    id: str
    project_id_or_topic: str
    question_id: str
    follow_up_index: int
    topic: str
    subtopic: str
    user_answer: str
    expected_concept: str
    detected_gap: Optional[str]
    severity: str
    earned_points: float
    possible_points: float
    evaluator_reason: str
    evidence_ref: Optional[str]

class ProjectScoreCard(BaseModel):
    project_id: str
    title: str
    score: float
    star_rating: float
    relevance_weight: float
    strengths: List[str]
    identified_gaps: List[str]
    topics_covered: List[str]

class InterviewFinalReportOut(BaseModel):
    session_id: str
    company: str
    role: str
    candidate_name: str
    # Dual headline scores (§6.5)
    resume_related_score: float  # /100
    subject_knowledge_score: float  # /100
    section_scores: Dict[str, float]
    project_cards: List[ProjectScoreCard]
    subject_topic_breakdown: Dict[str, str]  # topic -> STRONG | PARTIAL | WEAK | UNTESTED
    evidence_trail: List[InterviewEvidenceRecord]
    strengths: List[str]
    weaknesses: List[str]
    improvement_recommendations: List[str]
    completed_at: datetime

# --- Admin Review Queue ---
class ReviewQueueItem(BaseModel):
    id: str
    subject: str
    topic: str
    subtopic: str
    question_type: str
    difficulty: str
    title: Optional[str]
    prompt: str
    status: str
    review_report: Dict[str, Any]
    created_at: datetime

class ReviewDecisionRequest(BaseModel):
    action: str  # approve | reject
    notes: Optional[str] = None

# --- Unified Candidate & JD Onboarding ---
class CandidateSetupRequest(BaseModel):
    name: str
    email: str
    experience_years: Optional[str] = "1-3 years"
    target_company: str = "Google"
    target_role: str = "Software Engineer II (L4)"
    job_type: Optional[str] = "Full-Time"
    jd_text: Optional[str] = ""
    resume_text: Optional[str] = ""

class CandidateSetupResponse(BaseModel):
    user: UserOut
    role_profile: RoleTopicProfileOut
    structured_resume: StructuredResumeOut
    initial_turn: InterviewTurnOut
    company: str
    role: str
    candidate_name: Optional[str] = None
