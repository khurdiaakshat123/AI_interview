import React, { useState } from 'react';
import { 
  Trophy, Star, CheckCircle2, AlertCircle, ShieldCheck, ChevronDown,
  ChevronUp, ArrowRight, Layers, Cpu, Award, TrendingUp, TrendingDown,
  Briefcase, FolderGit2, Check, HelpCircle, FileText, Info
} from 'lucide-react';
import { InterviewFinalReport, InterviewEvidenceRecord, ProjectScoreCard } from '../types';
import { StarRating } from '../components/StarRating';

interface InterviewReportPageProps {
  report: InterviewFinalReport;
  onNavigate: (tab: string, state?: any) => void;
}

const CLAIM_STATUS_META: Record<string, { label: string; bg: string; text: string; border: string }> = {
  strongly_demonstrated: { label: 'Strongly Supported', bg: 'bg-success/15', text: 'text-success', border: 'border-success/30' },
  strongly_supported: { label: 'Strongly Supported', bg: 'bg-success/15', text: 'text-success', border: 'border-success/30' },
  demonstrated: { label: 'Demonstrated', bg: 'bg-success/10', text: 'text-success', border: 'border-success/20' },
  supported: { label: 'Supported', bg: 'bg-success/10', text: 'text-success', border: 'border-success/20' },
  partially_supported: { label: 'Partially Supported', bg: 'bg-surface', text: 'text-text', border: 'border-border' },
  candidate_mentioned: { label: 'Candidate Mentioned', bg: 'bg-surface', text: 'text-text', border: 'border-border' },
  mentioned_by_candidate: { label: 'Candidate Mentioned', bg: 'bg-surface', text: 'text-text', border: 'border-border' },
  resume_claim: { label: 'Resume Claim', bg: 'bg-surface', text: 'text-text-muted', border: 'border-border' },
  claimed_on_resume: { label: 'Resume Claim', bg: 'bg-surface', text: 'text-text-muted', border: 'border-border' },
  unverified: { label: 'Unverified', bg: 'bg-accent/15', text: 'text-accent', border: 'border-accent/30' },
  clarification_required: { label: 'Clarification Required', bg: 'bg-accent/15', text: 'text-accent', border: 'border-accent/30' },
  contradicted: { label: 'Contradicted', bg: 'bg-danger/15', text: 'text-danger', border: 'border-danger/30' },
  not_explored: { label: 'Not Explored', bg: 'bg-bg', text: 'text-text-dim', border: 'border-border' },
  unexplored: { label: 'Not Explored', bg: 'bg-bg', text: 'text-text-dim', border: 'border-border' },
};

export const InterviewReportPage: React.FC<InterviewReportPageProps> = ({ report, onNavigate }) => {
  const [expandedEvidenceId, setExpandedEvidenceId] = useState<string | null>(null);

  const toggleEvidence = (id: string) => {
    setExpandedEvidenceId(expandedEvidenceId === id ? null : id);
  };

  const experienceItems: ProjectScoreCard[] = 
    report.experience_items && report.experience_items.length > 0
      ? report.experience_items
      : (report.experience_cards && report.experience_cards.length > 0
          ? report.experience_cards
          : (report.project_cards || []));

  const subjectTopics = report.subject_topics || report.subject_topic_breakdown || {};

  const experienceScore = report.experience_score ?? report.resume_related_score;
  const subjectScore = report.subject_knowledge_score;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header Banner */}
      <div className="p-6 sm:p-8 rounded-xl bg-surface border border-border flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        <div>
          <div className="inline-flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-text-muted mb-2">
            <Award className="w-3.5 h-3.5 text-accent" />
            Evidence-Backed Performance Report
          </div>
          <h1 className="text-2xl sm:text-3xl font-serif text-text font-normal tracking-tight">
            Technical Interview Evaluation
          </h1>
          <p className="text-xs sm:text-sm text-text-muted mt-1.5 leading-relaxed">
            Candidate: <span className="text-text font-medium">{report.candidate_name}</span> • Role:{' '}
            <span className="text-accent font-medium">{report.role}</span> at <span className="text-text font-medium">{report.company}</span>
          </p>
        </div>

        {/* Dual Headline Score Cards */}
        <div className="flex flex-wrap items-center gap-4">
          {/* Card 1: Experience / Resume Score */}
          <div className="p-4 rounded-xl bg-bg border border-border text-center min-w-[200px] flex-1 sm:flex-initial">
            <div className="text-[11px] font-mono uppercase tracking-wider text-text-muted flex items-center justify-center gap-1.5">
              <Briefcase className="w-3.5 h-3.5 text-text-muted" />
              Experience / Resume
            </div>
            <div className="text-3xl font-mono text-text my-1.5">
              {experienceScore != null ? (
                <>
                  {experienceScore.toFixed(1)}
                  <span className="text-sm text-text-muted"> / 100</span>
                </>
              ) : (
                <span className="text-xs text-text-muted font-mono">UNTESTED</span>
              )}
            </div>
            <div className="text-[10px] text-accent font-mono">
              {experienceScore != null ? `★ ${(experienceScore / 20).toFixed(2)} / 5.0 Stars` : 'Relevance-Weighted'}
            </div>
            <div className="text-[10px] text-text-muted mt-0.5">
              Work Experience & Projects
            </div>
          </div>

          {/* Card 2: Subject Knowledge Score */}
          <div className="p-4 rounded-xl bg-bg border border-border text-center min-w-[200px] flex-1 sm:flex-initial">
            <div className="text-[11px] font-mono uppercase tracking-wider text-text-muted flex items-center justify-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-text-muted" />
              Subject Knowledge
            </div>
            <div className="text-3xl font-mono text-text my-1.5">
              {subjectScore != null ? (
                <>
                  {subjectScore.toFixed(1)}
                  <span className="text-sm text-text-muted"> / 100</span>
                </>
              ) : (
                <span className="text-xs text-text-muted font-mono">UNTESTED</span>
              )}
            </div>
            <div className="text-[10px] text-accent font-mono">
              {subjectScore != null ? `★ ${(subjectScore / 20).toFixed(2)} / 5.0 Stars` : 'CS Core Principles'}
            </div>
            <div className="text-[10px] text-text-muted mt-0.5">
              Computer Science Fundamentals
            </div>
          </div>
        </div>
      </div>

      {/* Scoring Hierarchy Framework Panel */}
      <div className="p-5 rounded-xl bg-surface border border-border space-y-3">
        <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-text-muted">
          <Layers className="w-3.5 h-3.5 text-accent" />
          Deterministic Evidence-Backed Scoring Hierarchy
        </div>
        <p className="text-xs text-text-muted leading-relaxed">
          Scores are derived purely from demonstrated semantic evidence across evaluated dialogue turns. Relevance weighting is applied once at the item level and never duplicated at the question level.
        </p>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-1">
          {/* Question Level */}
          <div className="p-3.5 rounded-lg bg-bg border border-border space-y-1">
            <div className="text-[10px] uppercase font-mono text-text-muted tracking-wider">
              1. Question Level
            </div>
            <div className="font-mono text-xs text-success font-medium">
              Σ earned / Σ possible
            </div>
            <p className="text-[11px] text-text-muted leading-normal">
              Adapts to difficulty and complexity. Clarifications are unscored.
            </p>
          </div>

          {/* Item Level */}
          <div className="p-3.5 rounded-lg bg-bg border border-border space-y-1">
            <div className="text-[10px] uppercase font-mono text-text-muted tracking-wider">
              2. Experience Item
            </div>
            <div className="font-mono text-xs text-text font-medium">
              (Σ earned / Σ possible) × 100
            </div>
            <p className="text-[11px] text-text-muted leading-normal">
              Computed per work experience and project. Untested items receive no synthetic score.
            </p>
          </div>

          {/* Overall Experience */}
          <div className="p-3.5 rounded-lg bg-bg border border-border space-y-1">
            <div className="text-[10px] uppercase font-mono text-text-muted tracking-wider">
              3. Overall Experience
            </div>
            <div className="font-mono text-xs text-accent font-medium">
              Σ(item score × relevance) / Σ(relevance)
            </div>
            <p className="text-[11px] text-text-muted leading-normal">
              Relevance-weighted across all tested work experiences and projects.
            </p>
          </div>

          {/* Subject Knowledge */}
          <div className="p-3.5 rounded-lg bg-bg border border-border space-y-1">
            <div className="text-[10px] uppercase font-mono text-text-muted tracking-wider">
              4. Subject Knowledge
            </div>
            <div className="font-mono text-xs text-text font-medium">
              (Σ earned / Σ possible) × 100
            </div>
            <p className="text-[11px] text-text-muted leading-normal">
              Separate CS core score; never blended or diluted into experience score.
            </p>
          </div>
        </div>
      </div>

      {/* Experience Item Scorecards Grid */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-serif text-text font-normal flex items-center gap-2">
            <Star className="w-4 h-4 text-accent fill-current" />
            Experience Items (Work Experience & Projects)
          </h2>
          <span className="text-xs text-text-muted font-mono">
            {experienceItems.length} Total Items
          </span>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          {experienceItems.map((card, idx) => {
            const isWorkExp = card.item_type === 'WORK_EXPERIENCE';
            const isUntested = card.score == null;

            return (
              <div
                key={card.item_id || card.project_id || idx}
                className="p-6 rounded-xl bg-surface border border-border flex flex-col justify-between space-y-4"
              >
                <div className="space-y-3">
                  {/* Top Row: Badge, Title, Score */}
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2 mb-1.5">
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-bg border border-border text-text-muted flex items-center gap-1">
                          {isWorkExp ? <Briefcase className="w-3 h-3" /> : <FolderGit2 className="w-3 h-3" />}
                          {isWorkExp ? 'Work Experience' : 'Project'}
                        </span>
                        <span className="text-[11px] text-text-muted font-mono">
                          Weight: {Number(card.relevance_weight || 1.0).toFixed(2)}x
                        </span>
                        {card.coverage != null && (
                          <span className="text-[11px] text-text-muted font-mono">
                            • {Math.round(card.coverage * 100)}% Coverage
                          </span>
                        )}
                      </div>
                      <h3 className="text-base font-semibold text-text leading-snug">
                        {card.title}
                      </h3>
                    </div>

                    <div className="text-right shrink-0">
                      {isUntested ? (
                        <div className="px-2.5 py-1 rounded bg-bg border border-border text-[11px] text-text-muted font-mono">
                          UNTESTED
                        </div>
                      ) : (
                        <div>
                          <div className="text-lg font-mono text-text font-medium">
                            {card.score!.toFixed(1)} <span className="text-xs text-text-muted font-normal">/ 100</span>
                          </div>
                          <StarRating rating={card.star_rating ?? (card.score! / 20)} size="sm" />
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Topics Covered */}
                  {card.topics_covered && card.topics_covered.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5">
                      {card.topics_covered.map((t, i) => (
                        <span key={i} className="px-2 py-0.5 rounded text-[10px] font-mono bg-bg text-text-muted border border-border">
                          {t}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Evidence-Backed Strengths */}
                  <div className="space-y-1 text-xs">
                    <span className="font-mono text-success flex items-center gap-1.5 font-medium">
                      <CheckCircle2 className="w-3.5 h-3.5 text-success" />
                      Demonstrated Strengths:
                    </span>
                    {(card.demonstrated_strengths && card.demonstrated_strengths.length > 0) || (card.strengths && card.strengths.length > 0) ? (
                      <ul className="list-disc list-inside text-text-muted pl-1 space-y-0.5">
                        {(card.demonstrated_strengths && card.demonstrated_strengths.length > 0 ? card.demonstrated_strengths : card.strengths).map((str, sIdx) => (
                          <li key={sIdx} className="leading-relaxed">{str}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-text-muted italic pl-1">
                        {isUntested ? 'Item was not explored during this session.' : 'No verified high-scoring turns recorded.'}
                      </p>
                    )}
                  </div>

                  {/* Evidence-Backed Identified Gaps */}
                  <div className="space-y-1 text-xs">
                    <span className="font-mono text-accent flex items-center gap-1.5 font-medium">
                      <AlertCircle className="w-3.5 h-3.5 text-accent" />
                      Identified Technical Gaps:
                    </span>
                    {card.identified_gaps && card.identified_gaps.length > 0 ? (
                      <ul className="list-disc list-inside text-text-muted pl-1 space-y-0.5">
                        {card.identified_gaps.map((gap, gIdx) => (
                          <li key={gIdx} className="leading-relaxed">{gap}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-text-muted italic pl-1">
                        {isUntested ? 'Item was not explored during this session.' : 'No technical gaps or contradictions detected.'}
                      </p>
                    )}
                  </div>

                  {/* Claim Status Summary Breakdown */}
                  {card.claim_status_summary && Object.keys(card.claim_status_summary).length > 0 && (
                    <div className="space-y-1.5 pt-2 border-t border-border">
                      <span className="text-[10px] font-mono uppercase tracking-wider text-text-muted block">
                        Claim Status Summary:
                      </span>
                      <div className="flex flex-wrap gap-1.5 font-mono text-[10px]">
                        {Object.entries(card.claim_status_summary).map(([statusKey, count]) => {
                          if (count <= 0) return null;
                          return (
                            <span
                              key={statusKey}
                              className="px-2 py-0.5 rounded bg-bg text-text-muted border border-border flex items-center gap-1"
                            >
                              <span>{statusKey.replace(/_/g, ' ')}:</span>
                              <span className="text-text font-medium">{count}</span>
                            </span>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>

                {/* Card Footer: Score status and weighting invariant */}
                <div className="pt-3 border-t border-border text-[11px] text-text-muted font-mono flex items-center justify-between">
                  <span>
                    Item Score: <strong className="text-text">{isUntested ? 'UNTESTED' : `${card.score!.toFixed(1)} / 100`}</strong>
                  </span>
                  <span>
                    Relevance Weight: {Number(card.relevance_weight || 1.0).toFixed(2)}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Core Subject Mastery Breakdown */}
      <div className="p-6 rounded-xl bg-surface border border-border space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-serif text-text font-normal flex items-center gap-2">
            <Cpu className="w-4 h-4 text-accent" />
            Core Subject Knowledge Mastery Breakdown
          </h2>
          <span className="text-xs text-text-muted font-mono">
            Derived from Actual Evaluated Turns
          </span>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Object.entries(subjectTopics).map(([topic, status], idx) => {
            const isStrong = status === 'STRONG';
            const isPartial = status === 'PARTIAL';
            const isWeak = status === 'WEAK';
            const isUntested = status === 'UNTESTED' || !status;

            return (
              <div
                key={idx}
                className="p-4 rounded-lg bg-bg border border-border flex flex-col justify-between space-y-2.5"
              >
                <span className="text-xs font-medium text-text">{topic}</span>
                <div className="flex items-center justify-between gap-2">
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase font-medium ${
                      isStrong
                        ? 'bg-success/15 text-success border border-success/30'
                        : isPartial
                        ? 'bg-accent/15 text-accent border border-accent/30'
                        : isWeak
                        ? 'bg-danger/15 text-danger border border-danger/30'
                        : 'bg-surface text-text-muted border border-border'
                    }`}
                  >
                    {isUntested ? 'UNTESTED' : status}
                  </span>
                  <span className="text-[10px] text-text-muted font-mono">
                    {isStrong ? '>= 75% Evidence' : isPartial ? '40-74%' : isWeak ? '< 40%' : 'Not Tested'}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Traceable Evidence Audit Trail */}
      <div className="p-6 rounded-xl bg-surface border border-border space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-xl font-serif text-text font-normal flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-accent" />
              Traceable Evidence Audit Trail
            </h2>
            <p className="text-xs text-text-muted mt-0.5">
              Every score point is backed by a stored evidence turn. Click any turn to review objective, answer, and feedback.
            </p>
          </div>
          <span className="px-3 py-1 rounded-lg bg-bg border border-border text-text-muted font-mono text-xs">
            {report.evidence_trail.length} Stored Evidence Turns
          </span>
        </div>

        <div className="space-y-3">
          {report.evidence_trail.map((ev) => {
            const isExpanded = expandedEvidenceId === ev.id;

            return (
              <div
                key={ev.id}
                className="rounded-lg border border-border bg-bg overflow-hidden text-xs"
              >
                {/* Accordion Trigger */}
                <div
                  onClick={() => toggleEvidence(ev.id)}
                  className="p-4 flex flex-wrap items-center justify-between gap-3 cursor-pointer hover:bg-surface transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="px-2 py-0.5 rounded bg-surface border border-border text-[10px] font-mono text-text-muted">
                      {ev.evidence_ref || 'EV-TURN'}
                    </span>
                    <span className="font-medium text-text">
                      {ev.topic}: {ev.subtopic}
                    </span>
                  </div>

                  <div className="flex items-center gap-4">
                    <span className="font-mono text-success font-medium">
                      +{Number(ev.earned_points || 0).toFixed(1)} / {Number(ev.possible_points || 0).toFixed(1)} pts
                    </span>
                    {isExpanded ? <ChevronUp className="w-4 h-4 text-text-muted" /> : <ChevronDown className="w-4 h-4 text-text-muted" />}
                  </div>
                </div>

                {/* Accordion Content */}
                {isExpanded && (
                  <div className="p-4 bg-surface border-t border-border space-y-3">
                    <div>
                      <span className="text-[11px] font-mono uppercase text-text-muted block mb-1">Candidate Answer:</span>
                      <p className="p-3 rounded-lg bg-bg border border-border text-text italic leading-relaxed">
                        "{ev.user_answer}"
                      </p>
                    </div>

                    <div className="grid sm:grid-cols-2 gap-3 text-xs">
                      <div className="p-3 rounded-lg bg-bg border border-border">
                        <span className="font-mono text-[10px] uppercase text-text-muted block mb-1">Target Concept / Objective:</span>
                        <p className="text-text leading-relaxed">{ev.expected_concept || 'Engineering rationale and implementation trade-offs'}</p>
                      </div>

                      <div className="p-3 rounded-lg bg-bg border border-border">
                        <span className="font-mono text-[10px] uppercase text-text-muted block mb-1">Concise Evaluator Feedback:</span>
                        <p className="text-text leading-relaxed">{ev.evaluator_reason}</p>
                      </div>
                    </div>

                    {ev.detected_gap && (
                      <div className="p-2.5 rounded-lg bg-danger/10 border border-danger/30 text-danger font-mono text-xs">
                        <span className="font-semibold">Detected Gap ({ev.severity || 'MODERATE'}):</span> {ev.detected_gap}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Strengths & Targeted Improvement Roadmap (Evidence-Backed) */}
      <div className="grid md:grid-cols-2 gap-6">
        <div className="p-6 rounded-xl bg-surface border border-border space-y-3">
          <h3 className="text-base font-serif text-text font-normal flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-success" />
            Demonstrated Technical Strengths
          </h3>
          {report.strengths && report.strengths.length > 0 ? (
            <ul className="space-y-2 text-xs text-text-muted">
              {report.strengths.map((str, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-success shrink-0 mt-0.5" />
                  <span className="leading-relaxed">{str}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-text-muted italic">
              No high-performing turns recorded across explored technical items.
            </p>
          )}
        </div>

        <div className="p-6 rounded-xl bg-surface border border-border space-y-3">
          <h3 className="text-base font-serif text-text font-normal flex items-center gap-2">
            <TrendingDown className="w-4 h-4 text-accent" />
            Targeted Improvement Roadmap
          </h3>
          {report.improvement_recommendations && report.improvement_recommendations.length > 0 ? (
            <ul className="space-y-2 text-xs text-text-muted">
              {report.improvement_recommendations.map((rec, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 text-accent shrink-0 mt-0.5" />
                  <span className="leading-relaxed">{rec}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-text-muted italic">
              No critical technical gaps or contradictions identified across tested items.
            </p>
          )}
        </div>
      </div>

      {/* Navigation Footer */}
      <div className="flex items-center justify-between pt-4">
        <button
          onClick={() => onNavigate('dashboard')}
          className="px-5 py-2.5 rounded-lg text-xs font-medium bg-surface hover:bg-bg text-text border border-border transition-colors"
        >
          Return to Dashboard
        </button>

        <button
          onClick={() => onNavigate('interview')}
          className="px-6 py-2.5 rounded-lg text-xs font-medium bg-accent text-accent-contrast hover:opacity-90 flex items-center gap-2 transition-opacity"
        >
          Retake Another Mock Interview
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

