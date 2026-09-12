import React, { useState } from 'react';
import { 
  Trophy, Star, CheckCircle2, AlertCircle, ShieldCheck, ChevronDown,
  ChevronUp, ArrowRight, Layers, Cpu, Award, TrendingUp, TrendingDown
} from 'lucide-react';
import { InterviewFinalReport, InterviewEvidenceRecord } from '../types';
import { StarRating } from '../components/StarRating';

interface InterviewReportPageProps {
  report: InterviewFinalReport;
  onNavigate: (tab: string, state?: any) => void;
}

export const InterviewReportPage: React.FC<InterviewReportPageProps> = ({ report, onNavigate }) => {
  const [expandedEvidenceId, setExpandedEvidenceId] = useState<string | null>(null);

  const toggleEvidence = (id: string) => {
    setExpandedEvidenceId(expandedEvidenceId === id ? null : id);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header Banner */}
      <div className="p-6 sm:p-8 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900 to-indigo-950/40 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div className="inline-flex items-center gap-2 text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-2">
            <Award className="w-4 h-4" />
            Comprehensive Evaluation & Performance Report
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">
            Final Technical Interview Evaluation
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Candidate: <span className="text-white font-medium">{report.candidate_name}</span> • Target:{' '}
            <span className="text-brand-300 font-medium">{report.company} ({report.role})</span>
          </p>
        </div>

        {/* Dual Headline Score Cards (§6.5) */}
        <div className="flex flex-wrap items-center gap-4">
          {/* Card 1: Resume Defense */}
          <div className="p-4 rounded-2xl bg-slate-950/80 border border-slate-800 text-center min-w-[170px]">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Resume Defense
            </div>
            <div className="text-3xl font-extrabold text-white font-mono my-1">
              {report.resume_related_score.toFixed(1)}
              <span className="text-sm font-normal text-slate-500"> / 100</span>
            </div>
            <div className="text-[10px] text-amber-400 font-mono">
              ★ {(report.resume_related_score / 20).toFixed(2)} / 5.0 Stars
            </div>
          </div>

          {/* Card 2: Subject Knowledge */}
          <div className="p-4 rounded-2xl bg-slate-950/80 border border-slate-800 text-center min-w-[170px]">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Subject Knowledge
            </div>
            <div className="text-3xl font-extrabold text-indigo-300 font-mono my-1">
              {report.subject_knowledge_score.toFixed(1)}
              <span className="text-sm font-normal text-slate-500"> / 100</span>
            </div>
            <div className="text-[10px] text-indigo-400 font-mono">
              Deterministic CS Core
            </div>
          </div>
        </div>
      </div>

      {/* 5-Star Project Cards Grid (§6.2) */}
      <div className="space-y-4">
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <Star className="w-5 h-5 text-amber-400 fill-current" />
          Project Defense 5-Star Performance Cards
        </h2>

        <div className="grid md:grid-cols-2 gap-6">
          {report.project_cards.map((card, idx) => (
            <div
              key={idx}
              className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col justify-between space-y-4"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <h3 className="text-base font-bold text-white">{card.title}</h3>
                  <StarRating rating={card.star_rating} size="sm" />
                </div>

                <div className="flex flex-wrap items-center gap-1.5 mb-4">
                  {card.topics_covered.map((t, i) => (
                    <span key={i} className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300">
                      {t}
                    </span>
                  ))}
                </div>

                {/* Strengths & Identified Gaps */}
                <div className="space-y-2 text-xs">
                  <div>
                    <span className="font-semibold text-emerald-400">Strengths:</span>
                    <ul className="list-disc list-inside text-slate-300 mt-1 space-y-0.5">
                      {card.strengths.map((str, sIdx) => (
                        <li key={sIdx}>{str}</li>
                      ))}
                    </ul>
                  </div>

                  {card.identified_gaps.length > 0 && (
                    <div>
                      <span className="font-semibold text-amber-400">Identified Gaps:</span>
                      <ul className="list-disc list-inside text-slate-300 mt-1 space-y-0.5">
                        {card.identified_gaps.map((gap, gIdx) => (
                          <li key={gIdx}>{gap}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>

              <div className="pt-3 border-t border-slate-800 text-xs text-slate-500 font-mono">
                Project Score: {card.score.toFixed(1)} / 100 • Weight: {card.relevance_weight}x
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Subject Topic Mastery Grid (§6.3) */}
      <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4">
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <Cpu className="w-5 h-5 text-indigo-400" />
          Core Subject Mastery Breakdown
        </h2>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Object.entries(report.subject_topic_breakdown).map(([top, status], idx) => {
            const isStrong = status === 'STRONG';
            const isPartial = status === 'PARTIAL';
            const isWeak = status === 'WEAK';

            return (
              <div
                key={idx}
                className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 flex flex-col justify-between space-y-2"
              >
                <span className="text-xs font-semibold text-slate-200">{top}</span>
                <span
                  className={`self-start px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase ${
                    isStrong
                      ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                      : isPartial
                      ? 'bg-amber-950 text-amber-300 border border-amber-800'
                      : isWeak
                      ? 'bg-rose-950 text-rose-300 border border-rose-800'
                      : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  {status}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Audit Trail Drawer (§6.2 - Stored Evidence Records) */}
      <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
              Traceable Evidence Audit Trail
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Every score point is backed by a stored evidence record. Never ungrounded LLM verdicts.
            </p>
          </div>
          <span className="px-3 py-1 rounded-xl bg-slate-800 text-slate-300 font-mono text-xs font-semibold">
            {report.evidence_trail.length} Evidence Records
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
                  className="p-4 flex items-center justify-between gap-4 cursor-pointer hover:bg-slate-900/60"
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
                      +{ev.earned_points} / {ev.possible_points} pts
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
                        <span className="font-bold text-slate-400 block mb-1">Expected Concept:</span>
                        <p className="text-slate-300">{ev.expected_concept}</p>
                      </div>

                      <div className="p-3 rounded-lg bg-slate-950 border border-slate-800/80">
                        <span className="font-bold text-slate-400 block mb-1">Evaluator Reason:</span>
                        <p className="text-slate-300">{ev.evaluator_reason}</p>
                      </div>
                    </div>

                    {ev.detected_gap && (
                      <div className="p-2.5 rounded-lg bg-amber-950/30 border border-amber-800/40 text-amber-200">
                        <span className="font-bold">Detected Gap ({ev.severity}):</span> {ev.detected_gap}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Strengths & Improvement Roadmap */}
      <div className="grid md:grid-cols-2 gap-6">
        <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-3">
          <h3 className="text-base font-bold text-emerald-400 flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            Key Technical Strengths
          </h3>
          <ul className="space-y-2 text-xs text-slate-300">
            {report.strengths.map((str, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <span>{str}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-3">
          <h3 className="text-base font-bold text-amber-400 flex items-center gap-2">
            <TrendingDown className="w-4 h-4" />
            Targeted Improvement Roadmap
          </h3>
          <ul className="space-y-2 text-xs text-slate-300">
            {report.improvement_recommendations.map((rec, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                <span>{rec}</span>
              </li>
            ))}
          </ul>
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
