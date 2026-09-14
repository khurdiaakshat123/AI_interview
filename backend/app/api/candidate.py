import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.models import (
    User, RoleTopicProfile, StructuredResume, InterviewSession, generate_uuid, utc_now
)
from backend.app.schemas.schemas import (
    CandidateSetupRequest, CandidateSetupResponse, UserOut,
    RoleTopicProfileOut, StructuredResumeOut, InterviewTurnOut,
    SubjectDetail, TopicDetail, ProvenanceEvidence, ProjectRelevance
)
from backend.app.agents.role_profile_agent import RoleProfileAgent
from backend.app.engines.resume_parser import ResumeParser
from backend.app.engines.document_parser import DocumentParser
from backend.app.agents.interview_agent import InterviewAgent

from backend.app.api.deps import get_current_user_optional

router = APIRouter(prefix="/api/candidate", tags=["Candidate & Custom Onboarding"])

@router.get("/debug/llm")
def debug_llm():
    import os
    import httpx
    keys = {
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY", "")[:4] + "***" if os.getenv("GROQ_API_KEY") else "MISSING",
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", "")[:4] + "***" if os.getenv("GEMINI_API_KEY") else "MISSING",
    }
    
    groq_key = os.getenv("GROQ_API_KEY")
    groq_status = "Skipped"
    groq_error = ""
    
    if groq_key:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
        payload = {
            "model": "llama3-8b-8192",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 10
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, headers=headers, json=payload)
                groq_status = resp.status_code
                groq_error = resp.text[:500]
        except Exception as e:
            groq_status = "Exception"
            groq_error = str(e)
            
    return {
        "keys_detected": keys,
        "groq_test_status": groq_status,
        "groq_test_response": groq_error
    }


@router.post("/extract-file")
async def extract_file_content(file: UploadFile = File(...)):
    """
    Accepts PDF, Image (PNG, JPG, WEBP), or Text file.
    Extracts and returns plain text for JD or Resume input with metadata.
    """
    try:
        content_bytes = await file.read()
        if not content_bytes or len(content_bytes) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        extracted_text, detected_type = DocumentParser.extract_text(
            file_bytes=content_bytes,
            filename=file.filename or "uploaded_file",
            content_type=file.content_type or ""
        )

        if not extracted_text or extracted_text.startswith("Error extracting") or extracted_text.startswith("Error:"):
            error_detail = extracted_text if extracted_text else "Could not extract readable text from document."
            raise HTTPException(status_code=400, detail=error_detail)

        words = len(extracted_text.split())
        candidate_name, candidate_email = DocumentParser.extract_candidate_meta(extracted_text)

        return {
            "filename": file.filename,
            "file_type": detected_type,
            "extracted_text": extracted_text,
            "word_count": words,
            "char_count": len(extracted_text),
            "candidate_name": candidate_name,
            "candidate_email": candidate_email
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")

@router.post("/setup", response_model=CandidateSetupResponse)
def setup_candidate_and_run(
    payload: CandidateSetupRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    # 1. Determine User identity for multi-tenant isolation
    if current_user:
        user = current_user
        # Only update user name if this is an anonymous guest account
        if user.id.startswith("guest_") and payload.name and payload.name.strip():
            user.name = payload.name.strip()
            db.commit()
            db.refresh(user)
    else:
        user = db.query(User).filter(User.email == payload.email.strip().lower()).first()
        if not user:
            user = User(
                id=generate_uuid(),
                name=payload.name.strip() or "Candidate",
                email=payload.email.strip().lower(),
                password_hash="mock_hash_auto",
                created_at=utc_now()
            )
            db.add(user)
            db.commit()
            db.refresh(user)

    candidate_name = payload.name.strip() if (payload.name and payload.name.strip()) else user.name
    candidate_email = payload.email.strip().lower() if (payload.email and payload.email.strip()) else user.email
    company = payload.target_company.strip() or "Target Company"
    role = payload.target_role.strip() or "Software Engineer"

    # 2. Extract / Generate Role Topic Profile via Agent 1 (Live LLM)
    profile_data = RoleProfileAgent.generate_profile(
        company=company,
        role=role,
        job_type=payload.job_type or "Full-Time",
        experience_requirement=payload.experience_years or "1-3 years",
        jd_text=payload.jd_text or ""
    )

    role_profile = RoleTopicProfile(
        id=generate_uuid(),
        company=company,
        role=role,
        job_type=payload.job_type or "Full-Time",
        experience_requirement=payload.experience_years or "1-3 years",
        required_skills=profile_data.get("required_skills", []),
        time_window_id=None,
        subjects_json=profile_data.get("subjects", []),
        evidence_json=profile_data.get("evidence", []),
        created_at=utc_now(),
        refreshed_at=utc_now()
    )
    db.add(role_profile)
    db.commit()
    db.refresh(role_profile)

    # 3. Parse Custom Resume via ResumeParser (Live LLM)
    resume_parsed = ResumeParser.parse_resume(
        raw_text=payload.resume_text or f"Resume of {candidate_name}. Technical skills: Python, Go, System Design.",
        target_company=company,
        target_role=role
    )

    resume_obj = StructuredResume(
        id=generate_uuid(),
        user_id=user.id,
        candidate_name=candidate_name,
        candidate_email=candidate_email,
        raw_text=payload.resume_text or "",
        sections_json=resume_parsed.get("sections", {}),
        section_weights_json=resume_parsed.get("section_weights", {}),
        created_at=utc_now()
    )
    db.add(resume_obj)
    db.commit()
    db.refresh(resume_obj)

    # 4. Initialize Live Interview Session
    try:
        session = InterviewAgent.start_session(
            db=db,
            user_id=user.id,
            company=company,
            role=role,
            resume=resume_obj,
            role_profile=role_profile,
            job_type=payload.job_type or "Full-Time",
            candidate_name=candidate_name
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Prepare initial turn
    first_turn = session.transcript_json[0] if session.transcript_json else {}
    initial_turn_out = InterviewTurnOut(
        session_id=session.id,
        phase=session.current_phase,
        current_topic=first_turn.get("topic", "Architecture"),
        question_id=session.current_question_id or str(uuid.uuid4()),
        question_text=first_turn.get("text", "Welcome to your interview. Let us discuss your projects."),
        depth_level=1,
        max_depth=InterviewAgent.MAX_DEPTH,
        is_completed=False,
        eval_previous=None,
        candidate_name=candidate_name
    )

    # Format output models
    subjects_out = [
        SubjectDetail(
            subject=s.get("subject", "General"),
            topics=[
                TopicDetail(
                    topic=t.get("topic", ""),
                    subtopics=t.get("subtopics", []),
                    importance_score=t.get("importance_score", 0.8),
                    expected_question_types=t.get("expected_question_types", ["DSA"]),
                    expected_difficulty_distribution=t.get("expected_difficulty_distribution", {"medium": 1.0})
                )
                for t in s.get("topics", [])
            ]
        )
        for s in role_profile.subjects_json or []
    ]

    evidence_out = [
        ProvenanceEvidence(
            fact=e.get("fact", ""),
            source=e.get("source", ""),
            trust_level=e.get("trust_level", "high"),
            timestamp=e.get("timestamp", utc_now().isoformat())
        )
        for e in role_profile.evidence_json or []
    ]

    role_profile_out = RoleTopicProfileOut(
        id=role_profile.id,
        company=role_profile.company,
        role=role_profile.role,
        job_type=role_profile.job_type,
        experience_requirement=role_profile.experience_requirement,
        required_skills=role_profile.required_skills or [],
        time_window_id=role_profile.time_window_id,
        subjects=subjects_out,
        evidence=evidence_out,
        created_at=role_profile.created_at,
        refreshed_at=role_profile.refreshed_at
    )

    projects_out = [
        ProjectRelevance(
            project_id=p.get("project_id", str(uuid.uuid4())),
            title=p.get("title", "Project"),
            description=p.get("description", ""),
            technologies=p.get("technologies", []),
            overall_relevance=p.get("overall_relevance", 0.9),
            questioning_priority=p.get("questioning_priority", 1),
            relevant_topics=p.get("relevant_topics", []),
            irrelevant_topics=p.get("irrelevant_topics", [])
        )
        for p in resume_obj.sections_json.get("projects", [])
    ]

    structured_resume_out = StructuredResumeOut(
        id=resume_obj.id,
        candidate_name=resume_obj.candidate_name,
        candidate_email=resume_obj.candidate_email,
        work_experience=resume_obj.sections_json.get("work_experience", []),
        projects=projects_out,
        skills=resume_obj.sections_json.get("skills", []),
        education=resume_obj.sections_json.get("education", []),
        section_weights=resume_obj.section_weights_json or {}
    )

    return CandidateSetupResponse(
        user=UserOut.model_validate(user),
        role_profile=role_profile_out,
        structured_resume=structured_resume_out,
        initial_turn=initial_turn_out,
        company=company,
        role=role,
        candidate_name=candidate_name
    )


