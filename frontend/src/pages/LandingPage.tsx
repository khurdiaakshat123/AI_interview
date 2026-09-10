import React from 'react';
import { 
  Sparkles, Code2, Cpu, ShieldCheck, ArrowRight, CheckCircle2,
  Lock, Activity, Layers, Terminal, BookOpen, Clock, Target, Star
} from 'lucide-react';

interface LandingPageProps {
  onNavigate: (tab: string) => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onNavigate }) => {
  return (
    <div className="relative overflow-hidden pt-6 pb-24">
      {/* Background Decorative Gradients */}
      <div className="absolute top-10 left-1/2 -translate-x-1/2 w-[700px] h-[350px] bg-gradient-to-tr from-brand-600/20 to-indigo-600/10 blur-[120px] pointer-events-none -z-10" />

      {/* Hero Section */}
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center pt-8 pb-12">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-brand-950/80 border border-brand-800/60 text-brand-300 text-xs font-semibold uppercase tracking-wider mb-6 shadow-sm">
          <Sparkles className="w-3.5 h-3.5 text-brand-400" />
          Evidence-Grounded AI Hiring & Assessment Platform
        </div>

        <h1 className="text-4xl sm:text-6xl font-extrabold text-white tracking-tight leading-[1.15] mb-6">
          Master Company-Specific OAs & <br />
          <span className="bg-gradient-to-r from-brand-400 via-indigo-300 to-cyan-300 bg-clip-text text-transparent">
            Adaptive AI Mock Interviews
          </span>
        </h1>

        <p className="max-w-2xl mx-auto text-base sm:text-lg text-slate-400 leading-relaxed mb-8">
          Stop practicing random question banks. <span className="text-slate-200 font-medium">Intervyn</span> extracts the exact topic priorities for your target role, serves canonical 7-day Mock OAs, and conducts deep situational interviews with deterministic audit-ready scoring.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-4">
          <button
            onClick={() => onNavigate('dashboard')}
            className="flex items-center gap-2.5 px-6 py-3.5 rounded-xl font-bold text-sm bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white shadow-lg shadow-brand-500/25 transition-all transform hover:-translate-y-0.5"
          >
            Launch Preparation Dashboard
            <ArrowRight className="w-4 h-4" />
          </button>

          <button
            onClick={() => onNavigate('interview')}
            className="flex items-center gap-2 px-5 py-3.5 rounded-xl font-semibold text-sm bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 border border-slate-700 transition-all"
          >
            <Cpu className="w-4 h-4 text-brand-400" />
            Try Live AI Interview
          </button>
        </div>

        {/* Feature Badges */}
        <div className="mt-12 flex flex-wrap items-center justify-center gap-6 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>Deterministic Scoring Formula (§6.2)</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>18-Point Verification Pipeline (§5.4)</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>Canonical 7-Day Rolling OA Windows (§5.3)</span>
          </div>
        </div>
      </div>

      {/* Dual Subsystem Grid */}
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 mt-6">
        <div className="text-center mb-10">
          <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Two Integrated Systems. Zero Generic Answers.
          </h2>
          <p className="text-sm text-slate-400 mt-2">
            Designed for high-bar technical hiring pipelines at Google, Amazon, Microsoft, and Uber.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          {/* Subsystem A: OA Preparation */}
          <div className="rounded-2xl border border-slate-800 bg-gradient-to-b from-slate-900/90 to-slate-950 p-6 sm:p-8 flex flex-col justify-between hover:border-slate-700 transition-all">
            <div>
              <div className="w-12 h-12 rounded-xl bg-brand-500/10 border border-brand-500/30 flex items-center justify-center mb-6">
                <Code2 className="w-6 h-6 text-brand-400" />
              </div>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-brand-400">System A</span>
                <span className="text-slate-600">•</span>
                <span className="text-xs text-slate-400">Online Assessment</span>
              </div>
              <h3 className="text-xl font-bold text-white mb-3">
                Role-Grounded OA Preparation & Mock Exam
              </h3>
              <p className="text-slate-400 text-sm leading-relaxed mb-6">
                Parses the exact Job Description to compute role topic profiles, generates deterministic SHA-256 practice questions, and administers realistic, timed Mock OAs matching company hiring windows.
              </p>

              <ul className="space-y-2.5 text-sm text-slate-300 mb-8">
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-brand-400 shrink-0 mt-0.5" />
                  <span><strong>Agent 1:</strong> Role Topic Profile with importance weights (0-1)</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-brand-400 shrink-0 mt-0.5" />
                  <span><strong>Agent 2:</strong> Practice Engine with Hint, Approach & Full Solution</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-brand-400 shrink-0 mt-0.5" />
                  <span><strong>Agent 3:</strong> Canonical Mock OA identical for all users in the 7-day window</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-brand-400 shrink-0 mt-0.5" />
                  <span><strong>Agent 5:</strong> Evaluator Registry for DSA test cases, SQL & rubrics</span>
                </li>
              </ul>
            </div>

            <button
              onClick={() => onNavigate('jd-intake')}
              className="w-full py-3 rounded-xl font-semibold text-sm bg-slate-800 hover:bg-slate-700 text-brand-300 border border-brand-700/40 flex items-center justify-center gap-2 transition-all"
            >
              Analyze Job Description
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>

          {/* Subsystem B: AI Mock Interview */}
          <div className="rounded-2xl border border-slate-800 bg-gradient-to-b from-slate-900/90 to-slate-950 p-6 sm:p-8 flex flex-col justify-between hover:border-slate-700 transition-all">
            <div>
              <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center mb-6">
                <Cpu className="w-6 h-6 text-indigo-400" />
              </div>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-indigo-400">System B</span>
                <span className="text-slate-600">•</span>
                <span className="text-xs text-slate-400">Adaptive Mock Interview</span>
              </div>
              <h3 className="text-xl font-bold text-white mb-3">
                Evidence-Backed Situational Interview
              </h3>
              <p className="text-slate-400 text-sm leading-relaxed mb-6">
                Interviews you like a senior staff engineer: starting from your most relevant resume projects, questioning trade-offs and failure modes, adaptively exploring follow-up depths (up to Level 5), and auditing every point.
              </p>

              <ul className="space-y-2.5 text-sm text-slate-300 mb-8">
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                  <span><strong>Agent 1:</strong> Project Defense prioritized by JD relevance</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                  <span><strong>Agent 2:</strong> Core Fundamentals (OS, Concurrency, SQL, System Design)</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                  <span><strong>Follow-up FSM:</strong> Adaptive branching (Level 1 to 5)</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                  <span><strong>Dual Headline Report:</strong> Resume Score /100 and Subject Score /100</span>
                </li>
              </ul>
            </div>

            <button
              onClick={() => onNavigate('interview')}
              className="w-full py-3 rounded-xl font-semibold text-sm bg-indigo-600 hover:bg-indigo-500 text-white flex items-center justify-center gap-2 transition-all shadow-md shadow-indigo-600/20"
            >
              Start Live Interview Session
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
