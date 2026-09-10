import json
import uuid
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from backend.app.models.models import (
    InterviewSession, InterviewEvidence, StructuredResume, RoleTopicProfile, generate_uuid, utc_now
)
from backend.app.engines.scoring_engine import ScoringEngine
from backend.app.engines.follow_up_fsm import FollowUpFSM, FSMAction, QualityBand
from backend.app.engines.evaluator_registry import EvaluatorRegistry
from backend.app.engines.web_search import WebSearchEngine
from backend.app.engines.transcript_normalizer import TranscriptNormalizer
from backend.app.llm.client import llm_client

class InterviewAgent:
    """
    Multi-Turn AI Interview Subsystem:
    - Phase 1: Project & Experience Defense (conversational probing tailored to candidate's actual projects)
    - Phase 2: Role-Specific Core Subject & Fundamental Knowledge
    - Human-like conversational dialogue (ChatGPT style, natural transitions, empathetic and sharp)
    - Sound engineering evaluation (no rigid overfitting, rewards valid architectural choices)
    - Real-time web-search grounding for company & role standards
    - Evidence trails recorded for every turn with deterministic scoring
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
        Constructs the comprehensive Resume Defense Agenda:
        1. All Work Experience items first (in order, exploring responsibilities, achievements, and stack).
        2. All Projects next, strictly sorted by overall_relevance in descending order.
        3. Dynamic number of questions and target depth based on relevance to the target role:
           - High Relevance (>= 0.80): 3-4 questions, target_depth = 3-4
           - Medium Relevance (0.50 <= R < 0.80): 2 questions, target_depth = 2
           - Low Relevance (< 0.50): 1 question, target_depth = 1
        """
        agenda = []
        sections = resume.sections_json if (resume and resume.sections_json) else {}

        # 1. Work Experiences (Ask first, covering each role/company in detail)
        work_exps = sections.get("work_experience", [])
        for idx, exp in enumerate(work_exps):
            company_name = exp.get("company", "Tech Company")
            exp_role = exp.get("role", "Software Engineer")
            title = f"{exp_role} at {company_name}"
            summary = exp.get("summary", "") or f"Professional experience at {company_name} as {exp_role}."
            key_skills = exp.get("key_skills", [])
            details = f"{summary} Key skills: {', '.join(key_skills)}" if key_skills else summary

            relevance = exp.get("overall_relevance")
            if relevance is None or not isinstance(relevance, (int, float)):
                relevance = max(0.60, round(0.94 - (idx * 0.08), 2))
            else:
                relevance = float(relevance)

            if relevance >= 0.80:
                max_q = 3
                target_depth = 3
            elif relevance >= 0.50:
                max_q = 2
                target_depth = 2
            else:
                max_q = 1
                target_depth = 1

            agenda.append({
                "item_id": exp.get("id", f"exp_{idx}"),
                "item_type": "WORK_EXPERIENCE",
                "phase": "EXPERIENCE_DEFENSE",
                "title": title,
                "company_name": company_name,
                "role_name": exp_role,
                "details": details,
                "relevance": relevance,
                "max_questions": max_q,
                "target_depth": target_depth,
                "questions_asked": 0,
                "topic": f"Experience: {company_name}",
                "subtopic": f"{exp_role} Responsibilities & Production Impact"
            })

        # 2. Projects (sorted by overall_relevance descending)
        raw_projects = list(sections.get("projects", []))
        for idx, p in enumerate(raw_projects):
            rel = p.get("overall_relevance")
            if rel is None or not isinstance(rel, (int, float)):
                p["overall_relevance"] = max(0.50, round(0.92 - (idx * 0.1), 2))
            else:
                p["overall_relevance"] = float(rel)

        # Sort in descending order of relevance (highest relevance first)
        sorted_projects = sorted(raw_projects, key=lambda p: float(p.get("overall_relevance", 0.5)), reverse=True)

        for idx, proj in enumerate(sorted_projects):
            p_title = proj.get("title", f"Project {idx+1}")
            p_desc = proj.get("description", "")
            p_tech = proj.get("technologies", [])
            details = f"{p_desc} Tech stack: {', '.join(p_tech)}" if p_tech else p_desc
            relevance = float(proj.get("overall_relevance", 0.70))

            if relevance >= 0.80:
                max_q = 3
                target_depth = 3
            elif relevance >= 0.50:
                max_q = 2
                target_depth = 2
            else:
                max_q = 1
                target_depth = 1

            agenda.append({
                "item_id": proj.get("project_id", f"proj_{idx}"),
                "item_type": "PROJECT",
                "phase": "PROJECT_DEFENSE",
                "title": p_title,
                "details": details,
                "relevance": relevance,
                "max_questions": max_q,
                "target_depth": target_depth,
                "questions_asked": 0,
                "topic": proj.get("relevant_topics", [p_title])[0] if proj.get("relevant_topics") else p_title,
                "subtopic": "Architecture & Engineering Trade-offs"
            })

        # Fallback if both were completely empty
        if not agenda:
            agenda.append({
                "item_id": "fallback_proj_1",
                "item_type": "PROJECT",
                "phase": "PROJECT_DEFENSE",
                "title": "Flagship Engineering Project",
                "details": "Core software engineering project demonstrating system design and implementation.",
                "relevance": 0.90,
                "max_questions": 3,
                "target_depth": 3,
                "questions_asked": 0,
                "topic": "System Architecture",
                "subtopic": "Architecture & Engineering Trade-offs"
            })

        return agenda

    @classmethod
    def start_session(
        cls,
        db: Session,
        user_id: str,
        company: str,
        role: str,
        job_type: str = "Full-Time",
        resume: StructuredResume = None,
        role_profile: RoleTopicProfile = None,
        candidate_name: str = "Candidate"
    ) -> InterviewSession:
        if resume and getattr(resume, "candidate_name", None) and resume.candidate_name != "Candidate":
            candidate_name = resume.candidate_name

        # Build full resume defense agenda (Work Experience first, then Projects sorted by relevance)
        agenda = cls._build_interview_agenda(resume, role_profile, role, company)
        initial_item = agenda[0]
        initial_item["questions_asked"] = 1

        initial_phase = initial_item.get("phase", "EXPERIENCE_DEFENSE")
        thread_id = initial_item.get("item_id", "thread_1")
        item_title = initial_item.get("title", "Technical Background")
        item_details = initial_item.get("details", "")
        item_type = initial_item.get("item_type", "PROJECT")

        role_skills = role_profile.required_skills if role_profile else []
        web_trends = WebSearchEngine.search_interview_trends(company, role, max_results=3)

        initial_q_id = str(uuid.uuid4())
        dynamic_init_q = None
        try:
            dynamic_init_q = llm_client.generate_interview_question(
                candidate_name=candidate_name,
                company=company,
                role=role,
                phase=initial_phase,
                current_depth=1,
                project_title=item_title,
                project_details=item_details,
                candidate_last_answer=None,
                previous_question=None,
                role_skills=role_skills,
                web_trends=web_trends,
                item_type=item_type
            )
        except Exception as e:
            print(f"[InterviewAgent] Dynamic initial question generation fallback: {e}")

        if item_type == "WORK_EXPERIENCE":
            default_init_q = (
                f"Hey {candidate_name}, welcome! Great to meet you for the {role} interview at {company}. "
                f"To kick things off, could you give me an overview of your work as a {item_title} and what primary engineering challenges your team was solving?"
            )
        else:
            default_init_q = (
                f"Hey {candidate_name}, welcome! Great to meet you for the {role} interview at {company}. "
                f"To kick things off, could you give me a brief, high-level overview of '{item_title}' and what core problem it solves?"
            )

        initial_question = dynamic_init_q or default_init_q

        session = InterviewSession(
            id=generate_uuid(),
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
                "current_agenda_index": 0
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
        Processes candidate's response:
        1. Evaluates qualitative answer quality band (Excellent/Good/Average/Weak/Incorrect) with sound engineering logic.
        2. Applies deterministic scoring engine for points and penalty curves.
        3. Saves an interview_evidence audit record.
        4. Queries adaptive follow-up FSM to determine next depth or thread pivot.
        5. Advances phase from PROJECT_DEFENSE to SUBJECT_KNOWLEDGE or COMPLETED.
        6. Generates natural, human-like follow-up question (ChatGPT style) reacting to candidate's answer.
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
        q_id = session.current_question_id or str(uuid.uuid4())
        question_text = last_interviewer_turn.get("text", "") if last_interviewer_turn else ""

        # Load contextual models
        resume = db.query(StructuredResume).filter(StructuredResume.id == session.resume_id).first() if session.resume_id else None
        role_profile = db.query(RoleTopicProfile).filter(RoleTopicProfile.id == session.role_topic_profile_id).first() if session.role_topic_profile_id else None
        candidate_name = resume.candidate_name if (resume and resume.candidate_name) else "Candidate"

        # Retrieve or initialize agenda
        agent1_meta = dict(session.agent1_report_json or {})
        agenda = list(agent1_meta.get("agenda") or [])
        if not agenda:
            agenda = cls._build_interview_agenda(resume, role_profile, session.role, session.company)
            agent1_meta["agenda"] = agenda
            agent1_meta["current_agenda_index"] = 0

        curr_idx = agent1_meta.get("current_agenda_index", 0)
        curr_idx = max(0, min(curr_idx, len(agenda) - 1))
        active_item = agenda[curr_idx]

        item_title = active_item.get("title", "Technical Defense")
        item_details = active_item.get("details", "")
        item_type = active_item.get("item_type", "PROJECT")
        role_skills = role_profile.required_skills if role_profile else []
        web_trends = WebSearchEngine.search_interview_trends(session.company, session.role, max_results=3)

        # 0. Autocorrect & normalize speech-to-text transcript typos and phonetic sound-alikes
        cleaned_answer, was_autocorrected = TranscriptNormalizer.normalize(user_answer)

        # Check if current turn is a 2nd-go clarification attempt
        pending_clarification = agent1_meta.get("pending_clarification")
        is_clarification_turn = bool(pending_clarification)
        missing_specs_context = pending_clarification.get("missing_specs", "") if is_clarification_turn else ""

        # 1. Evaluate qualitative band based on candidate's reasoning depth and classify question difficulty
        (
            quality_band,
            detected_gap,
            reason,
            expected_concept,
            difficulty,
            actual_topic,
            score_pct,
            suggested_possible,
            suggested_earned,
            is_non_answer,
            needs_specification_clarification,
            clarification_prompt_focus
        ) = cls._evaluate_response_quality(
            user_answer=cleaned_answer,
            question_text=question_text,
            topic=topic,
            phase=session.current_phase,
            depth=current_depth,
            role=session.role,
            company=session.company,
            project_context=f"{item_type}: {item_title}. {item_details}",
            is_clarification_attempt=is_clarification_turn,
            missing_specs_context=missing_specs_context
        )

        if actual_topic and len(actual_topic.strip()) > 3 and "none" not in actual_topic.lower():
            topic = actual_topic.strip()

        # Check if we should trigger 2nd-go precision clarification (Attempt 1 with missing specs)
        if not is_clarification_turn and needs_specification_clarification and not is_non_answer:
            missing_focus = clarification_prompt_focus or detected_gap or expected_concept
            clarification_question = llm_client.generate_specification_clarification_question(
                candidate_name=candidate_name,
                company=session.company,
                role=session.role,
                project_title=item_title,
                candidate_answer=cleaned_answer,
                expected_concept=expected_concept,
                missing_specs=missing_focus
            )

            # Store pending clarification state so Attempt 2 is evaluated with asymmetric 2nd-go scoring
            agent1_meta["pending_clarification"] = {
                "topic": topic,
                "subtopic": subtopic,
                "depth": current_depth,
                "difficulty": difficulty,
                "initial_question": question_text,
                "initial_answer": cleaned_answer,
                "expected_concept": expected_concept,
                "missing_specs": missing_focus,
                "item_id": active_item.get("item_id", topic)
            }
            session.agent1_report_json = agent1_meta

            # Add candidate turn to transcript
            transcript.append({
                "turn_index": len(transcript) + 1,
                "sender": "CANDIDATE",
                "text": cleaned_answer,
                "raw_text": user_answer if was_autocorrected else None,
                "timestamp": utc_now().isoformat()
            })

            # Add interviewer clarification turn to transcript
            clar_q_id = str(uuid.uuid4())
            transcript.append({
                "turn_index": len(transcript) + 1,
                "sender": "INTERVIEWER",
                "question_id": clar_q_id,
                "phase": session.current_phase,
                "topic": topic,
                "subtopic": subtopic,
                "text": clarification_question,
                "depth_level": current_depth,
                "is_clarification_prompt": True,
                "timestamp": utc_now().isoformat()
            })

            session.transcript_json = transcript
            session.current_question_id = clar_q_id
            db.commit()
            db.refresh(session)

            return {
                "session_id": session.id,
                "phase": session.current_phase,
                "current_topic": topic,
                "question_id": clar_q_id,
                "question_text": clarification_question,
                "depth_level": current_depth,
                "max_depth": cls.MAX_DEPTH,
                "is_completed": False,
                "is_clarification_prompt": True,
                "eval_previous": {
                    "quality_band": "Specification Clarification",
                    "earned_points": 0.0,
                    "possible_points": 0.0,
                    "severity": "PENDING",
                    "feedback": f"Overview noted. Please specify concrete implementation details: {missing_focus}",
                    "detected_gap": None,
                    "is_clarification_prompt": True
                }
            }

        # 2. Intelligent points calculation with context-aware asymmetric risk/reward
        earned_pts, possible_pts, severity = ScoringEngine.evaluate_quality_points(
            quality_band=quality_band,
            depth_level=current_depth,
            difficulty=difficulty,
            score_pct=score_pct,
            suggested_possible=suggested_possible,
            suggested_earned=suggested_earned,
            is_non_answer=is_non_answer,
            is_clarification_attempt=is_clarification_turn
        )

        evaluator_reason_text = reason
        if is_clarification_turn:
            evaluator_reason_text = f"[2nd-Go Evaluation] {reason}"
            agent1_meta.pop("pending_clarification", None)

        # 3. Store Evidence Record
        evidence = InterviewEvidence(
            id=generate_uuid(),
            session_id=session.id,
            project_id_or_topic=session.current_thread_id or active_item.get("item_id", topic),
            question_id=q_id,
            follow_up_index=current_depth - 1,
            topic=topic,
            subtopic=subtopic,
            user_answer=cleaned_answer,
            expected_concept=expected_concept,
            detected_gap=detected_gap,
            severity=severity,
            earned_points=earned_pts,
            possible_points=possible_pts,
            evaluator_reason=evaluator_reason_text,
            evidence_ref=f"EV-{session.current_phase[:3]}-{current_depth}-{q_id[:6]}",
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

        # 4. Check if current agenda item is finished
        questions_asked_so_far = active_item.get("questions_asked", 1)
        max_q = active_item.get("max_questions", 3)
        target_depth = active_item.get("target_depth", 3)

        is_item_done = False
        if questions_asked_so_far >= max_q or current_depth >= target_depth:
            is_item_done = True
        elif (is_non_answer or quality_band in ["Incorrect", "Weak"]) and current_depth >= 2:
            is_item_done = True

        next_phase = session.current_phase
        is_completed = False
        next_question_text = ""
        next_q_id = str(uuid.uuid4())
        next_topic = topic
        next_subtopic = subtopic

        if is_item_done:
            next_idx = curr_idx + 1
            if next_idx < len(agenda):
                # Transition to next agenda item (covering next work experience or next relevance-sorted project)
                agent1_meta["current_agenda_index"] = next_idx
                next_item = agenda[next_idx]
                next_item["questions_asked"] = 1
                agent1_meta["agenda"] = agenda

                next_phase = next_item.get("phase", "PROJECT_DEFENSE")
                next_depth = 1
                next_topic = next_item.get("topic", next_item["title"])
                next_subtopic = next_item.get("subtopic", "Technical Architecture")
                session.current_thread_id = next_item.get("item_id", f"item_{next_idx}")

                dynamic_trans_q = None
                try:
                    dynamic_trans_q = llm_client.generate_interview_question(
                        candidate_name=candidate_name,
                        company=session.company,
                        role=session.role,
                        phase=next_phase,
                        current_depth=1,
                        project_title=next_item["title"],
                        project_details=next_item["details"],
                        candidate_last_answer=user_answer,
                        previous_question=question_text,
                        quality_band=quality_band,
                        detected_gap=detected_gap,
                        role_skills=role_skills,
                        web_trends=web_trends,
                        item_type=next_item.get("item_type", "PROJECT"),
                        transition_from=item_title
                    )
                except Exception as e:
                    print(f"[InterviewAgent] Dynamic transition question generation failed: {e}")

                if next_item.get("item_type") == "PROJECT" and item_type == "WORK_EXPERIENCE":
                    fallback_trans = (
                        f"That gives me a great picture of your professional experience, {candidate_name}! "
                        f"Let's transition now to your technical projects. Looking at your resume, '{next_item['title']}' stands out—could you give me a brief overview of what problem it was designed to solve?"
                    )
                elif next_item.get("item_type") == "WORK_EXPERIENCE":
                    fallback_trans = (
                        f"Thanks for explaining your work at {item_title}, {candidate_name}! "
                        f"Next, I'd like to ask about your time as a {next_item['title']}—what were your primary technical responsibilities there?"
                    )
                else:
                    fallback_trans = (
                        f"Awesome, that makes the architecture of {item_title} clear. "
                        f"Let's move on to your next project: '{next_item['title']}'. Could you walk me through what this project does and why you built it?"
                    )
                next_question_text = dynamic_trans_q or fallback_trans
            else:
                # All work experiences and all projects in the agenda have been completed!
                next_phase = "COMPLETED"
                is_completed = True
                session.status = "COMPLETED"
                session.completed_at = utc_now()
                next_question_text = (
                    f"Thank you so much, {candidate_name}! That concludes our technical interview today. "
                    "We covered your professional work experience and all your technical projects in depth. "
                    "I've compiled your full evidence-backed performance metrics and comprehensive interview report."
                )
                cls._generate_final_reports(db, session)
        else:
            # Stay on the current item for another follow-up question
            active_item["questions_asked"] = questions_asked_so_far + 1
            agent1_meta["agenda"] = agenda
            next_phase = active_item.get("phase", session.current_phase)
            next_depth = min(cls.MAX_DEPTH, current_depth + 1)
            next_topic = active_item.get("topic", topic)
            next_subtopic = active_item.get("subtopic", subtopic)

            next_question_text = cls._generate_follow_up_question(
                session=session,
                topic=next_topic,
                depth=next_depth,
                candidate_answer=user_answer,
                phase=next_phase,
                previous_question=question_text,
                quality_band=quality_band,
                detected_gap=detected_gap,
                candidate_name=candidate_name,
                project_title=item_title,
                project_details=item_details,
                role_skills=role_skills,
                web_trends=web_trends,
                item_type=item_type
            )

        session.agent1_report_json = agent1_meta

        # Append next interviewer turn if not completed
        transcript.append({
            "turn_index": len(transcript) + 1,
            "sender": "INTERVIEWER",
            "question_id": next_q_id,
            "phase": next_phase,
            "topic": next_topic,
            "subtopic": "Situational reasoning" if next_phase == "PROJECT_DEFENSE" else "Fundamental algorithms",
            "text": next_question_text,
            "depth_level": next_depth,
            "timestamp": utc_now().isoformat()
        })

        session.current_phase = next_phase
        session.current_depth = next_depth
        session.current_question_id = next_q_id
        session.transcript_json = transcript
        db.commit()
        db.refresh(session)

        return {
            "session_id": session.id,
            "phase": next_phase,
            "current_topic": next_topic,
            "question_id": next_q_id,
            "question_text": next_question_text,
            "depth_level": next_depth,
            "max_depth": cls.MAX_DEPTH,
            "is_completed": is_completed,
            "eval_previous": {
                "quality_band": quality_band,
                "earned_points": earned_pts,
                "possible_points": possible_pts,
                "severity": severity,
                "feedback": reason,
                "detected_gap": detected_gap
            }
        }

    @classmethod
    def _evaluate_response_quality(
        cls,
        user_answer: str,
        question_text: str,
        topic: str,
        phase: str,
        depth: int = 1,
        role: str = "Software Engineer",
        company: str = "Target Company",
        project_context: str = "",
        is_clarification_attempt: bool = False,
        missing_specs_context: str = ""
    ) -> Tuple[str, Optional[str], str, str, str, str, Optional[float], Optional[float], Optional[float], bool, bool, Optional[str]]:
        """
        Evaluates candidate's engineering reasoning:
        (quality_band, detected_gap, evaluator_reason, expected_concept, question_difficulty, actual_topic, score_percentage, suggested_possible, suggested_earned, is_non_answer, needs_specification_clarification, clarification_prompt_focus)
        Uses sound engineering judgment: does not overfit to arbitrary reference answers.
        """
        ans = user_answer.strip()
        ans_lower = ans.lower()
        word_count = len(ans.split())
        q_lower = question_text.lower()

        # 0. Live LLM evaluation with sound engineering guidance & intrinsic difficulty detection
        try:
            llm_eval = llm_client.evaluate_candidate_answer(
                question_text=question_text,
                topic=topic,
                candidate_answer=user_answer,
                depth=depth,
                role=role,
                company=company,
                project_context=project_context,
                phase=phase,
                is_clarification_attempt=is_clarification_attempt,
                missing_specs_context=missing_specs_context
            )
            if llm_eval and "quality_band" in llm_eval:
                diff = llm_eval.get("question_difficulty", "medium").lower()
                topic_detected = llm_eval.get("actual_topic", topic)
                score_pct = llm_eval.get("score_percentage")
                sug_poss = llm_eval.get("suggested_possible_points")
                sug_earn = llm_eval.get("suggested_earned_points")
                is_non_ans = llm_eval.get("is_non_answer", False)
                needs_clar = llm_eval.get("needs_specification_clarification", False)
                clar_focus = llm_eval.get("clarification_prompt_focus")
                return (
                    llm_eval["quality_band"],
                    llm_eval.get("detected_gap"),
                    llm_eval.get("evaluator_reason", "Evaluated via live AI agent model."),
                    llm_eval.get("expected_concept", "Sound engineering design and algorithmic justification."),
                    diff,
                    topic_detected,
                    score_pct,
                    sug_poss,
                    sug_earn,
                    is_non_ans,
                    needs_clar,
                    clar_focus
                )
        except Exception as e:
            print(f"[InterviewAgent] Live LLM eval failed, using domain expert rubric: {e}")

        # Fallback Rubric (ensures sound engineering answers like Coffman/wait-die or practical designs receive high marks)
        hard_markers = [
            "upsert", "pinecone", "vector", "embedding", "crdt", "raft", "paxos", "split-brain",
            "deadlock", "wait-die", "lock-free", "lsm", "stampede", "layout thrashing",
            "sharding", "zero-downtime", "multi-region", "byzantine", "starvation", "hydration",
            "observability", "prometheus", "grafana", "alertmanager", "alerting"
        ]
        is_hard = any(m in q_lower for m in hard_markers)
        if is_hard or "eviction" in q_lower or "partition" in q_lower or depth >= 3:
            fallback_difficulty = "hard"
        elif "overview" in q_lower or "walk me through" in q_lower or "introduce" in q_lower or len(q_lower.split()) < 15:
            fallback_difficulty = "easy"
        else:
            fallback_difficulty = "medium"

        fallback_topic = topic
        if "vector" in q_lower or "pinecone" in q_lower or "embedding" in q_lower:
            fallback_topic = "Vector Databases & Embeddings"
        elif "deadlock" in q_lower or "wait-die" in q_lower or "locking" in q_lower:
            fallback_topic = "Concurrency & Deadlocks"
        elif "caching" in q_lower or "redis" in q_lower:
            fallback_topic = "Distributed Caching & Invalidation"
        elif "prometheus" in q_lower or "grafana" in q_lower or "monitoring" in q_lower or "observability" in q_lower:
            fallback_topic = "Observability & SLA Monitoring"

        fallacy_indicators = [
            "always faster", "never fails", "unlimited scale", "zero latency", "perfect consistency",
            "just use mongo", "infinitely scalable"
        ]
        has_fallacy = any(f in ans_lower for f in fallacy_indicators)

        # Technical entity lexicons
        data_structures = ["b-tree", "lsm", "hash map", "skip list", "heap", "trie", "inverted index", "ring buffer", "bloom filter", "wal", "segment tree"]
        complexity_and_perf = ["o(1)", "o(log n)", "o(n)", "p99", "throughput", "latency", "qps", "i/o", "bottleneck", "concurrency", "amortized"]
        system_and_concurrency = ["raft", "paxos", "crdt", "2pc", "ordered locking", "wait-die", "mutex", "cas", "read-committed", "serializable", "mvcc", "sharding", "partition", "replication", "write-ahead log", "cache stampede", "eviction"]
        reasoning_connectives = ["because", "trade-off", "mitigate", "prevent", "instead of", "sacrificing", "in order to", "prioritizing"]

        ds_hits = [ds for ds in data_structures if ds in ans_lower]
        perf_hits = [p for p in complexity_and_perf if p in ans_lower]
        sys_hits = [s for s in system_and_concurrency if s in ans_lower]
        reason_hits = [r for r in reasoning_connectives if r in ans_lower]
        total_technical_entities = len(ds_hits) + len(perf_hits) + len(sys_hits)

        # Dynamic expected concept matching question asked
        if "deadlock" in q_lower or "lock" in q_lower:
            expected = "Explanation of deadlock conditions (Coffman conditions) and mitigation schemes like ordered resource acquisition or timestamp-based wait-die / wound-wait."
        elif "data structure" in q_lower or "storage" in q_lower:
            expected = "Identify specific data structure/storage engine and justify via complexity trade-offs, access patterns, and performance characteristics."
        elif "protocol" in q_lower or "communication" in q_lower:
            expected = "Contrast network protocols (e.g., gRPC/HTTP2 vs REST/HTTP1.1, binary serialization vs JSON) in terms of latency, streaming, and overhead."
        elif "pinecone" in q_lower or "vector" in q_lower:
            expected = "Vector database indexing and zero-downtime updates via namespaces, index swapping, or version tagging."
        elif "monitoring" in q_lower or "prometheus" in q_lower or "grafana" in q_lower or "sla" in q_lower:
            expected = "Production observability instrumentation (Prometheus/Grafana), p95/p99 latency tracking, and SLA alert triggers."
        else:
            expected = "Concrete architectural justification detailing practical design trade-offs, operational constraints, and failure modes."

        # Case 1: Specific recognized strong answers (e.g. Coffman conditions and wait-die)
        if "coffman" in ans_lower or ("deadlock" in ans_lower and ("wait-die" in ans_lower or "ordered" in ans_lower or "preemption" in ans_lower)):
            return (
                "Good",
                None,
                "Strong technical understanding of deadlock conditions and prevention protocols (ordered locking / wait-die mechanism).",
                expected,
                fallback_difficulty,
                fallback_topic,
                78.0,
                None,
                None,
                False,
                False,
                None
            )

        # Case 2: Blatant Fallacies
        if has_fallacy and total_technical_entities == 0:
            return (
                "Incorrect",
                "Non-technical or fallacious justification. Failed to provide engineering or algorithmic rationale.",
                "Unacceptable technical response relying on non-technical colloquialisms instead of engineering rationale.",
                expected,
                fallback_difficulty,
                fallback_topic,
                0.0,
                None,
                0.0,
                True,
                False,
                None
            )

        # Case 3: Vacuous answer / Deflections (<8 words, no idea, or evasive phrases)
        if (
            (word_count < 8 and total_technical_entities == 0)
            or "dont have" in ans_lower
            or "no idea" in ans_lower
            or "totally aware" in ans_lower
            or "aware about" in ans_lower
            or "i know this" in ans_lower
        ):
            return (
                "Weak",
                "Candidate did not provide a substantive technical answer or deflected without explaining.",
                "Provided no technical explanation or implementation details, offering only an empty or generic statement.",
                expected,
                fallback_difficulty,
                fallback_topic,
                0.0,
                None,
                0.0,
                True,
                False,
                None
            )

        # Case 4: Strong / Excellent technical defense
        if total_technical_entities >= 3 and (len(reason_hits) >= 1 or word_count >= 35):
            return (
                "Excellent",
                None,
                f"Outstanding technical reasoning! Articulated clear engineering trade-offs referencing {', '.join((ds_hits + perf_hits + sys_hits)[:4])}.",
                expected,
                fallback_difficulty,
                fallback_topic,
                93.0,
                None,
                None,
                False,
                False,
                None
            )

        # Case 5: Solid / Good answer
        if total_technical_entities >= 2 or word_count >= 25:
            return (
                "Good",
                None,
                f"Solid technical explanation addressing key engineering concepts: {', '.join((ds_hits + sys_hits + perf_hits)[:3]) or 'relevant mechanisms'}.",
                expected,
                fallback_difficulty,
                fallback_topic,
                75.0,
                None,
                None,
                False,
                False,
                None
            )

        # Case 6: Average (Acceptable high-level answer)
        needs_clar_fallback = not is_clarification_attempt and depth <= 2
        clar_focus_fallback = "concrete technical implementation details, architecture, or chosen database" if needs_clar_fallback else None
        return (
            "Average",
            "Basic understanding demonstrated, but provided high-level summary rather than concrete implementation specifics.",
            "Acceptable baseline knowledge; candidate should provide specific configuration, code, or metrics details.",
            expected,
            fallback_difficulty,
            fallback_topic,
            50.0,
            None,
            None,
            False,
            needs_clar_fallback,
            clar_focus_fallback
        )

    @classmethod
    def _generate_follow_up_question(
        cls,
        session: InterviewSession,
        topic: str,
        depth: int,
        candidate_answer: str,
        phase: str,
        previous_question: str = "",
        quality_band: str = "Good",
        detected_gap: Optional[str] = None,
        candidate_name: str = "Candidate",
        project_title: str = "Flagship Project",
        project_details: str = "",
        role_skills: Optional[List[str]] = None,
        web_trends: Optional[List[str]] = None,
        item_type: str = "PROJECT"
    ) -> str:
        """
        Dynamically generates natural, conversational follow-up questions (ChatGPT style).
        Uses live LLM grounded in web research and the candidate's actual answers.
        """
        try:
            dynamic_q = llm_client.generate_interview_question(
                candidate_name=candidate_name,
                company=session.company,
                role=session.role,
                phase=phase,
                current_depth=depth,
                project_title=project_title,
                project_details=project_details,
                candidate_last_answer=candidate_answer,
                previous_question=previous_question,
                quality_band=quality_band,
                detected_gap=detected_gap,
                role_skills=role_skills,
                web_trends=web_trends,
                item_type=item_type
            )
            if dynamic_q and len(dynamic_q.strip()) > 20:
                return dynamic_q.strip()
        except Exception as e:
            print(f"[InterviewAgent] Dynamic question generation fallback: {e}")

        # Intelligent conversational fallbacks (tailored to item type, role, and context)
        if item_type == "WORK_EXPERIENCE" or phase == "EXPERIENCE_DEFENSE":
            if depth == 2:
                return f"That gives helpful context on your role. At {project_title}, what was a specific service or core feature you personally architected or optimized?"
            elif depth == 3:
                return f"Makes sense! In that production environment at {project_title}, what was the most challenging latency or scaling trade-off you had to navigate?"
            else:
                return f"Looking back at your time at {project_title}, if a downstream dependency or database node failed, what was your fallback strategy to preserve data integrity?"
        elif phase == "PROJECT_DEFENSE":
            ans_lower = candidate_answer.lower()
            if "redis" in ans_lower or "cache" in ans_lower:
                return f"That makes good sense. When caching with Redis in {project_title}, how did you handle cache invalidation when data was updated, and did you have to guard against cache stampedes?"
            elif "database" in ans_lower or "postgres" in ans_lower or "sql" in ans_lower:
                return f"Got it. On the database side in {project_title}, what specific indexing or partitioning strategy did you choose, and what did you measure to verify query performance?"
            elif depth == 2:
                return f"That's a solid architectural foundation. In {project_title}, if traffic scaled up by 10x, what specific component or database bottleneck would be the first to struggle, and how would you optimize it?"
            elif depth == 3:
                return f"Makes sense! If a network partition or dependent service failure occurred in {project_title}, what was your fallback mechanism to maintain availability without corrupting data?"
            else:
                return f"Looking back at {project_title}, if you were to redesign that system from scratch today, what specific architectural or framework choice would you change?"
        else:  # SUBJECT_KNOWLEDGE
            role_lower = (session.role or "").lower()
            if "front" in role_lower or "web" in role_lower or "ui" in role_lower:
                if depth == 2:
                    return "That's a clean explanation. In a complex web application, how do you diagnose and prevent unnecessary component re-renders, and what metrics from Core Web Vitals do you monitor?"
                elif depth == 3:
                    return "Understood. When managing global state across multiple nested views, what are the trade-offs between local context and an external store like Redux or Zustand?"
                else:
                    return "How would you design an asset-loading and code-splitting strategy to keep initial bundle size under 150KB for users on high-latency mobile networks?"
            elif "ml" in role_lower or "data" in role_lower or "ai" in role_lower:
                if depth == 2:
                    return "Great breakdown. When deploying that model to production, how would you detect and handle feature drift and model degradation over time?"
                elif depth == 3:
                    return "Under high-concurrency inference requests, what techniques (like batching, quantization, or caching embeddings) would you apply to keep p99 latency low?"
                else:
                    return "Could you walk through how you would trade off precision versus recall for this specific business use case?"
            else:  # Backend / Systems
                if "deadlock" in candidate_answer.lower() or "coffman" in candidate_answer.lower() or "lock" in candidate_answer.lower():
                    return "Spot-on explanation of deadlock conditions and ordered locking! In a real distributed system with multiple nodes and clock drift, how do you handle timestamp ordering reliably, or mitigate transaction starvation?"
                elif depth == 2:
                    return "Great point. How would you design an idempotent API endpoint for a critical write operation (like a financial charge) to guarantee exactly-once processing even with client retries?"
                elif depth == 3:
                    return "In an event-driven architecture using Kafka or RabbitMQ, what is your strategy for handling poisoned messages or consumer rebalances without losing ordering?"
                else:
                    return "If your CPU usage spikes to 100% due to thread pool exhaustion, what telemetry and profiling tools would you use to pinpoint the root cause?"

    @classmethod
    def _generate_final_reports(cls, db: Session, session: InterviewSession) -> None:
        """
        Generates dual headline scores:
        - Resume Related Interview Score /100 (Work Experiences + Projects)
        - Subject/Fundamental Knowledge Score /100
        Backed by stored evidence records.
        """
        all_evidence = db.query(InterviewEvidence).filter(
            InterviewEvidence.session_id == session.id
        ).all()

        agent1_evidence = [e for e in all_evidence if "EV-PRO" in (e.evidence_ref or "") or "EV-EXP" in (e.evidence_ref or "")]
        agent2_evidence = [e for e in all_evidence if "EV-SUB" in (e.evidence_ref or "")]

        if not agent1_evidence and not agent2_evidence and all_evidence:
            agent1_evidence = all_evidence

        score1 = ScoringEngine.compute_aggregate_score([
            {"earned_points": e.earned_points, "possible_points": e.possible_points} for e in agent1_evidence
        ])
        star_rating = ScoringEngine.compute_star_rating(score1)

        score2 = ScoringEngine.compute_aggregate_score([
            {"earned_points": e.earned_points, "possible_points": e.possible_points} for e in agent2_evidence
        ]) if agent2_evidence else score1

        # Build individual cards for each agenda item explored
        agenda = list(session.agent1_report_json.get("agenda") or [])
        project_cards = []
        for item in agenda:
            if item.get("questions_asked", 0) > 0:
                item_evidence = [
                    e for e in all_evidence
                    if e.project_id_or_topic == item.get("item_id")
                    or item.get("title", "") in e.topic
                    or e.topic in item.get("title", "")
                ]
                if item_evidence:
                    item_score = ScoringEngine.compute_aggregate_score([
                        {"earned_points": e.earned_points, "possible_points": e.possible_points} for e in item_evidence
                    ])
                else:
                    item_score = score1
                item_star = ScoringEngine.compute_star_rating(item_score)
                project_cards.append({
                    "project_id": item.get("item_id", str(uuid.uuid4())),
                    "title": item.get("title", "Technical Defense"),
                    "type": item.get("item_type", "PROJECT"),
                    "score": item_score,
                    "star_rating": item_star,
                    "relevance_weight": item.get("relevance", 0.8),
                    "strengths": ["Demonstrated sound technical communication", "Defended implementation choices"],
                    "identified_gaps": ["Could elaborate further on edge cases under high concurrency"],
                    "topics_covered": [item.get("topic", "System Architecture"), item.get("subtopic", "Engineering Trade-offs")]
                })

        if not project_cards:
            project_cards = [
                {
                    "project_id": "proj-1",
                    "title": "Primary Technical Defense",
                    "score": score1,
                    "star_rating": star_rating,
                    "relevance_weight": 1.0,
                    "strengths": ["Demonstrated strong architectural understanding", "Defended technology choices with sound engineering reasoning"],
                    "identified_gaps": ["Could elaborate further on high-concurrency failure edge cases"],
                    "topics_covered": ["Architecture", "Trade-offs", "Scalability", "Bottlenecks"]
                }
            ]

        role_lower = (session.role or "").lower()
        if "front" in role_lower or "web" in role_lower:
            subject_breakdown = {
                "Browser Rendering & DOM Performance": "STRONG" if score2 >= 75 else "PARTIAL",
                "State Management & Component Lifecycle": "STRONG" if score1 >= 75 else "PARTIAL",
                "Core Web Vitals & Optimization": "STRONG" if score2 >= 70 else "PARTIAL",
                "API Contracts & State Sync": "STRONG" if score2 >= 80 else "UNTESTED"
            }
        elif "ml" in role_lower or "ai" in role_lower:
            subject_breakdown = {
                "Model Architecture & Training Pipelines": "STRONG" if score2 >= 75 else "PARTIAL",
                "Inference Latency & Serving": "STRONG" if score1 >= 75 else "PARTIAL",
                "Feature Engineering & Embeddings": "STRONG" if score2 >= 70 else "PARTIAL",
                "Evaluation Metrics & Drift Detection": "STRONG" if score2 >= 80 else "UNTESTED"
            }
        else:
            subject_breakdown = {
                "Concurrency & Thread Synchronization": "STRONG" if score2 >= 75 else "PARTIAL",
                "Distributed Systems & Caching": "STRONG" if score1 >= 75 else "PARTIAL",
                "Database Transactions & Isolation": "PARTIAL",
                "Network Protocols (HTTP/2, gRPC)": "STRONG" if score2 >= 80 else "UNTESTED"
            }

        strengths = [
            "Articulates design trade-offs with practical engineering rationale.",
            "Demonstrates solid fundamental and architectural intuition.",
            "Quick to adapt to situational constraints and scale requirements."
        ]

        weaknesses = [
            "Deeper knowledge of partition-tolerance failure edge cases would further strengthen candidate's defense.",
            "Continue practicing role-specific high-throughput tuning."
        ]

        final_score1 = round(score1, 1) if agent1_evidence else 0.0
        final_score2 = round(score2, 1) if agent2_evidence else 0.0

        final_report = {
            "resume_related_score": final_score1,
            "subject_knowledge_score": final_score2,
            "section_scores": {
                "Work Experience & Projects": final_score1,
                "Technical Fundamentals": final_score2,
                "Situational Reasoning": round((final_score1 + final_score2) / 2, 1) if (final_score1 or final_score2) else 0.0,
                "Code Quality & Complexity": final_score2 if final_score2 > 0 else final_score1
            },
            "project_cards": project_cards,
            "subject_topic_breakdown": subject_breakdown,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "improvement_recommendations": [
                "Review distributed state synchronization and split-brain handling.",
                "Practice tuning connection pools and statement timeouts under high concurrency."
            ]
        }

        session.agent1_report_json = {"score": score1, "star_rating": star_rating}
        session.agent2_report_json = {"score": score2}
        session.final_report_json = final_report
        db.commit()
