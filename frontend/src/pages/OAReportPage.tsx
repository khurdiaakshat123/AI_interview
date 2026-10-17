import React from 'react';
import { 
  Trophy, Clock, CheckCircle2, XCircle, ArrowRight, BarChart3,
  TrendingUp, TrendingDown, Layers, ChevronRight, Check, X, RotateCcw,
  ShieldCheck, ShieldAlert
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
      <div className="p-6 sm:p-8 rounded-xl bg-surface border border-border flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div className="inline-flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-text-muted mb-2">
            <Trophy className="w-3.5 h-3.5 text-accent" />
            Assessment Evaluation
          </div>
          <h1 className="text-2xl sm:text-3xl font-serif text-text font-normal tracking-tight">
            Online Assessment Performance Scorecard
          </h1>
          <p className="text-xs sm:text-sm text-text-muted mt-1.5 leading-relaxed font-mono">
            {report.company} • {report.role} (Variant #{report.attempt_number})
          </p>
        </div>

        {/* Score Pill */}
        <div className="flex items-center gap-4 bg-bg border border-border p-4 rounded-xl">
          <div className="text-right">
            <div className="text-[10px] text-text-muted uppercase font-mono tracking-wider">Candidate Score</div>
            <div className="text-3xl font-mono text-text">
              {report.total_score.toFixed(1)} <span className="text-sm font-normal text-text-muted">/ 100</span>
            </div>
          </div>

          <div
            className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium uppercase ${
              isPassed
                ? 'bg-success/15 text-success border border-success/30'
                : 'bg-accent/15 text-accent border border-accent/30'
            }`}
          >
            {isPassed ? 'OA Cleared' : 'Needs Practice'}
          </div>
        </div>
      </div>

      {/* Topic Accuracy & Timing Grid */}
      <div className="grid md:grid-cols-3 gap-6">
        {/* Topic Accuracy Breakdown */}
        <div className="md:col-span-2 p-6 rounded-xl bg-surface border border-border space-y-4">
          <h2 className="text-base font-semibold text-text flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-accent" />
            Topic-Wise Mastery & Accuracy
          </h2>

          <div className="space-y-4">
            {Object.entries(report.accuracy_by_topic).map(([topic, stat], idx) => (
              <div key={idx} className="space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-text">{topic}</span>
                  <span className="font-mono text-text-muted">
                    {stat.earned} / {stat.possible} pts ({Math.round(stat.accuracy_percentage)}%)
                  </span>
                </div>
                <div className="w-full h-1.5 rounded-full bg-border overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      stat.accuracy_percentage >= 75
                        ? 'bg-success'
                        : stat.accuracy_percentage >= 50
                        ? 'bg-accent'
                        : 'bg-danger'
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
          <div className="p-5 rounded-xl bg-surface border border-border space-y-3">
            <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-success">
              <TrendingUp className="w-3.5 h-3.5" />
              Identified Strengths
            </div>
            {report.strong_topics.length > 0 ? (
              <div className="space-y-1.5">
                {report.strong_topics.map((t, i) => (
                  <div key={i} className="text-xs text-text flex items-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-success shrink-0" />
                    <span>{t}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-text-muted italic">No topics reached &gt;= 75% accuracy.</p>
            )}
          </div>

          <div className="p-5 rounded-xl bg-surface border border-border space-y-3">
            <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-danger">
              <TrendingDown className="w-3.5 h-3.5" />
              Focus Areas for Improvement
            </div>
            {report.weak_topics.length > 0 ? (
              <div className="space-y-1.5">
                {report.weak_topics.map((t, i) => (
                  <div key={i} className="text-xs text-text flex items-center gap-2">
                    <XCircle className="w-3.5 h-3.5 text-danger shrink-0" />
                    <span>{t}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-success italic">No weak topics below 60% detected!</p>
            )}
          </div>
        </div>
      </div>

      {/* Assessment Integrity & Proctoring Audit Card */}
      {report.proctoring_summary && (
        <div className="p-6 rounded-xl bg-surface border border-border space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-lg bg-bg border border-border flex items-center justify-center">
                <ShieldCheck className="w-5 h-5 text-accent" />
              </div>
              <div>
                <h2 className="text-base font-semibold text-text">Assessment Integrity & Proctoring Audit</h2>
                <p className="text-xs text-text-muted">Autonomous browser focus, tab activity, and paste telemetry analysis</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="text-right">
                <div className="text-[10px] text-text-muted font-mono uppercase tracking-wider">Integrity Score</div>
                <div className="text-2xl font-mono text-text">
                  {report.proctoring_summary.integrity_score}%
                </div>
              </div>
              <span className={`px-2.5 py-1 rounded text-xs font-mono uppercase tracking-wider font-medium ${
                report.proctoring_summary.integrity_score >= 85
                  ? 'bg-success/15 text-success border border-success/30'
                  : report.proctoring_summary.integrity_score >= 65
                  ? 'bg-accent/15 text-accent border border-accent/30'
                  : 'bg-danger/15 text-danger border border-danger/30'
              }`}>
                {report.proctoring_summary.integrity_status.replace(/_/g, ' ')}
              </span>
            </div>
          </div>

          {/* Metric Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
            <div className="p-3.5 rounded-lg bg-bg border border-border text-center">
              <div className="text-[11px] text-text-muted font-mono">Tab Switches</div>
              <div className="text-lg font-mono text-text mt-0.5">
                {report.proctoring_summary.tab_switch_count}
              </div>
            </div>
            <div className="p-3.5 rounded-lg bg-bg border border-border text-center">
              <div className="text-[11px] text-text-muted font-mono">Focus Loss Events</div>
              <div className="text-lg font-mono text-text mt-0.5">
                {report.proctoring_summary.window_blur_count}
              </div>
            </div>
            <div className="p-3.5 rounded-lg bg-bg border border-border text-center">
              <div className="text-[11px] text-text-muted font-mono">Time Away</div>
              <div className="text-lg font-mono text-text mt-0.5">
                {report.proctoring_summary.total_time_away_seconds}s
              </div>
            </div>
            <div className="p-3.5 rounded-lg bg-bg border border-border text-center">
              <div className="text-[11px] text-text-muted font-mono">Paste Bursts</div>
              <div className="text-lg font-mono text-text mt-0.5">
                {report.proctoring_summary.paste_burst_count}
              </div>
            </div>
          </div>

          {/* Incident Log if any */}
          {report.proctoring_summary.incidents && report.proctoring_summary.incidents.length > 0 && (
            <div className="space-y-2 pt-2">
              <div className="text-xs font-mono uppercase text-text-muted">Logged Telemetry Incidents</div>
              <div className="max-h-40 overflow-y-auto space-y-1.5 text-xs pr-1 font-mono">
                {report.proctoring_summary.incidents.map((inc, i) => (
                  <div key={i} className="p-2.5 rounded-lg bg-bg border border-border flex items-center justify-between text-[11px]">
                    <div className="text-text">{inc.detail}</div>
                    <span className="text-text-muted shrink-0 ml-2">{inc.timestamp}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Detailed Question Review List */}
      <div className="p-6 rounded-xl bg-surface border border-border space-y-4">
        <h2 className="text-xl font-serif text-text font-normal">
          Question-by-Question Post-Mortem & Answer Keys
        </h2>

        <div className="space-y-4">
          {report.questions_review.map((q, idx) => (
            <div
              key={idx}
              className={`p-5 rounded-lg border text-xs space-y-3 bg-bg ${
                q.is_correct
                  ? 'border-border'
                  : 'border-danger/30'
              }`}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-text">Q{idx + 1}: {q.title || q.topic}</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-surface border border-border text-text-muted">
                    {q.question_type}
                  </span>
                </div>

                <div className="flex items-center gap-3 font-mono">
                  <span className={q.is_correct ? 'text-success font-medium' : 'text-danger font-medium'}>
                    {q.is_correct ? 'PASSED (+100%)' : 'MISSED (0%)'}
                  </span>
                </div>
              </div>

              <p className="text-text-muted leading-relaxed">{q.prompt.slice(0, 180)}...</p>

              <div className="p-3 rounded-lg bg-surface border border-border space-y-1.5 font-mono text-[11px]">
                <div className="flex items-start gap-2">
                  <span className="text-text-muted shrink-0">Your Answer:</span>
                  <span className={q.is_correct ? 'text-success' : 'text-danger'}>
                    {String(q.user_answer || '(No submission)')}
                  </span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-text-muted shrink-0">Reference Solution:</span>
                  <span className="text-text">{String(q.correct_answer)}</span>
                </div>
                {q.approach && (
                  <div className="text-[11px] text-accent pt-1 border-t border-border font-sans">
                    <strong>Optimal Invariant:</strong> {q.approach}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Next Step Action */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-6 rounded-xl bg-surface border border-border">
        <div>
          <h3 className="text-base font-serif text-text font-normal">Ready for Technical Interview Defense?</h3>
          <p className="text-xs text-text-muted mt-1 leading-relaxed">
            Now that you've completed the OA, test your situational project reasoning with Intervyn's AI interviewer.
          </p>
        </div>

        <button
          onClick={() => onNavigate('interview', { company: report.company, role: report.role })}
          className="px-6 py-2.5 rounded-lg text-xs font-medium bg-accent text-accent-contrast hover:opacity-90 flex items-center gap-2 transition-opacity"
        >
          Proceed to AI Mock Interview
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
