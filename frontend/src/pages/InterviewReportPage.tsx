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
  strongly_demonstrated: { label: 'Strongly Supported', bg: 'bg-emerald-950/80', text: 'text-emerald-300', border: 'border-emerald-700/60' },
  strongly_supported: { label: 'Strongly Supported', bg: 'bg-emerald-950/80', text: 'text-emerald-300', border: 'border-emerald-700/60' },
  demonstrated: { label: 'Demonstrated', bg: 'bg-emerald-950/50', text: 'text-emerald-400', border: 'border-emerald-800/50' },
  supported: { label: 'Supported', bg: 'bg-emerald-950/50', text: 'text-emerald-400', border: 'border-emerald-800/50' },
  partially_supported: { label: 'Partially Supported', bg: 'bg-cyan-950/60', text: 'text-cyan-300', border: 'border-cyan-800/50' },
  candidate_mentioned: { label: 'Candidate Mentioned', bg: 'bg-indigo-950/60', text: 'text-indigo-300', border: 'border-indigo-800/50' },
  mentioned_by_candidate: { label: 'Candidate Mentioned', bg: 'bg-indigo-950/60', text: 'text-indigo-300', border: 'border-indigo-800/50' },
  resume_claim: { label: 'Resume Claim', bg: 'bg-slate-800/80', text: 'text-slate-300', border: 'border-slate-700/60' },
  claimed_on_resume: { label: 'Resume Claim', bg: 'bg-slate-800/80', text: 'text-slate-300', border: 'border-slate-700/60' },
  unverified: { label: 'Unverified', bg: 'bg-amber-950/60', text: 'text-amber-300', border: 'border-amber-800/50' },
  clarification_required: { label: 'Clarification Required', bg: 'bg-amber-950/80', text: 'text-amber-300', border: 'border-amber-700/70' },
  contradicted: { label: 'Contradicted', bg: 'bg-rose-950/80', text: 'text-rose-300', border: 'border-rose-700/60' },
  not_explored: { label: 'Not Explored', bg: 'bg-slate-900/60', text: 'text-slate-500', border: 'border-slate-800/60' },
  unexplored: { label: 'Not Explored', bg: 'bg-slate-900/60', text: 'text-slate-500', border: 'border-slate-800/60' },
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
      <div className="p-6 sm:p-8 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900 to-indigo-950/40 border border-slate-800 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        <div>
          <div className="inline-flex items-center gap-2 text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-2">
            <Award className="w-4 h-4" />
            Evidence-Backed Performance Report
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Technical Interview Evaluation
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Candidate: <span className="text-white font-medium">{report.candidate_name}</span> • Role:{' '}
            <span className="text-sky-300 font-medium">{report.role}</span> at <span className="text-white font-medium">{report.company}</span>
          </p>
        </div>

        {/* Dual Headline Score Cards */}
        <div className="flex flex-wrap items-center gap-4">
          {/* Card 1: Experience / Resume Score */}
          <div className="p-4 rounded-2xl bg-slate-950/90 border border-slate-800 text-center min-w-[200px] flex-1 sm:flex-initial shadow-sm">
            <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider flex items-center justify-center gap-1.5">
              <Briefcase className="w-3.5 h-3.5 text-sky-400" />
              Experience / Resume Score
            </div>
            <div className="text-3xl font-extrabold text-white font-mono my-1.5">
              {experienceScore != null ? (
                <>
                  {experienceScore.toFixed(1)}
                  <span className="text-sm font-normal text-slate-500"> / 100</span>
                </>
              ) : (
                <span className="text-base text-slate-500 font-sans font-medium">UNTESTED / NOT SCORED</span>
              )}
            </div>
            <div className="text-[10px] text-amber-400 font-mono">
              {experienceScore != null ? `★ ${(experienceScore / 20).toFixed(2)} / 5.0 Stars` : 'Relevance-Weighted'}
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">
              Work Experience & Projects
            </div>
          </div>

          {/* Card 2: Subject Knowledge Score */}
          <div className="p-4 rounded-2xl bg-slate-950/90 border border-slate-800 text-center min-w-[200px] flex-1 sm:flex-initial shadow-sm">
            <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider flex items-center justify-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-indigo-400" />
              Subject Knowledge Score
            </div>
            <div className="text-3xl font-extrabold text-indigo-300 font-mono my-1.5">
              {subjectScore != null ? (
                <>
                  {subjectScore.toFixed(1)}
                  <span className="text-sm font-normal text-slate-500"> / 100</span>
                </>
              ) : (
                <span className="text-base text-slate-500 font-sans font-medium">UNTESTED / NOT SCORED</span>
              )}
            </div>
            <div className="text-[10px] text-indigo-400 font-mono">
              {subjectScore != null ? `★ ${(subjectScore / 20).toFixed(2)} / 5.0 Stars` : 'CS Core Principles'}
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">
              Computer Science Fundamentals
            </div>
          </div>
        </div>
      </div>

      {/* Scoring Hierarchy Framework Panel */}
      <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-3">
        <div className="flex items-center gap-2 text-xs font-bold text-indigo-400 uppercase tracking-wider">
          <Layers className="w-4 h-4 text-indigo-400" />
          Deterministic Evidence-Backed Scoring Hierarchy
        </div>
        <p className="text-xs text-slate-400 leading-relaxed">
          Scores are derived purely from demonstrated semantic evidence across evaluated dialogue turns. Relevance weighting is applied once at the item level and never duplicated at the question level.
        </p>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-1">
          {/* Question Level */}
          <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800/80 space-y-1">
            <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
              1. Question Level
            </div>
            <div className="font-mono text-xs text-emerald-400 font-semibold">
              Σ earned / Σ possible
            </div>
            <p className="text-[11px] text-slate-500 leading-normal">
              Adapts to difficulty and complexity. Clarifications are unscored.
            </p>
          </div>

          {/* Item Level */}
          <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800/80 space-y-1">
            <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
              2. Experience Item
            </div>
            <div className="font-mono text-xs text-sky-400 font-semibold">
              (Σ earned / Σ possible) × 100
            </div>
            <p className="text-[11px] text-slate-500 leading-normal">
              Computed per work experience and project. Untested items receive no synthetic score.
            </p>
          </div>

          {/* Overall Experience */}
          <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800/80 space-y-1">
            <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
              3. Overall Experience
            </div>
            <div className="font-mono text-xs text-amber-400 font-semibold">
              Σ(item score × relevance) / Σ(relevance)
            </div>
            <p className="text-[11px] text-slate-500 leading-normal">
              Relevance-weighted across all tested work experiences and projects.
            </p>
          </div>

          {/* Subject Knowledge */}
          <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800/80 space-y-1">
            <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
              4. Subject Knowledge
            </div>
            <div className="font-mono text-xs text-indigo-400 font-semibold">
              (Σ earned / Σ possible) × 100
            </div>
            <p className="text-[11px] text-slate-500 leading-normal">
              Separate CS core score; never blended or diluted into experience score.
            </p>
          </div>
        </div>
      </div>

      {/* Experience Item Scorecards Grid */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Star className="w-5 h-5 text-amber-400 fill-current" />
            Experience Items (Work Experience & Projects)
          </h2>
          <span className="text-xs text-slate-400 font-mono">
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
                className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col justify-between space-y-4 shadow-sm"
              >
                <div className="space-y-3">
                  {/* Top Row: Badge, Title, Score */}
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2 mb-1.5">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border flex items-center gap-1 ${
                            isWorkExp
                              ? 'bg-sky-950/80 text-sky-300 border-sky-800/60'
                              : 'bg-indigo-950/80 text-indigo-300 border-indigo-800/60'
                          }`}
                        >
                          {isWorkExp ? <Briefcase className="w-3 h-3" /> : <FolderGit2 className="w-3 h-3" />}
                          {isWorkExp ? 'Work Experience' : 'Project'}
                        </span>
                        <span className="text-[11px] text-slate-400 font-mono">
                          Weight: {Number(card.relevance_weight || 1.0).toFixed(2)}x
                        </span>
                        {card.coverage != null && (
                          <span className="text-[11px] text-slate-400 font-mono">
                            • {Math.round(card.coverage * 100)}% Coverage
                          </span>
                        )}
                      </div>
                      <h3 className="text-base font-bold text-white leading-snug">
                        {card.title}
                      </h3>
                    </div>

                    <div className="text-right shrink-0">
                      {isUntested ? (
                        <div className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-[11px] font-medium text-slate-500 font-mono">
                          UNTESTED
                        </div>
                      ) : (
                        <div>
                          <div className="text-lg font-mono font-bold text-white">
                            {card.score!.toFixed(1)} <span className="text-xs text-slate-500 font-normal">/ 100</span>
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
                        <span key={i} className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-950 text-slate-300 border border-slate-800">
                          {t}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Evidence-Backed Strengths */}
                  <div className="space-y-1 text-xs">
                    <span className="font-bold text-emerald-400 flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Demonstrated Strengths:
                    </span>
                    {(card.demonstrated_strengths && card.demonstrated_strengths.length > 0) || (card.strengths && card.strengths.length > 0) ? (
                      <ul className="list-disc list-inside text-slate-300 pl-1 space-y-0.5">
                        {(card.demonstrated_strengths && card.demonstrated_strengths.length > 0 ? card.demonstrated_strengths : card.strengths).map((str, sIdx) => (
                          <li key={sIdx} className="leading-relaxed">{str}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-slate-500 italic pl-1">
                        {isUntested ? 'Item was not explored during this session.' : 'No verified high-scoring turns recorded.'}
                      </p>
                    )}
                  </div>

                  {/* Evidence-Backed Identified Gaps */}
                  <div className="space-y-1 text-xs">
                    <span className="font-bold text-amber-400 flex items-center gap-1.5">
                      <AlertCircle className="w-3.5 h-3.5" />
                      Identified Technical Gaps:
                    </span>
                    {card.identified_gaps && card.identified_gaps.length > 0 ? (
                      <ul className="list-disc list-inside text-slate-300 pl-1 space-y-0.5">
                        {card.identified_gaps.map((gap, gIdx) => (
                          <li key={gIdx} className="leading-relaxed">{gap}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-slate-500 italic pl-1">
                        {isUntested ? 'Item was not explored during this session.' : 'No technical gaps or contradictions detected.'}
                      </p>
                    )}
                  </div>

                  {/* Claim Status Summary Breakdown */}
                  {card.claim_status_summary && Object.keys(card.claim_status_summary).length > 0 && (
                    <div className="space-y-1.5 pt-2 border-t border-slate-800/80">
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                        Claim Status Summary:
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {Object.entries(card.claim_status_summary).map(([statusKey, count]) => {
                          if (count <= 0) return null;
                          const meta = CLAIM_STATUS_META[statusKey] || {
                            label: statusKey.replace(/_/g, ' '),
                            bg: 'bg-slate-950',
                            text: 'text-slate-300',
                            border: 'border-slate-800'
                          };
                          return (
                            <span
                              key={statusKey}
                              className={`px-2 py-0.5 rounded text-[10px] font-medium border flex items-center gap-1 ${meta.bg} ${meta.text} ${meta.border}`}
                            >
                              <span>{meta.label}:</span>
                              <span className="font-bold font-mono">{count}</span>
                            </span>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>

                {/* Card Footer: Score status and weighting invariant */}
                <div className="pt-3 border-t border-slate-800/80 text-[11px] text-slate-400 font-mono flex items-center justify-between">
                  <span>
                    Item Score: <strong className="text-white">{isUntested ? 'UNTESTED / NOT SCORED' : `${card.score!.toFixed(1)} / 100`}</strong>
                  </span>
                  <span className="text-slate-500">
                    Relevance Weight: {Number(card.relevance_weight || 1.0).toFixed(2)}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Core Subject Mastery Breakdown */}
      <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Cpu className="w-5 h-5 text-indigo-400" />
            Core Subject Knowledge Mastery Breakdown
          </h2>
          <span className="text-xs text-slate-400 font-mono">
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
                className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 flex flex-col justify-between space-y-2.5 shadow-sm"
              >
                <span className="text-xs font-bold text-slate-200">{topic}</span>
                <div className="flex items-center justify-between gap-2">
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase ${
                      isStrong
                        ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                        : isPartial
                        ? 'bg-amber-950 text-amber-300 border border-amber-800'
                        : isWeak
                        ? 'bg-rose-950 text-rose-300 border border-rose-800'
                        : 'bg-slate-900 text-slate-500 border border-slate-800'
                    }`}
                  >
                    {isUntested ? 'UNTESTED' : status}
                  </span>
                  <span className="text-[10px] text-slate-500">
                    {isStrong ? '>= 75% Evidence' : isPartial ? '40-74% Evidence' : isWeak ? '< 40% Evidence' : 'Not Tested'}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Traceable Evidence Audit Trail */}
      <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
              Traceable Evidence Audit Trail
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Every score point is backed by a stored evidence turn. Click any turn to review objective, answer, and feedback.
            </p>
          </div>
          <span className="px-3 py-1 rounded-xl bg-slate-800 text-slate-300 font-mono text-xs font-semibold">
            {report.evidence_trail.length} Stored Evidence Turns
          </span>
        </div>

        <div className="space-y-3">
          {report.evidence_trail.map((ev) => {
            const isExpanded = expandedEvidenceId === ev.id;

            return (
              <div
                key={ev.id}
                className="rounded-xl border border-slate-800 bg-slate-950/60 overflow-hidden transition-all text-xs"
              >
                {/* Accordion Trigger */}
                <div
                  onClick={() => toggleEvidence(ev.id)}
                  className="p-4 flex flex-wrap items-center justify-between gap-3 cursor-pointer hover:bg-slate-900/60 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-[10px] font-mono text-slate-400">
                      {ev.evidence_ref || 'EV-TURN'}
                    </span>
                    <span className="font-semibold text-slate-200">
                      {ev.topic}: {ev.subtopic}
                    </span>
                  </div>

                  <div className="flex items-center gap-4">
                    <span className="font-mono text-emerald-400 font-bold">
                      +{Number(ev.earned_points || 0).toFixed(1)} / {Number(ev.possible_points || 0).toFixed(1)} pts
                    </span>
                    {isExpanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                  </div>
                </div>

                {/* Accordion Content */}
                {isExpanded && (
                  <div className="p-4 bg-slate-900/40 border-t border-slate-800/80 space-y-3">
                    <div>
                      <span className="text-[11px] font-bold text-slate-400 block mb-1">Candidate Answer:</span>
                      <p className="p-3 rounded-lg bg-slate-950 border border-slate-800/80 text-slate-300 italic">
                        "{ev.user_answer}"
                      </p>
                    </div>

                    <div className="grid sm:grid-cols-2 gap-3 text-xs">
                      <div className="p-3 rounded-lg bg-slate-950 border border-slate-800/80">
                        <span className="font-bold text-slate-400 block mb-1">Target Concept / Objective:</span>
                        <p className="text-slate-300">{ev.expected_concept || 'Engineering rationale and implementation trade-offs'}</p>
                      </div>

                      <div className="p-3 rounded-lg bg-slate-950 border border-slate-800/80">
                        <span className="font-bold text-slate-400 block mb-1">Concise Evaluator Feedback:</span>
                        <p className="text-slate-300">{ev.evaluator_reason}</p>
                      </div>
                    </div>

                    {ev.detected_gap && (
                      <div className="p-2.5 rounded-lg bg-amber-950/30 border border-amber-800/40 text-amber-200">
                        <span className="font-bold">Detected Gap ({ev.severity || 'MODERATE'}):</span> {ev.detected_gap}
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
        <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-3">
          <h3 className="text-base font-bold text-emerald-400 flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            Demonstrated Technical Strengths
          </h3>
          {report.strengths && report.strengths.length > 0 ? (
            <ul className="space-y-2 text-xs text-slate-300">
              {report.strengths.map((str, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span className="leading-relaxed">{str}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-slate-500 italic">
              No high-performing turns recorded across explored technical items.
            </p>
          )}
        </div>

        <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-3">
          <h3 className="text-base font-bold text-amber-400 flex items-center gap-2">
            <TrendingDown className="w-4 h-4" />
            Targeted Improvement Roadmap
          </h3>
          {report.improvement_recommendations && report.improvement_recommendations.length > 0 ? (
            <ul className="space-y-2 text-xs text-slate-300">
              {report.improvement_recommendations.map((rec, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                  <span className="leading-relaxed">{rec}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-slate-500 italic">
              No critical technical gaps or contradictions identified across tested items.
            </p>
          )}
        </div>
      </div>

      {/* Navigation Footer */}
      <div className="flex items-center justify-between pt-4">
        <button
          onClick={() => onNavigate('dashboard')}
          className="px-5 py-2.5 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
        >
          Return to Dashboard
        </button>

        <button
          onClick={() => onNavigate('interview')}
          className="px-6 py-2.5 rounded-xl text-xs font-bold bg-brand-600 hover:bg-brand-500 text-white flex items-center gap-2 shadow-sm transition-all"
        >
          Retake Another Mock Interview
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

