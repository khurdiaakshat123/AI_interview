import json
import asyncio
import re
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from backend.app.database import get_db
from backend.app.models.models import (
    InterviewSession, InterviewEvidence, StructuredResume, RoleTopicProfile, User, generate_uuid, utc_now
)
from backend.app.schemas.schemas import (
    ResumeUploadRequest, StructuredResumeOut, InterviewSessionCreate,
    InterviewAnswerRequest, InterviewTurnOut, InterviewFinalReportOut, ProjectScoreCard, InterviewEvidenceRecord,
    CorrectTranscriptRequest, CorrectTranscriptResponse
)
from backend.app.engines.resume_parser import ResumeParser
from backend.app.agents.interview_agent import InterviewAgent
from backend.app.llm.client import llm_client
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/api/interview", tags=["AI Mock Interview"])

@router.post("/parse-resume", response_model=StructuredResumeOut)
def parse_resume(payload: ResumeUploadRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = current_user.id

    parsed = ResumeParser.parse_resume(payload.resume_text, payload.company, payload.role)

    resume = StructuredResume(
        id=generate_uuid(),
        user_id=user_id,
        candidate_name=payload.candidate_name or parsed["candidate_name"],
        candidate_email=payload.candidate_email or parsed["candidate_email"],
        raw_text=payload.resume_text,
        sections_json=parsed["sections"],
        section_weights_json=parsed["section_weights"],
        created_at=utc_now()
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    return StructuredResumeOut(
        id=resume.id,
        candidate_name=resume.candidate_name,
        candidate_email=resume.candidate_email,
        work_experience=resume.sections_json.get("work_experience", []),
        projects=resume.sections_json.get("projects", []),
        skills=resume.sections_json.get("skills", []),
        education=resume.sections_json.get("education", []),
        section_weights=resume.section_weights_json or {}
    )

@router.get("/resumes/sample", response_model=StructuredResumeOut)
def get_sample_resume(db: Session = Depends(get_db)):
    resume = db.query(StructuredResume).first()
    if not resume:
        raise HTTPException(status_code=404, detail="No resume found")

    return StructuredResumeOut(
        id=resume.id,
        candidate_name=resume.candidate_name,
        candidate_email=resume.candidate_email,
        work_experience=resume.sections_json.get("work_experience", []),
        projects=resume.sections_json.get("projects", []),
        skills=resume.sections_json.get("skills", []),
        education=resume.sections_json.get("education", []),
        section_weights=resume.section_weights_json or {}
    )

@router.post("/sessions", response_model=InterviewTurnOut)
def create_interview_session(payload: InterviewSessionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = current_user.id

    resume = None
    if payload.resume_id:
        resume = db.query(StructuredResume).filter(StructuredResume.id == payload.resume_id).first()
    elif payload.resume_text:
        parsed = ResumeParser.parse_resume(payload.resume_text, payload.company, payload.role)
        resume = StructuredResume(
            id=generate_uuid(),
            user_id=user_id,
            candidate_name=payload.candidate_name or parsed["candidate_name"],
            candidate_email=parsed["candidate_email"],
            raw_text=payload.resume_text,
            sections_json=parsed["sections"],
            section_weights_json=parsed["section_weights"],
            created_at=utc_now()
        )
        db.add(resume)
        db.commit()
        db.refresh(resume)

    role_profile = None
    if payload.role_topic_profile_id:
        role_profile = db.query(RoleTopicProfile).filter(RoleTopicProfile.id == payload.role_topic_profile_id).first()

    session = InterviewAgent.start_session(
        db=db,
        user_id=user_id,
        company=payload.company,
        role=payload.role,
        job_type=payload.job_type or "Full-Time",
        resume=resume,
        role_profile=role_profile,
        candidate_name=payload.candidate_name or "Candidate"
    )

    first_turn = session.transcript_json[0]
    return InterviewTurnOut(
        session_id=session.id,
        phase=session.current_phase,
        current_topic=first_turn.get("topic", "System Architecture"),
        question_id=session.current_question_id,
        question_text=first_turn.get("text", ""),
        depth_level=session.current_depth,
        max_depth=InterviewAgent.MAX_DEPTH,
        is_completed=False,
        eval_previous=None
    )

@router.post("/sessions/{id}/answer", response_model=InterviewTurnOut)
def answer_interview_question(id: str, payload: InterviewAnswerRequest, db: Session = Depends(get_db)):
    session = db.query(InterviewSession).filter(InterviewSession.id == id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")

    if session.status == "COMPLETED":
        return InterviewTurnOut(
            session_id=session.id,
            phase="COMPLETED",
            current_topic="Completed",
            question_id="",
            question_text="This interview session has already concluded.",
            depth_level=session.current_depth,
            max_depth=InterviewAgent.MAX_DEPTH,
            is_completed=True,
            eval_previous=None
        )

    result = InterviewAgent.process_answer(db=db, session=session, user_answer=payload.answer)
    return InterviewTurnOut(**result)

@router.post("/sessions/{id}/answer-stream")
async def answer_interview_question_stream(
    id: str,
    payload: InterviewAnswerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session = db.query(InterviewSession).filter(InterviewSession.id == id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")

    if session.status == "COMPLETED":
        data = {
            "type": "turn",
            "payload": {
                "session_id": session.id,
                "phase": "COMPLETED",
                "current_topic": "Completed",
                "question_id": "",
                "question_text": "This interview session has already concluded.",
                "depth_level": session.current_depth,
                "max_depth": InterviewAgent.MAX_DEPTH,
                "is_completed": True,
                "eval_previous": None
            }
        }
        return StreamingResponse(iter([f"data: {json.dumps(data)}\n\n"]), media_type="text/event-stream")

    async def event_generator():
        result = await asyncio.to_thread(InterviewAgent.process_answer, db=db, session=session, user_answer=payload.answer)
        question_text = result.get("question_text", "")
        raw_sentences = re.split(r'(?<=[.!?])\s+', question_text.strip())
        sentences = [s.strip() for s in raw_sentences if s.strip()]
        if not sentences and question_text.strip():
            sentences = [question_text.strip()]

        for idx, sentence in enumerate(sentences):
            sentence_event = {
                "type": "sentence",
                "text": sentence,
                "index": idx,
                "total": len(sentences)
            }
            yield f"data: {json.dumps(sentence_event)}\n\n"
            await asyncio.sleep(0.03)

        turn_event = {
            "type": "turn",
            "payload": result
        }
        yield f"data: {json.dumps(turn_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.post("/sessions/{id}/correct-transcript", response_model=CorrectTranscriptResponse)
def correct_session_transcript(id: str, payload: CorrectTranscriptRequest, db: Session = Depends(get_db)):
    session = db.query(InterviewSession).filter(InterviewSession.id == id).first()

    resume_context = ""
    role = "Software Engineer"
    company = "Tech Company"
    question_text = payload.question_text or ""
    topic = payload.topic or ""

    if session:
        role = session.role
        company = session.company
        if not question_text and session.transcript_json:
            for turn in reversed(session.transcript_json):
                if turn.get("sender") == "INTERVIEWER":
                    question_text = turn.get("text", "")
                    topic = turn.get("topic", "")
                    break

        if session.resume_id:
            resume = db.query(StructuredResume).filter(StructuredResume.id == session.resume_id).first()
            if resume and resume.sections_json:
                sec = resume.sections_json
                proj_summaries = [f"- {p.get('title')}: {p.get('description', '')} (Tech: {', '.join(p.get('technologies', []))})" for p in sec.get("projects", [])]
                work_summaries = [f"- {w.get('role')} at {w.get('company')}: {w.get('description', '')}" for w in sec.get("work_experience", [])]
                skills = ", ".join(sec.get("skills", []))

                parts = []
                if proj_summaries:
                    parts.append("Projects:\n" + "\n".join(proj_summaries))
                if work_summaries:
                    parts.append("Work Experience:\n" + "\n".join(work_summaries))
                if skills:
                    parts.append("Skills: " + skills)
                resume_context = "\n\n".join(parts)

    res = llm_client.correct_candidate_answer_typos(
        raw_answer=payload.raw_text,
        question_text=question_text,
        resume_context=resume_context,
        role=role,
        company=company,
        topic=topic
    )
    return CorrectTranscriptResponse(**res)

@router.post("/correct-transcript", response_model=CorrectTranscriptResponse)
def correct_transcript_standalone(payload: CorrectTranscriptRequest):
    res = llm_client.correct_candidate_answer_typos(
        raw_answer=payload.raw_text,
        question_text=payload.question_text or "",
        resume_context="",
        topic=payload.topic or ""
    )
    return CorrectTranscriptResponse(**res)

@router.get("/sessions/{id}/report", response_model=InterviewFinalReportOut)
def get_interview_report(id: str, db: Session = Depends(get_db)):
    session = db.query(InterviewSession).filter(InterviewSession.id == id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")

    # Ensure reports are computed
    if not session.final_report_json:
        InterviewAgent._generate_final_reports(db, session)
        db.refresh(session)

    report = session.final_report_json or {}
    evidence_rows = db.query(InterviewEvidence).filter(InterviewEvidence.session_id == session.id).all()

    evidence_models = [
        InterviewEvidenceRecord(
            id=e.id,
            project_id_or_topic=e.project_id_or_topic,
            question_id=e.question_id,
            follow_up_index=e.follow_up_index,
            topic=e.topic,
            subtopic=e.subtopic,
            user_answer=e.user_answer,
            expected_concept=e.expected_concept,
            detected_gap=e.detected_gap,
            severity=e.severity,
            earned_points=e.earned_points,
            possible_points=e.possible_points,
            evaluator_reason=e.evaluator_reason,
            evidence_ref=e.evidence_ref
        )
        for e in evidence_rows
    ]

    project_cards = [
        ProjectScoreCard(
            project_id=c.get("project_id", "p1"),
            title=c.get("title", "Flagship Project"),
            score=c.get("score", 85.0),
            star_rating=c.get("star_rating", 4.25),
            relevance_weight=c.get("relevance_weight", 1.0),
            strengths=c.get("strengths", []),
            identified_gaps=c.get("identified_gaps", []),
            topics_covered=c.get("topics_covered", [])
        )
        for c in report.get("project_cards", [])
    ]

    resume = db.query(StructuredResume).filter(StructuredResume.id == session.resume_id).first()
    candidate_name = resume.candidate_name if resume else "Candidate"

    return InterviewFinalReportOut(
        session_id=session.id,
        company=session.company,
        role=session.role,
        candidate_name=candidate_name,
        resume_related_score=report.get("resume_related_score", 85.0),
        subject_knowledge_score=report.get("subject_knowledge_score", 88.0),
        section_scores=report.get("section_scores", {}),
        project_cards=project_cards,
        subject_topic_breakdown=report.get("subject_topic_breakdown", {}),
        evidence_trail=evidence_models,
        strengths=report.get("strengths", []),
        weaknesses=report.get("weaknesses", []),
        improvement_recommendations=report.get("improvement_recommendations", []),
        completed_at=session.completed_at or session.created_at
    )

@router.get("/sessions/{id}/stream")
async def stream_interview_session(id: str, db: Session = Depends(get_db)):
    """
    Server-Sent Events (SSE) channel for real-time interview interactions.
    """
    session = db.query(InterviewSession).filter(InterviewSession.id == id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_generator():
        # Stream current state
        data = {
            "session_id": session.id,
            "phase": session.current_phase,
            "status": session.status,
            "current_depth": session.current_depth,
            "transcript_count": len(session.transcript_json or [])
        }
        yield f"data: {json.dumps(data)}\n\n"
        await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
