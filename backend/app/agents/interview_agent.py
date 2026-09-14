from __future__ import annotations
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from backend.app.models.models import (
    InterviewSession, InterviewEvidence, StructuredResume, RoleTopicProfile, generate_uuid, utc_now
)
from backend.app.engines.interview_state import InterviewState, ClaimSource, ClaimStatus
from backend.app.engines.question_profile import QuestionProfile, QuestionKind
from backend.app.engines.answer_evaluator import AnswerEvaluator, SemanticEvaluationResult
from backend.app.engines.consistency_engine import ConsistencyEngine, ConsistencyAnalysisResult
from backend.app.engines.scoring_policy import ScoringPolicy
from backend.app.engines.adaptive_planner import AdaptivePlanner, PlannerAction, PlannerDecision
from backend.app.engines.scoring_engine import ScoringEngine
from backend.app.engines.question_generator import QuestionGenerator
from backend.app.engines.resume_parser import ResumeParser
from backend.app.engines.web_search import WebSearchEngine
from backend.app.engines.transcript_normalizer import TranscriptNormalizer
from backend.app.engines.report_generator import ReportGenerator
from backend.app.llm.client import llm_client


class InterviewAgent:
    """
    Multi-Turn Adaptive AI Technical Interview Subsystem:
    - Phase 1: Work Experience Defense (all professional experience explored first)
    - Phase 2: Project Defense (projects explored strictly sorted by relevance descending)
    - Phase 3: Role-Specific Core Subject & Fundamental CS Knowledge
    - Dynamic adaptive planning without hardcoded depth ladders or keyword FSMs
    - Sound engineering evaluation and contextual consistency checking
    - Fully deterministic mathematical scoring without LLM point hallucination
    """

    MAX_DEPTH = 7

    @classmethod
    def _build_interview_agenda(
        cls,
        resume: Optional[StructuredResume],
        role_profile: Optional[RoleTopicProfile],
        target_role: str,
        target_company: str
    ) -> List[Dict[str, Any]]:
        """
        Constructs the comprehensive Interview Agenda:
        1. All Work Experience items first (in order).
        2. All Projects next, strictly sorted by relevance descending.
        3. Subject Knowledge topics (CS core and role fundamentals).
        
        CRITICAL INVARIANT:
        Do NOT predefine exact question counts (max_questions) or target depth (target_depth).
        Relevance influences exploration priority/budget, but the actual number of questions
        depends on evidence gathered by the AdaptivePlanner.
        """
        agenda = []
        sections = resume.sections_json if (resume and resume.sections_json) else {}

        # 1. Work Experiences (Ask all work experience first, preserving chronology)
        work_exps = sections.get("work_experience", [])
        for idx, exp in enumerate(work_exps):
            company_name = exp.get("company", "Tech Company")
            exp_role = exp.get("role", "Software Engineer")
            title = f"{exp_role} at {company_name}"
            summary = exp.get("summary", "") or exp.get("description", "") or f"Professional experience at {company_name} as {exp_role}."
            key_skills = exp.get("key_skills", [])
            details = f"{summary} Key skills: {', '.join(key_skills)}" if key_skills else summary

            relevance = exp.get("overall_relevance")
            if relevance is None or not isinstance(relevance, (int, float)):
                relevance = 0.75
            else:
                relevance = max(0.1, min(1.0, float(relevance)))

            agenda.append({
                "item_id": exp.get("id", f"exp_{idx}"),
                "item_type": "WORK_EXPERIENCE",
                "phase": "EXPERIENCE_DEFENSE",
                "title": title,
                "company_name": company_name,
                "role_name": exp_role,
                "details": details,
                "relevance": relevance,
                "topic": f"Experience: {company_name}",
                "subtopic": f"{exp_role} Responsibilities & Production Impact"
            })

        # 2. Projects (strictly sorted by overall_relevance descending)
        raw_projects = list(sections.get("projects", []))
        for idx, p in enumerate(raw_projects):
            rel = p.get("overall_relevance")
            if rel is None or not isinstance(rel, (int, float)):
                p["overall_relevance"] = 0.70
            else:
                p["overall_relevance"] = max(0.1, min(1.0, float(rel)))

        sorted_projects = sorted(raw_projects, key=lambda p: float(p.get("overall_relevance", 0.5)), reverse=True)

        for idx, proj in enumerate(sorted_projects):
            p_title = proj.get("title", f"Project {idx+1}")
            p_desc = proj.get("description", "")
            p_tech = proj.get("technologies", [])
            details = f"{p_desc} Tech stack: {', '.join(p_tech)}" if p_tech else p_desc
            relevance = float(proj.get("overall_relevance", 0.70))

            agenda.append({
                "item_id": proj.get("project_id", f"proj_{idx}"),
                "item_type": "PROJECT",
                "phase": "PROJECT_DEFENSE",
                "title": p_title,
                "details": details,
                "relevance": relevance,
                "topic": proj.get("relevant_topics", [p_title])[0] if proj.get("relevant_topics") else p_title,
                "subtopic": "Architecture & Engineering Trade-offs"
            })

        # Safety invariant: Ensure at least one technical experience defense item exists
        # so the candidate is never thrown straight into subject knowledge without defending their background
        if not agenda:
            agenda.append({
                "item_id": "exp_overview",
                "item_type": "WORK_EXPERIENCE",
                "phase": "EXPERIENCE_DEFENSE",
                "title": "Technical Background & Engineering Experience",
                "company_name": target_company,
                "role_name": target_role,
                "details": f"Exploration of technical background, core engineering skills, and system design experience for {target_role}.",
                "relevance": 0.85,
                "topic": "Technical Background",
                "subtopic": "Engineering Responsibilities & Architecture"
            })

        # 3. Subject Knowledge Topics (Begins after all work experiences and projects have concluded)
        subject_items = []
        if role_profile and getattr(role_profile, "subjects_json", None):
            raw_subjects = role_profile.subjects_json
            if isinstance(raw_subjects, list):
                for s_idx, subj in enumerate(raw_subjects):
                    s_name = subj if isinstance(subj, str) else subj.get("subject", f"Core Fundamentals {s_idx+1}")
                    s_topic = subj.get("topic", s_name) if isinstance(subj, dict) else s_name
                    subject_items.append({
                        "item_id": f"subj_{s_idx+1}",
                        "item_type": "SUBJECT_TOPIC",
                        "phase": "SUBJECT_KNOWLEDGE",
                        "title": s_name,
                        "details": f"Fundamental technical assessment on {s_name}.",
                        "relevance": 1.0,
                        "topic": s_topic,
                        "subtopic": "Core Principles & Engineering Trade-offs"
                    })

        if not subject_items:
            role_lower = (target_role or "").lower()
            if "front" in role_lower or "web" in role_lower or "ui" in role_lower:
                subject_items = [
                    {
                        "item_id": "subj_fe_1",
                        "item_type": "SUBJECT_TOPIC",
                        "phase": "SUBJECT_KNOWLEDGE",
                        "title": "Browser Performance & Rendering Lifecycle",
                        "details": "Core DOM rendering pipeline, reflow, repaint, and Core Web Vitals optimization.",
                        "relevance": 1.0,
                        "topic": "Frontend Architecture",
                        "subtopic": "Rendering & Optimization"
                    },
                    {
                        "item_id": "subj_fe_2",
                        "item_type": "SUBJECT_TOPIC",
                        "phase": "SUBJECT_KNOWLEDGE",
                        "title": "State Management & Component Architecture",
                        "details": "Global vs local state patterns, reactivity, and side-effect management.",
                        "relevance": 1.0,
                        "topic": "State Management",
                        "subtopic": "Reactivity & Lifecycle"
                    }
                ]
            elif "ml" in role_lower or "data" in role_lower or "ai" in role_lower:
                subject_items = [
                    {
                        "item_id": "subj_ml_1",
                        "item_type": "SUBJECT_TOPIC",
                        "phase": "SUBJECT_KNOWLEDGE",
                        "title": "Model Serving & Low-Latency Inference",
                        "details": "Production ML deployment, batching, quantization, and caching inference embeddings.",
                        "relevance": 1.0,
                        "topic": "ML Systems",
                        "subtopic": "Inference Optimization"
                    },
                    {
                        "item_id": "subj_ml_2",
                        "item_type": "SUBJECT_TOPIC",
                        "phase": "SUBJECT_KNOWLEDGE",
                        "title": "Feature Pipelines & Drift Monitoring",
                        "details": "Real-time streaming features, data drift detection, and automated retraining triggers.",
                        "relevance": 1.0,
                        "topic": "Data Engineering",
                        "subtopic": "Data Quality & Drift"
                    }
                ]
            else:
                subject_items = [
                    {
                        "item_id": "subj_be_1",
                        "item_type": "SUBJECT_TOPIC",
                        "phase": "SUBJECT_KNOWLEDGE",
                        "title": "Distributed Systems & Scalability",
                        "details": "Consensus, partitioning, replication strategies, and CAP theorem trade-offs.",
                        "relevance": 1.0,
                        "topic": "Distributed Systems",
                        "subtopic": "Partitioning & Consistency"
                    },
                    {
                        "item_id": "subj_be_2",
                        "item_type": "SUBJECT_TOPIC",
                        "phase": "SUBJECT_KNOWLEDGE",
                        "title": "Concurrency & Database Transactions",
                        "details": "ACID guarantees, transaction isolation levels, deadlock mitigation, and connection pooling.",
                        "relevance": 1.0,
                        "topic": "Database Internals",
                        "subtopic": "Transactions & Isolation"
                    }
                ]

        agenda.extend(subject_items)
        return agenda

    @classmethod
    def start_session(
        cls,
        db: Session,
        user_id: str,
        company: str,
        role: str,
        job_type: str = "Full-Time",
        resume: Optional[StructuredResume] = None,
        role_profile: Optional[RoleTopicProfile] = None,
        candidate_name: str = "Candidate"
    ) -> InterviewSession:
        if resume and getattr(resume, "candidate_name", None) and resume.candidate_name != "Candidate":
            candidate_name = resume.candidate_name

        session_id = generate_uuid()

        # 1. Construct ordered experience universe
        agenda = cls._build_interview_agenda(resume, role_profile, role, company)

        # 2. Select initial item: First work experience if available, else first project, else subject stage
        initial_item = agenda[0]

        # 3. Initialize unified InterviewState
        state = InterviewState(session_id=session_id)
        for item in agenda:
            state.register_item(
                item_id=item["item_id"],
                item_type=item.get("item_type", "PROJECT"),
                phase=item.get("phase", "PROJECT_DEFENSE"),
                title=item["title"],
                details=item.get("details", ""),
                relevance_weight=item.get("relevance", 1.0)
            )

        # 4. Register resume claims into state as contextual evidence
        if resume and resume.sections_json:
            ResumeParser.populate_interview_state(state, resume.sections_json)

        # 5. Start initial item in InterviewState
        state.start_item(initial_item["item_id"])

        initial_phase = initial_item.get("phase", "EXPERIENCE_DEFENSE")
        thread_id = initial_item.get("item_id", "thread_1")
        item_title = initial_item.get("title", "Technical Background")
        item_type = initial_item.get("item_type", "PROJECT")

        role_skills = role_profile.required_skills if role_profile else []
        initial_q_id = str(uuid.uuid4())

        # 6. Formulate initial question decision and QuestionProfile
        initial_action = PlannerAction.START_NEXT_ITEM if item_type != "SUBJECT_TOPIC" else PlannerAction.START_SUBJECT_STAGE
        initial_decision = PlannerDecision(
            action=initial_action,
            focus_topic=item_title,
            focus_dimension="responsibilities" if item_type == "WORK_EXPERIENCE" else ("fundamentals" if item_type == "SUBJECT_TOPIC" else "architecture"),
            target_difficulty=0.50,
            target_depth=1,
            rationale=f"Opening inquiry into {item_title}."
        )

        init_profile = QuestionProfile.from_planner_decision(
            question_id=initial_q_id,
            decision=initial_decision,
            item=state.items.get(initial_item["item_id"]),
            phase=initial_phase,
            role=role
        )

        # 7. Generate first question using QuestionGenerator
        generated_q = QuestionGenerator.generate_question(
            planner_action=initial_decision.action,
            question_profile=init_profile,
            state=state,
            current_item=state.items.get(initial_item["item_id"]),
            candidate_claims=[],
            candidate_topics=[],
            relevant_history=[],
            role_objective=role_skills,
            candidate_name=candidate_name,
            company=company,
            role=role,
            llm_client_instance=llm_client,
            persist_in_history=True
        )
        initial_question = generated_q.question_text

        # 8. Create and persist InterviewSession
        session = InterviewSession(
            id=session_id,
            user_id=user_id,
            resume_id=resume.id if resume else None,
            role_topic_profile_id=role_profile.id if role_profile else None,
            company=company,
            role=role,
            job_type=job_type,
            status="IN_PROGRESS",
            current_phase=initial_phase,
            current_thread_id=thread_id,
            current_question_id=initial_q_id,
            current_depth=1,
            transcript_json=[
                {
                    "turn_index": 1,
                    "sender": "INTERVIEWER",
                    "question_id": initial_q_id,
                    "phase": initial_phase,
                    "topic": initial_item.get("topic", item_title),
                    "subtopic": initial_item.get("subtopic", "Responsibilities & Architecture"),
                    "text": initial_question,
                    "depth_level": 1,
                    "timestamp": utc_now().isoformat()
                }
            ],
            agent1_report_json={
                "agenda": agenda,
                "current_agenda_index": 0,
                "unified_state": state.to_dict(),
                "current_question_profile": init_profile.to_dict(),
                "is_clarification_prompt": False
            },
            agent2_report_json={},
            final_report_json={},
            created_at=utc_now()
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    @classmethod
    def process_answer(
        cls,
        db: Session,
        session: InterviewSession,
        user_answer: str
    ) -> Dict[str, Any]:
        """
        Live Adaptive Interview Loop:
        Question
        -> Answer
        -> Normalize answer (TranscriptNormalizer)
        -> Load QuestionProfile
        -> AnswerEvaluator
        -> Update InterviewState
        -> ConsistencyEngine
        -> Reconcile claims/evidence
        -> Deterministic scoring (ScoringPolicy)
        -> Persist InterviewEvidence
        -> AdaptivePlanner
        -> Generate next QuestionProfile
        -> Generate question (QuestionGenerator)
        -> Persist state
        -> Return next turn
        """
        transcript = list(session.transcript_json or [])
        last_interviewer_turn = None
        for turn in reversed(transcript):
            if turn.get("sender") == "INTERVIEWER":
                last_interviewer_turn = turn
                break

        current_depth = session.current_depth or 1
        topic = last_interviewer_turn.get("topic", "System Architecture") if last_interviewer_turn else "Architecture"
        subtopic = last_interviewer_turn.get("subtopic", "Trade-offs") if last_interviewer_turn else "Trade-offs"
        question_text = last_interviewer_turn.get("text", "") if last_interviewer_turn else ""

        # Load models
        resume = db.query(StructuredResume).filter(StructuredResume.id == session.resume_id).first() if session.resume_id else None
        role_profile = db.query(RoleTopicProfile).filter(RoleTopicProfile.id == session.role_topic_profile_id).first() if session.role_topic_profile_id else None
        candidate_name = resume.candidate_name if (resume and resume.candidate_name) else "Candidate"
        role_skills = role_profile.required_skills if role_profile else []

        agent1_meta = dict(session.agent1_report_json or {})

        # 1. Restore unified InterviewState
        state = InterviewState.from_dict(agent1_meta.get("unified_state"), session_id=session.id)
        if not state.items:
            agenda = list(agent1_meta.get("agenda") or [])
            if not agenda:
                agenda = cls._build_interview_agenda(resume, role_profile, session.role, session.company)
            for it in agenda:
                state.register_item(
                    item_id=it["item_id"],
                    item_type=it.get("item_type", "PROJECT"),
                    phase=it.get("phase", "PROJECT_DEFENSE"),
                    title=it["title"],
                    details=it.get("details", ""),
                    relevance_weight=it.get("relevance", 1.0)
                )
            if state.item_order:
                state.start_item(state.item_order[0])

        active_item = state.items.get(state.active_item_id) if state.active_item_id else None

        # 2. Normalize transcript (speech-to-text / acoustic corrections)
        cleaned_answer, was_autocorrected = TranscriptNormalizer.normalize(user_answer)

        # 3. Rehydrate QuestionProfile for the question being answered
        raw_profile = agent1_meta.get("current_question_profile")
        current_q_profile = None
        if raw_profile:
            try:
                current_q_profile = QuestionProfile.from_dict(raw_profile)
            except Exception:
                current_q_profile = None

        if not current_q_profile:
            current_q_profile = QuestionProfile(
                question_id=session.current_question_id or str(uuid.uuid4()),
                objective=f"Evaluate technical explanation on {topic}",
                phase=session.current_phase,
                item_id=state.active_item_id,
                item_type=active_item.item_type if active_item else "PROJECT",
                topic=topic,
                subtopic=subtopic,
                difficulty=0.50,
                follow_up_depth=current_depth
            )

        # 4. Prepare resume context string
        resume_context_str = ""
        if resume and resume.sections_json:
            sec = resume.sections_json
            work_strs = [f"- {w.get('role')} at {w.get('company')}: {w.get('summary', '') or w.get('description', '')}" for w in sec.get("work_experience", [])]
            proj_strs = [f"- {p.get('title')}: {p.get('description', '')} (Tech: {', '.join(p.get('technologies', []))})" for p in sec.get("projects", [])]
            nl = "\n"
            resume_context_str = f"Work Experience:{nl}{nl.join(work_strs)}{nl}{nl}Projects:{nl}{nl.join(proj_strs)}"

        role_profile_dict = {
            "role": session.role,
            "company": session.company,
            "required_skills": role_skills
        }

        # 5. Semantic Answer Evaluation (AnswerEvaluator)
        eval_result: SemanticEvaluationResult = AnswerEvaluator.evaluate(
            question_profile=current_q_profile,
            candidate_answer=cleaned_answer,
            history=transcript,
            state=state,
            resume_context=resume_context_str,
            role_profile=role_profile_dict,
            llm_client_instance=llm_client
        )

        # 6. Consistency Engine (discrepancy & contradiction detection)
        cons_result: ConsistencyAnalysisResult = ConsistencyEngine.analyze(
            eval_result=eval_result,
            state=state,
            current_item_id=state.active_item_id,
            current_item_title=active_item.title if active_item else None,
            role_context=session.role,
            current_turn=len(transcript) // 2 + 1,
            llm_client=llm_client
        )

        # 7. Reconcile claims and contradictions
        if cons_result.has_discrepancies:
            for d in cons_result.discrepancies:
                c_a = d.claim_references[0] if d.claim_references else f"claim_{uuid.uuid4().hex[:6]}"
                c_b = d.claim_references[1] if len(d.claim_references) > 1 else f"claim_{uuid.uuid4().hex[:6]}"
                state.record_contradiction(
                    claim_id_a=c_a,
                    claim_id_b=c_b,
                    description=d.discrepancy_description,
                    item_id=d.affected_item or state.active_item_id,
                    turn_index=len(transcript) // 2 + 1
                )
                if d.clarification_recommended:
                    eval_result.clarification_needed = True
                    eval_result.clarification_reason = d.discrepancy_description

        # Update State with candidate's claims & topics
        for claim_ext in eval_result.candidate_claims:
            state.record_candidate_claim(
                statement=claim_ext.statement,
                item_id=state.active_item_id,
                entity=claim_ext.entity,
                attribute=claim_ext.attribute_or_action,
                topics=eval_result.candidate_topics,
                verified=claim_ext.causality_valid
            )
        for t in eval_result.candidate_topics:
            state.add_candidate_topic(t)

        # Register candidate-introduced entities as candidate topics and claims
        stopwords = {"when", "then", "also", "after", "before", "while", "here", "there", "this", "that", "with", "from"}
        for ent in (eval_result.entities or []):
            if len(ent) > 2 and ent.lower() not in stopwords:
                state.add_candidate_topic(ent)
                has_ent_claim = any(c.entity and c.entity.lower() == ent.lower() for c in state.claims.values())
                if not has_ent_claim:
                    state.record_candidate_claim(
                        statement=f"Candidate introduced and discussed {ent}.",
                        item_id=state.active_item_id,
                        entity=ent,
                        attribute="introduced",
                        topics=[ent],
                        verified=True
                    )

        # Record candidate mention of resume claims
        if eval_result.entities:
            for c_id, clm in state.claims.items():
                if clm.source == ClaimSource.RESUME and clm.status == ClaimStatus.UNEXPLORED:
                    if clm.entity and any(e.lower() == clm.entity.lower() for e in eval_result.entities):
                        state.record_candidate_mention_of_resume_claim(c_id, len(transcript) // 2 + 1)

        # Record completed turn in InterviewState
        turn_idx = len(transcript) // 2 + 1
        state.record_turn(
            question_id=current_q_profile.question_id,
            turn_index=turn_idx,
            topic=current_q_profile.topic or topic,
            question_text=question_text,
            subtopic=current_q_profile.subtopic or subtopic,
            question_profile=current_q_profile
        )

        # 8. Deterministic Scoring (ScoringPolicy)
        was_clarification_prompt = agent1_meta.get("is_clarification_prompt", False)
        if was_clarification_prompt:
            # Clarification prompt itself is not counted as a normal scored question (0/0)
            earned_pts = 0.0
            possible_pts = 0.0
            severity = "NEUTRAL"
            is_scored = False
            agent1_meta["is_clarification_prompt"] = False
            for c in state.contradictions:
                if c.status == "OPEN" and (not c.item_id or c.item_id == state.active_item_id):
                    state.resolve_contradiction(
                        contradiction_id=c.contradiction_id,
                        resolution_notes=f"Candidate clarified: {cleaned_answer[:120]}",
                        turn_index=turn_idx
                    )
        else:
            earned_pts, possible_pts, severity = ScoringPolicy.calculate_turn_score(
                eval_result=eval_result,
                question_profile=current_q_profile,
                fallback_difficulty=0.50
            )
            is_scored = True

        e_score = ScoringPolicy.compute_semantic_evidence_score(eval_result)
        if eval_result.is_non_answer:
            quality_band = "Weak"
        elif e_score >= 0.85:
            quality_band = "Excellent"
        elif e_score >= 0.70:
            quality_band = "Good"
        elif e_score >= 0.40:
            quality_band = "Average"
        else:
            quality_band = "Weak"

        # 9. Persist InterviewEvidence audit record
        evidence = InterviewEvidence(
            id=generate_uuid(),
            session_id=session.id,
            project_id_or_topic=(state.active_item_id or session.current_thread_id or "general")[:500],
            question_id=str(current_q_profile.question_id)[:100],
            follow_up_index=max(0, current_depth - 1),
            topic=(current_q_profile.topic or topic)[:500],
            subtopic=(current_q_profile.subtopic or subtopic)[:500],
            user_answer=cleaned_answer,
            expected_concept=current_q_profile.objective,
            detected_gap=eval_result.missing_evidence[0] if eval_result.missing_evidence else None,
            severity=severity,
            earned_points=earned_pts,
            possible_points=possible_pts,
            evaluator_reason=eval_result.reasoning_summary,
            evidence_ref=f"EV-{session.current_phase[:3]}-{current_depth}-{str(uuid.uuid4())[:6]}",
            created_at=utc_now()
        )
        db.add(evidence)
        db.commit()

        # Add candidate turn to transcript
        transcript.append({
            "turn_index": len(transcript) + 1,
            "sender": "CANDIDATE",
            "text": cleaned_answer,
            "raw_text": user_answer if was_autocorrected else None,
            "timestamp": utc_now().isoformat()
        })

        # 10. Update current item evidence & coverage
        for t in eval_result.candidate_topics:
            if t not in state.topics_covered:
                state.topics_covered.append(t)
            if active_item and hasattr(active_item, "topics_covered") and t not in active_item.topics_covered:
                active_item.topics_covered.append(t)
        if active_item:
            if eval_result.correctness >= 0.75:
                for c in eval_result.candidate_claims:
                    if c.statement not in active_item.claims_verified:
                        active_item.claims_verified.append(c.statement)

        # 11. Adaptive Planner determines next action
        decision: PlannerDecision = AdaptivePlanner.plan_next_action(
            state=state,
            latest_eval=eval_result,
            current_item=state.items.get(state.active_item_id),
            role_objectives=role_skills
        )

        state.record_planner_action(
            turn_index=turn_idx,
            action=decision.action.value,
            focus_topic=decision.focus_topic,
            focus_claim_id=decision.focus_claim_id,
            target_difficulty=str(decision.target_difficulty),
            rationale=decision.rationale,
            focus_dimension=decision.focus_dimension
        )

        is_completed = False
        next_phase = state.current_phase
        next_depth = decision.target_depth
        next_topic = decision.focus_topic
        next_subtopic = decision.focus_dimension.capitalize()
        next_q_id = str(uuid.uuid4())

        # 12. Handle Interview Conclusion vs Next Turn Question Generation
        if decision.action == PlannerAction.END_INTERVIEW or state.current_phase == "COMPLETED":
            next_phase = "COMPLETED"
            is_completed = True
            session.status = "COMPLETED"
            session.completed_at = utc_now()
            next_question_text = (
                f"Thank you so much, {candidate_name}! That concludes our technical interview today. "
                "We covered your professional work experience, technical projects, and fundamental software engineering principles in depth. "
                "I've compiled your full evidence-backed performance metrics and comprehensive interview report."
            )
            cls._generate_final_reports(db, session, state)
            agent1_meta["current_question_profile"] = None
            agent1_meta["is_clarification_prompt"] = False
            next_active_item = None
            next_dim = None
            next_diff = None
            next_is_clarification = False
            next_is_scored = False
        else:
            updated_active_item = state.items.get(state.active_item_id)
            next_active_item = updated_active_item
            
            # Build QuestionProfile for the upcoming turn
            next_q_profile = QuestionProfile.from_planner_decision(
                question_id=next_q_id,
                decision=decision,
                item=updated_active_item,
                phase=next_phase,
                role=session.role
            )
            agent1_meta["current_question_profile"] = next_q_profile.to_dict()
            next_is_clarification = (decision.action in (PlannerAction.CLARIFY_CONTRADICTION, PlannerAction.VERIFY_UNSUPPORTED_CLAIM))
            next_is_scored = not next_is_clarification
            agent1_meta["is_clarification_prompt"] = next_is_clarification
            next_dim = decision.focus_dimension
            next_diff = next_q_profile.difficulty

            # Generate question using QuestionGenerator
            gen_next = QuestionGenerator.generate_question(
                planner_action=decision.action,
                question_profile=next_q_profile,
                state=state,
                current_item=updated_active_item,
                candidate_claims=eval_result.candidate_claims,
                candidate_topics=eval_result.candidate_topics,
                relevant_history=transcript,
                role_objective=role_skills,
                evidence_gaps=eval_result.missing_evidence,
                contradiction_context=eval_result.clarification_reason if eval_result.clarification_needed else None,
                candidate_name=candidate_name,
                company=session.company,
                role=session.role,
                llm_client_instance=llm_client,
                persist_in_history=True,
                latest_eval=eval_result
            )
            next_question_text = gen_next.question_text

        agent1_meta["unified_state"] = state.to_dict()
        session.agent1_report_json = agent1_meta

        # Append next interviewer turn to transcript
        transcript.append({
            "turn_index": len(transcript) + 1,
            "sender": "INTERVIEWER",
            "question_id": next_q_id,
            "phase": next_phase,
            "topic": next_topic,
            "subtopic": next_subtopic,
            "text": next_question_text,
            "depth_level": next_depth,
            "timestamp": utc_now().isoformat()
        })

        session.current_phase = next_phase
        session.current_depth = next_depth
        session.current_question_id = next_q_id
        session.current_thread_id = state.active_item_id or session.current_thread_id
        session.transcript_json = transcript
        db.commit()
        db.refresh(session)

        item_id = next_active_item.item_id if next_active_item else state.active_item_id
        item_type = next_active_item.item_type if next_active_item else None
        item_title = next_active_item.title if next_active_item else None
        current_item_dict = {"item_id": item_id, "item_type": item_type, "title": item_title} if item_id and item_title else None

        return {
            "session_id": session.id,
            "phase": next_phase,
            "current_topic": next_topic,
            "question_id": next_q_id,
            "question_text": next_question_text,
            "next_question": next_question_text,
            "depth_level": next_depth,
            "max_depth": cls.MAX_DEPTH,
            "is_completed": is_completed,
            "current_item_id": item_id,
            "current_item_type": item_type,
            "current_item_title": item_title,
            "current_item": current_item_dict,
            "current_dimension": next_dim,
            "depth_dimension": next_dim,
            "target_difficulty": next_diff,
            "question_difficulty": next_diff,
            "is_clarification": next_is_clarification,
            "is_scored": next_is_scored,
            "earned_points": earned_pts,
            "possible_points": possible_pts,
            "evidence_score": round(e_score, 3) if is_scored else 0.0,
            "concise_evaluation_summary": eval_result.reasoning_summary,
            "eval_previous": {
                "quality_band": quality_band,
                "earned_points": earned_pts,
                "possible_points": possible_pts,
                "severity": severity,
                "feedback": eval_result.reasoning_summary,
                "detected_gap": eval_result.missing_evidence[0] if eval_result.missing_evidence else None,
                "is_scored": is_scored,
                "evidence_score": round(e_score, 3) if is_scored else 0.0,
                "concise_evaluation_summary": eval_result.reasoning_summary
            }
        }

    @classmethod
    def _generate_final_reports(
        cls,
        db: Session,
        session: InterviewSession,
        state: Optional[InterviewState] = None
    ) -> None:
        """
        Generates 100% evidence-backed final report:
        - Overall Experience Score /100 (Relevance-weighted across all Work Experiences & Projects)
        - CS Core & Subject Knowledge Score /100
        - Separate card for every work experience and project with claim status breakdown
        - Evidence-backed subject mastery, strengths, weaknesses, and recommendations
        Backed by stored InterviewEvidence records.
        """
        all_evidence = db.query(InterviewEvidence).filter(
            InterviewEvidence.session_id == session.id
        ).all()

        if state is None:
            agent1_meta = session.agent1_report_json or {}
            state = InterviewState.from_dict(agent1_meta.get("unified_state"), session_id=session.id)

        final_report = ReportGenerator.generate_report(session, state, all_evidence)

        final_exp_score = final_report.get("resume_related_score", 0.0)
        final_subj_score = final_report.get("subject_knowledge_score")
        if final_subj_score is None:
            final_subj_score = 0.0

        session.agent1_report_json = {"score": final_exp_score, "star_rating": round(final_exp_score / 20.0, 2)}
        session.agent2_report_json = {"score": final_subj_score}
        session.final_report_json = final_report
        db.commit()
