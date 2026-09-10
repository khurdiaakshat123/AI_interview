import React from 'react';
import { 
  Trophy, Clock, CheckCircle2, XCircle, ArrowRight, BarChart3,
  TrendingUp, TrendingDown, Layers, ChevronRight, Check, X, RotateCcw
} from 'lucide-react';
import { MockOAReport } from '../types';

interface OAReportPageProps {
  report: MockOAReport;
  onNavigate: (tab: string, state?: any) => void;
}

export const OAReportPage: React.FC<OAReportPageProps> = ({ report, onNavigate }) => {
  const isPassed = report.percentage >= 70;

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Banner */}
      <div className="p-6 sm:p-8 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900 to-brand-950/40 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div className="inline-flex items-center gap-2 text-xs font-semibold text-brand-400 uppercase tracking-wider mb-2">
            <Trophy className="w-4 h-4" />
            Agent 5 Assessment Evaluation
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">
            Online Assessment Performance Scorecard
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            {report.company} • {report.role} (Variant #{report.attempt_number})
          </p>
        </div>

        {/* Score Pill */}
        <div className="flex items-center gap-4 bg-slate-950/80 border border-slate-800 p-4 rounded-2xl">
          <div className="text-right">
            <div className="text-xs text-slate-400 uppercase tracking-wider">Candidate Score</div>
            <div className="text-3xl font-extrabold text-white font-mono">
              {report.total_score.toFixed(1)} <span className="text-sm font-normal text-slate-500">/ 100</span>
            </div>
          </div>

          <div
            className={`px-3.5 py-2 rounded-xl text-xs font-bold uppercase ${
              isPassed
                ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                : 'bg-amber-950 text-amber-300 border border-amber-800'
            }`}
          >
            {isPassed ? 'OA Cleared' : 'Needs Practice'}
          </div>
        </div>
      </div>

      {/* Topic Accuracy & Timing Grid */}
      <div className="grid md:grid-cols-3 gap-6">
        {/* Topic Accuracy Breakdown */}
        <div className="md:col-span-2 p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-brand-400" />
            Topic-Wise Mastery & Accuracy
          </h2>

          <div className="space-y-4">
            {Object.entries(report.accuracy_by_topic).map(([topic, stat], idx) => (
              <div key={idx} className="space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-200">{topic}</span>
                  <span className="font-mono text-slate-400">
                    {stat.earned} / {stat.possible} pts ({Math.round(stat.accuracy_percentage)}%)
                  </span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-950 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      stat.accuracy_percentage >= 75
                        ? 'bg-emerald-500'
                        : stat.accuracy_percentage >= 50
                        ? 'bg-amber-500'
                        : 'bg-rose-500'
                    }`}
                    style={{ width: `${stat.accuracy_percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Strong vs Weak Areas */}
        <div className="space-y-4">
          <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-3">
            <div className="flex items-center gap-2 text-xs font-bold text-emerald-400 uppercase tracking-wider">
              <TrendingUp className="w-4 h-4" />
              Identified Strengths
            </div>
            {report.strong_topics.length > 0 ? (
              <div className="space-y-1.5">
                {report.strong_topics.map((t, i) => (
                  <div key={i} className="text-xs text-slate-300 flex items-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span>{t}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">No topics reached &gt;= 75% accuracy.</p>
            )}
          </div>

          <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-3">
            <div className="flex items-center gap-2 text-xs font-bold text-rose-400 uppercase tracking-wider">
              <TrendingDown className="w-4 h-4" />
              Focus Areas for Improvement
            </div>
            {report.weak_topics.length > 0 ? (
              <div className="space-y-1.5">
                {report.weak_topics.map((t, i) => (
                  <div key={i} className="text-xs text-slate-300 flex items-center gap-2">
                    <XCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                    <span>{t}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-emerald-400 italic">No weak topics below 60% detected!</p>
            )}
          </div>
        </div>
      </div>

      {/* Detailed Question Review List */}
      <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4">
        <h2 className="text-lg font-bold text-white">
          Question-by-Question Post-Mortem & Answer Keys
        </h2>

        <div className="space-y-4">
          {report.questions_review.map((q, idx) => (
            <div
              key={idx}
              className={`p-5 rounded-xl border text-xs space-y-3 ${
                q.is_correct
                  ? 'bg-slate-950/60 border-emerald-900/40'
                  : 'bg-slate-950/60 border-rose-900/40'
              }`}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-slate-200">Q{idx + 1}: {q.title || q.topic}</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-800 text-slate-300">
                    {q.question_type}
                  </span>
                </div>

                <div className="flex items-center gap-3 font-mono">
                  <span className={q.is_correct ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>
                    {q.is_correct ? 'PASSED (+100%)' : 'MISSED (0%)'}
                  </span>
                </div>
              </div>

              <p className="text-slate-400">{q.prompt.slice(0, 180)}...</p>

              <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 space-y-1.5 font-mono text-[11px]">
                <div className="flex items-start gap-2">
                  <span className="text-slate-500 shrink-0">Your Answer:</span>
                  <span className={q.is_correct ? 'text-emerald-300' : 'text-rose-300'}>
                    {String(q.user_answer || '(No submission)')}
                  </span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-slate-500 shrink-0">Reference Solution:</span>
                  <span className="text-slate-200">{String(q.correct_answer)}</span>
                </div>
                {q.approach && (
                  <div className="text-[11px] text-brand-300 pt-1 border-t border-slate-800 font-sans">
                    <strong>Optimal Invariant:</strong> {q.approach}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Next Step Action */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-6 rounded-2xl bg-gradient-to-r from-indigo-950/60 to-slate-900 border border-indigo-800/50">
        <div>
          <h3 className="text-base font-bold text-white">Ready for Technical Interview Defense?</h3>
          <p className="text-xs text-slate-400 mt-1">
            Now that you've completed the OA, test your situational project reasoning with Intervyn's AI interviewer.
          </p>
        </div>

        <button
          onClick={() => onNavigate('interview', { company: report.company, role: report.role })}
          className="px-6 py-3 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white flex items-center gap-2 transition-all shadow-md shadow-indigo-600/25"
        >
          Proceed to AI Mock Interview
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
