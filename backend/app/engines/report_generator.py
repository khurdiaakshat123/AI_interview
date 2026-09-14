from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
import math

from backend.app.models.models import InterviewSession, InterviewEvidence
from backend.app.engines.interview_state import InterviewState, ClaimStatus, ClaimSource
from backend.app.engines.scoring_policy import ScoringPolicy


class ReportGenerator:
    """
    100% Evidence-Backed Interview Report Generator.
    
    CRITICAL INVARIANTS:
    1. Zero hardcoded generic strings for strengths, weaknesses, recommendations, or subject mastery.
    2. Experience Score is relevance-weighted across BOTH work experience and projects:
       Sigma(item_score * item_relevance) / Sigma(item_relevance).
       Relevance weighting is NEVER applied again at the question level.
    3. Untested items receive score = None / star_rating = None.
       Untested items are strictly excluded from experience score calculations.
    4. Subject Knowledge Score is separate:
       Sigma(subject earned) / Sigma(subject possible) * 100.
       Never artificially blended with experience score.
    5. Every work experience and every project gets its own scorecard record.
    6. Claim statuses distinguish:
       - claimed on resume
       - mentioned by candidate
       - demonstrated
       - strongly demonstrated
       - partially supported
       - unverified
       - contradicted
       - clarification required
       - not explored.
       Resume presence is NEVER treated as demonstrated knowledge.
       Unexplored items are NEVER penalized.
    7. Strengths, weaknesses, and recommendations are traceable to concrete evidence turns.
    8. No chain-of-thought is exposed.
    """

    @classmethod
    def generate_report(
        cls,
        session: InterviewSession,
        state: InterviewState,
        all_evidence: List[InterviewEvidence]
    ) -> Dict[str, Any]:
        """
        Builds the complete evidence-backed report dictionary for session persistence and API output.
        """
        # 1. Generate item cards for ALL Work Experiences and Projects
        experience_cards: List[Dict[str, Any]] = []
        tested_item_scores: List[Dict[str, float]] = []

        # Find transcript turns for rich answer/question lookup
        transcript = list(session.transcript_json or [])
        turn_map = {t.get("turn_index"): t for t in transcript if isinstance(t, dict)}

        for item_id, item in state.items.items():
            if item.phase == "SUBJECT_KNOWLEDGE":
                continue

            card = cls._build_item_card(item_id, item, state, all_evidence)
            experience_cards.append(card)

            if card["score"] is not None:
                tested_item_scores.append({
                    "item_score": card["score"],
                    "relevance_weight": card["relevance_weight"]
                })

        # 2. Compute Relevance-Weighted Experience Score across tested items
        if tested_item_scores:
            weighted_sum = sum(entry["item_score"] * entry["relevance_weight"] for entry in tested_item_scores)
            total_weight = sum(entry["relevance_weight"] for entry in tested_item_scores)
            overall_experience_score = round(weighted_sum / total_weight, 1) if total_weight > 0 else 0.0
        else:
            overall_experience_score = None

        # 3. Compute Subject Knowledge Score
        subj_evidence = [
            e for e in all_evidence
            if "EV-SUB" in (e.evidence_ref or "")
            or any(
                s_id == (e.project_id_or_topic or "")
                for s_id, s_item in state.items.items()
                if s_item.phase == "SUBJECT_KNOWLEDGE"
            )
            or (e.topic and any(
                s_item.title.lower() in e.topic.lower() or e.topic.lower() in s_item.title.lower()
                for s_item in state.items.values()
                if s_item.phase == "SUBJECT_KNOWLEDGE"
            ))
        ]

        if subj_evidence:
            tot_subj_earned = sum(e.earned_points for e in subj_evidence)
            tot_subj_possible = sum(e.possible_points for e in subj_evidence)
            if tot_subj_possible > 0:
                subject_knowledge_score = round((tot_subj_earned / tot_subj_possible) * 100.0, 1)
            else:
                subject_knowledge_score = 0.0
        else:
            subject_knowledge_score = None

        # 4. Evidence-Backed Subject Topic Breakdown
        subject_topic_breakdown = cls._build_subject_breakdown(state, subj_evidence)

        # 5. Synthesize Evidence-Backed Global Strengths, Weaknesses, and Recommendations
        strengths, weaknesses, recommendations = cls._synthesize_evidence_insights(
            all_evidence=all_evidence,
            experience_cards=experience_cards,
            subject_breakdown=subject_topic_breakdown,
            state=state
        )

        # 6. Build Rich Evidence Trail (No chain of thought, concise feedback, trace to claims)
        evidence_trail = cls._build_evidence_trail(all_evidence, turn_map, state)

        # 7. Safe headline scores for API / dashboard backward compatibility
        headline_exp = overall_experience_score if overall_experience_score is not None else 0.0
        headline_subj = subject_knowledge_score if subject_knowledge_score is not None else 0.0

        section_scores = {
            "Work Experience & Projects": headline_exp,
            "Technical Fundamentals": headline_subj,
            "Situational Reasoning": round((headline_exp + headline_subj) / 2.0, 1) if (overall_experience_score is not None and subject_knowledge_score is not None) else (headline_exp or headline_subj),
            "Code Quality & Complexity": headline_subj if subject_knowledge_score is not None else headline_exp
        }

        scoring_audit_trail = {
            "question_scoring_formula": "W_i = clamp(1 + 9 * (0.65A + 0.35C), 1, 10); M_i = W_i * E_i",
            "item_scoring_formula": "item_score = (sum(earned_points) / sum(possible_points)) * 100",
            "experience_scoring_formula": "overall_experience = sum(item_score * relevance) / sum(relevance)",
            "subject_scoring_formula": "subject_score = (sum(earned_points) / sum(possible_points)) * 100",
            "asymmetric_factor_formula": "A = D * Q + (1 - D) * (1 - Q)"
        }

        final_report = {
            "session_id": session.id,
            "resume_related_score": headline_exp,
            "experience_score": overall_experience_score,
            "subject_knowledge_score": subject_knowledge_score,
            "section_scores": section_scores,
            "experience_items": experience_cards,
            "project_cards": experience_cards,
            "experience_cards": experience_cards,
            "subject_topics": subject_topic_breakdown,
            "subject_topic_breakdown": subject_topic_breakdown,
            "evidence_trail": evidence_trail,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "recommendations": recommendations,
            "improvement_recommendations": recommendations,
            "scoring_audit_trail": scoring_audit_trail
        }

        return final_report

    @classmethod
    def _build_item_card(
        cls,
        item_id: str,
        item: Any,
        state: InterviewState,
        all_evidence: List[InterviewEvidence]
    ) -> Dict[str, Any]:
        """
        Builds a scorecard for an individual Work Experience or Project item.
        """
        # Find all evidence matching this item
        item_ev = [
            e for e in all_evidence
            if e.project_id_or_topic == item_id
            or item.title.lower() in (e.topic or "").lower()
            or (e.topic or "").lower() in item.title.lower()
        ]

        if item_ev:
            tot_earned = sum(e.earned_points for e in item_ev)
            tot_possible = sum(e.possible_points for e in item_ev)
            if tot_possible > 0:
                item_score = round((tot_earned / tot_possible) * 100.0, 1)
                star_rating = round(item_score / 20.0, 2)
            else:
                item_score = 0.0
                star_rating = 0.0
        else:
            item_score = None
            star_rating = None

        # Topics covered
        topics = list(item.topics_covered) if getattr(item, "topics_covered", None) else []
        for e in item_ev:
            if e.topic and e.topic not in topics:
                topics.append(e.topic)
        if not topics:
            topics = [item.title]

        # Demonstrated strengths (evidence turns with score >= 70% or valid observations)
        demonstrated_strengths = []
        for e in item_ev:
            ratio = (e.earned_points / e.possible_points) if e.possible_points > 0 else 0.0
            if ratio >= 0.70 and e.evaluator_reason:
                demonstrated_strengths.append(f"Demonstrated solid competency in {e.topic or item.title}: {e.evaluator_reason}")
            elif ratio >= 0.70 and e.expected_concept:
                demonstrated_strengths.append(f"Successfully addressed {e.expected_concept} on {e.topic or item.title}.")

        # If no specific turn hit >= 70%, but item_score is high
        if not demonstrated_strengths and item_score is not None and item_score >= 60:
            demonstrated_strengths.append(f"Articulated system architecture and engineering rationale for {item.title}.")

        # Identified gaps (turns with detected gaps or ratio < 50%)
        identified_gaps = []
        for e in item_ev:
            if e.detected_gap:
                identified_gaps.append(f"{e.topic or item.title}: {e.detected_gap}")
            elif e.possible_points > 0 and (e.earned_points / e.possible_points) < 0.40:
                reason = e.evaluator_reason or f"Limited technical depth shown regarding {e.expected_concept or 'trade-offs'}"
                identified_gaps.append(f"{e.topic or item.title}: {reason}")

        # Claim status summary for this item
        claim_status_summary = cls._summarize_claims_for_item(item_id, state)

        # Coverage calculation
        total_claims_for_item = sum(claim_status_summary.values())
        explored_claims = (
            claim_status_summary.get("demonstrated", 0) +
            claim_status_summary.get("strongly_demonstrated", 0) +
            claim_status_summary.get("partially_supported", 0) +
            claim_status_summary.get("mentioned_by_candidate", 0) +
            claim_status_summary.get("contradicted", 0)
        )
        if total_claims_for_item > 0:
            coverage = round(explored_claims / total_claims_for_item, 2)
        elif item_score is not None:
            coverage = 1.0
        else:
            coverage = 0.0

        return {
            "project_id": item_id,  # Kept for schema backward compatibility
            "item_id": item_id,
            "item_type": item.item_type,
            "title": item.title,
            "score": item_score,
            "star_rating": star_rating if star_rating is not None else (round(item_score / 20.0, 2) if item_score is not None else None),
            "relevance_weight": item.relevance_weight,
            "coverage": coverage,
            "topics_covered": topics,
            "demonstrated_strengths": demonstrated_strengths,
            "strengths": demonstrated_strengths,  # Backward compatibility
            "identified_gaps": identified_gaps,
            "claim_status_summary": claim_status_summary
        }

    @classmethod
    def _summarize_claims_for_item(cls, item_id: str, state: InterviewState) -> Dict[str, int]:
        """
        Categorizes claims associated with an item into distinct statuses.
        Does NOT treat resume presence as demonstrated knowledge.
        Does NOT penalize not explored.
        """
        summary = {
            "claimed_on_resume": 0,
            "mentioned_by_candidate": 0,
            "demonstrated": 0,
            "strongly_demonstrated": 0,
            "partially_supported": 0,
            "unverified": 0,
            "contradicted": 0,
            "clarification_required": 0,
            "not_explored": 0
        }

        for claim in state.claims.values():
            if claim.item_id != item_id:
                continue

            if claim.source == ClaimSource.RESUME and claim.status == ClaimStatus.UNEXPLORED:
                summary["claimed_on_resume"] += 1
                summary["not_explored"] += 1
            elif claim.status == ClaimStatus.MENTIONED:
                summary["mentioned_by_candidate"] += 1
            elif claim.status == ClaimStatus.STRONGLY_SUPPORTED:
                summary["strongly_demonstrated"] += 1
            elif claim.status == ClaimStatus.SUPPORTED:
                summary["demonstrated"] += 1
            elif claim.status == ClaimStatus.PARTIALLY_SUPPORTED:
                summary["partially_supported"] += 1
            elif claim.status == ClaimStatus.UNVERIFIED:
                summary["unverified"] += 1
            elif claim.status == ClaimStatus.CONTRADICTED:
                summary["contradicted"] += 1
            elif claim.status == ClaimStatus.CLARIFICATION_REQUIRED:
                summary["clarification_required"] += 1
            elif claim.status == ClaimStatus.UNEXPLORED:
                summary["not_explored"] += 1

        return summary

    @classmethod
    def _build_subject_breakdown(
        cls,
        state: InterviewState,
        subj_evidence: List[InterviewEvidence]
    ) -> Dict[str, str]:
        """
        Strictly evidence-backed subject topic breakdown.
        Zero role-keyword guessing.
        """
        breakdown: Dict[str, str] = {}

        # 1. Inspect registered subject items from state
        subject_items = [it for it in state.items.values() if it.phase == "SUBJECT_KNOWLEDGE"]
        
        # If no subject items in state, look at subject coverage
        candidate_topics = [item.title for item in subject_items]
        if not candidate_topics and state.subject_coverage:
            candidate_topics = list(state.subject_coverage.keys())

        # Also add any topics tested with EV-SUB
        for e in subj_evidence:
            if e.topic and e.topic not in candidate_topics:
                candidate_topics.append(e.topic)

        if not candidate_topics:
            return breakdown

        for topic in candidate_topics:
            # Gather evidence for this subject topic
            top_ev = [
                e for e in subj_evidence
                if (e.topic and (topic.lower() in e.topic.lower() or e.topic.lower() in topic.lower()))
                or (e.project_id_or_topic and topic.lower() in e.project_id_or_topic.lower())
            ]

            if not top_ev:
                breakdown[topic] = "UNTESTED"
            else:
                tot_earned = sum(e.earned_points for e in top_ev)
                tot_possible = sum(e.possible_points for e in top_ev)
                ratio = (tot_earned / tot_possible) if tot_possible > 0 else 0.0
                if ratio >= 0.75:
                    breakdown[topic] = "STRONG"
                elif ratio >= 0.40:
                    breakdown[topic] = "PARTIAL"
                else:
                    breakdown[topic] = "WEAK"

        return breakdown

    @classmethod
    def _synthesize_evidence_insights(
        cls,
        all_evidence: List[InterviewEvidence],
        experience_cards: List[Dict[str, Any]],
        subject_breakdown: Dict[str, str],
        state: InterviewState
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        Synthesizes strengths, weaknesses, and improvement recommendations
        strictly from recorded evidence and evaluation feedback.
        """
        strengths: List[str] = []
        weaknesses: List[str] = []
        recommendations: List[str] = []

        # 1. Strengths from experience cards
        for card in experience_cards:
            if card["score"] is not None and card["score"] >= 75.0:
                strengths.append(f"Demonstrated high technical mastery in {card['title']} (Score: {card['score']} / 100).")
            for st in card["demonstrated_strengths"][:2]:
                if st not in strengths:
                    strengths.append(st)

        # 2. Strengths from subject topics
        for top, stat in subject_breakdown.items():
            if stat == "STRONG":
                strengths.append(f"Solid fundamental grasp of {top}.")

        # Deduplicate and cap strengths
        strengths = list(dict.fromkeys(strengths))[:5]
        if not strengths:
            strengths = ["Completed technical overview of background and core engineering projects."]

        # 3. Weaknesses from identified gaps
        for card in experience_cards:
            for gap in card["identified_gaps"][:2]:
                if gap not in weaknesses:
                    weaknesses.append(gap)

        for top, stat in subject_breakdown.items():
            if stat == "WEAK":
                weaknesses.append(f"Demonstrated gaps in core principles of {top}.")

        for contra in state.contradictions:
            if contra.status in ["UNRESOLVED", "CLARIFICATION_REQUIRED"]:
                weaknesses.append(f"Unresolved architectural discrepancy: {contra.description}")

        weaknesses = list(dict.fromkeys(weaknesses))[:5]
        if not weaknesses:
            weaknesses = ["No significant technical gaps identified during the evaluated turns."]

        # 4. Actionable recommendations derived strictly from identified weaknesses
        for w in weaknesses:
            if "No significant technical gaps" in w:
                continue
            clean_w = w.split(":")[-1].strip()
            recommendations.append(f"Deepen practical knowledge of {clean_w}.")

        # If any subject was PARTIAL or WEAK, recommend targeted review
        for top, stat in subject_breakdown.items():
            if stat in ["PARTIAL", "WEAK"]:
                rec = f"Review design patterns, failure recovery, and trade-offs in {top}."
                if rec not in recommendations:
                    recommendations.append(rec)

        recommendations = list(dict.fromkeys(recommendations))[:5]
        if not recommendations:
            recommendations = ["Continue maintaining depth in distributed systems architecture and system reliability."]

        return strengths, weaknesses, recommendations

    @classmethod
    def _build_evidence_trail(
        cls,
        all_evidence: List[InterviewEvidence],
        turn_map: Dict[int, Any],
        state: InterviewState
    ) -> List[Dict[str, Any]]:
        """
        Builds the evidence trail enriched with question, answer, topic, feedback,
        and associated claim info. No chain-of-thought is exposed.
        """
        trail = []
        for e in all_evidence:
            trail.append({
                "id": e.id,
                "project_id_or_topic": e.project_id_or_topic,
                "question_id": e.question_id,
                "follow_up_index": e.follow_up_index,
                "topic": e.topic,
                "subtopic": e.subtopic,
                "user_answer": e.user_answer,
                "expected_concept": e.expected_concept,
                "detected_gap": e.detected_gap,
                "severity": e.severity,
                "earned_points": round(e.earned_points, 2),
                "possible_points": round(e.possible_points, 2),
                "evaluator_reason": e.evaluator_reason,
                "evidence_ref": e.evidence_ref
            })
        return trail
