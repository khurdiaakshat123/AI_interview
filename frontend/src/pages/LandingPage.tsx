import React from 'react';
import { 
  Sparkles, Code2, Cpu, ShieldCheck, ArrowRight, CheckCircle2,
  Lock, Activity, Layers, Terminal, BookOpen, Clock, Target, Star
} from 'lucide-react';

interface LandingPageProps {
  onNavigate: (tab: string) => void;
  currentUser?: any;
  onOpenAuth?: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onNavigate, currentUser, onOpenAuth }) => {
  const handleAction = (tab: string) => {
    if (!currentUser && onOpenAuth) {
      onOpenAuth();
      return;
    }
    onNavigate(tab);
  };

  return (
    <div className="relative overflow-hidden pt-6 pb-24">
      {/* Ambient Background Glows */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[850px] h-[420px] bg-gradient-to-tr from-blue-600/20 via-indigo-600/15 to-violet-600/10 blur-[140px] pointer-events-none -z-10" />
      <div className="absolute top-[400px] left-1/4 w-[400px] h-[300px] bg-cyan-500/10 blur-[120px] pointer-events-none -z-10" />

      {/* Hero Section */}
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center pt-8 pb-12">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-slate-900/90 border border-white/10 text-sky-300 text-xs font-semibold tracking-wide mb-6 shadow-sm">
          <Sparkles className="w-3.5 h-3.5 text-sky-400" />
          The Intelligent Technical Hiring Preparation Studio
        </div>

        <h1 className="text-4xl sm:text-6xl font-extrabold text-white tracking-tight leading-[1.12] mb-6">
          Crack Company Coding OAs & <br />
          <span className="bg-gradient-to-r from-sky-400 via-indigo-300 to-violet-400 bg-clip-text text-transparent">
            Master 1-on-1 Technical Interviews
          </span>
        </h1>

        <p className="max-w-2xl mx-auto text-base sm:text-lg text-slate-300 leading-relaxed mb-8">
          Generic question banks don't reflect real technical hiring. <span className="text-white font-semibold">Intervyn</span> analyzes your target role, serves realistic timed assessments matching company hiring windows, and runs voice-enabled technical interviews with actionable, evidence-backed feedback.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-4">
          {!currentUser ? (
            <>
              <button
                onClick={onOpenAuth}
                className="flex items-center gap-3 px-8 py-4 rounded-xl font-bold text-sm bg-white hover:bg-slate-100 text-slate-900 shadow-xl shadow-white/10 transition-all transform hover:-translate-y-0.5 active:scale-[0.98]"
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                </svg>
                <span>Sign in with Google to Start</span>
                <ArrowRight className="w-4 h-4 text-slate-600" />
              </button>

              <button
                onClick={onOpenAuth}
                className="flex items-center gap-2 px-6 py-4 rounded-xl font-semibold text-sm bg-slate-900/90 hover:bg-slate-800 text-slate-200 border border-white/10 transition-all shadow-sm"
              >
                <Cpu className="w-4 h-4 text-sky-400" />
                <span>Explore Platform Features</span>
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => handleAction('dashboard')}
                className="flex items-center gap-2.5 px-7 py-3.5 rounded-xl font-bold text-sm bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-xl shadow-indigo-600/25 transition-all transform hover:-translate-y-0.5 active:scale-[0.98]"
              >
                Open Candidate Dashboard
                <ArrowRight className="w-4 h-4" />
              </button>

              <button
                onClick={() => handleAction('interview')}
                className="flex items-center gap-2 px-6 py-3.5 rounded-xl font-semibold text-sm bg-slate-900/90 hover:bg-slate-800 text-slate-200 border border-white/10 transition-all shadow-sm"
              >
                <Cpu className="w-4 h-4 text-sky-400" />
                Launch 1-on-1 AI Interview
              </button>
            </>
          )}
        </div>

        {/* Feature Badges */}
        <div className="mt-12 flex flex-wrap items-center justify-center gap-6 text-xs text-slate-300">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900/70 border border-white/5">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>Deterministic Rubric Scoring</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900/70 border border-white/5">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>18-Point Question Quality Standard</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900/70 border border-white/5">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>Real-World 7-Day Assessment Windows</span>
          </div>
        </div>
      </div>

      {/* Dual Pillars Section */}
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 mt-8">
        <div className="text-center mb-10">
          <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Two Complete Preparation Pillars. Zero Generic Advice.
          </h2>
          <p className="text-sm text-slate-400 mt-2">
            Tailored for high-impact roles at Google, Amazon, Microsoft, Stripe, and Uber.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          {/* Pillar 1: Coding Assessments & Practice */}
          <div className="rounded-2xl border border-white/10 bg-gradient-to-b from-slate-900/80 to-slate-950/90 p-6 sm:p-8 flex flex-col justify-between hover:border-white/20 transition-all shadow-xl shadow-black/40">
            <div>
              <div className="w-12 h-12 rounded-xl bg-sky-500/10 border border-sky-500/30 flex items-center justify-center mb-6 shadow-md shadow-sky-500/10">
                <Code2 className="w-6 h-6 text-sky-400" />
              </div>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-sky-400">Pillar 1</span>
                <span className="text-slate-600">•</span>
                <span className="text-xs text-slate-400 font-medium">Coding Assessments</span>
              </div>
              <h3 className="text-xl font-bold text-white mb-3">
                Targeted Practice & Timed Assessments
              </h3>
              <p className="text-slate-300 text-sm leading-relaxed mb-6">
                Parse job specifications to extract topic weights, practice with hints and full solutions, and take realistic 60-minute timed assessments matching real hiring cycles.
              </p>

              <ul className="space-y-3 text-sm text-slate-300 mb-8">
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
                  <span><strong>Role Topic Profiling:</strong> Extracts core subjects with prioritized importance weights</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
                  <span><strong>Personalized Practice:</strong> Structured hints, architectural approaches, and code solutions</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
                  <span><strong>Timed Exam Simulation:</strong> Realistic 60-minute exam environment synchronized across 7-day windows</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
                  <span><strong>Automated Test Runner:</strong> Monaco VS Code experience with hidden boundary & performance test cases</span>
                </li>
              </ul>
            </div>

            <button
              onClick={() => handleAction('practice')}
              className="w-full py-3 rounded-xl font-semibold text-sm bg-slate-800 hover:bg-slate-700 text-sky-300 border border-sky-500/30 flex items-center justify-center gap-2 transition-all shadow-sm"
            >
              Start Coding Practice
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>

          {/* Pillar 2: 1-on-1 AI Technical Interview */}
          <div className="rounded-2xl border border-white/10 bg-gradient-to-b from-slate-900/80 to-slate-950/90 p-6 sm:p-8 flex flex-col justify-between hover:border-white/20 transition-all shadow-xl shadow-black/40">
            <div>
              <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center mb-6 shadow-md shadow-indigo-500/10">
                <Cpu className="w-6 h-6 text-indigo-400" />
              </div>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-indigo-400">Pillar 2</span>
                <span className="text-slate-600">•</span>
                <span className="text-xs text-slate-400 font-medium">Interactive Interview</span>
              </div>
              <h3 className="text-xl font-bold text-white mb-3">
                1-on-1 AI Technical Interview
              </h3>
              <p className="text-slate-300 text-sm leading-relaxed mb-6">
                Experience an interview that sounds, feels, and questions like a senior staff engineer. Defend your real resume projects, explain trade-offs, and tackle adaptive follow-up depths.
              </p>

              <ul className="space-y-3 text-sm text-slate-300 mb-8">
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                  <span><strong>Resume Project Defense:</strong> Rigorously probes architecture choices and production trade-offs</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                  <span><strong>Computer Science Fundamentals:</strong> OS internals, distributed locks, database transactions, and caching</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                  <span><strong>Adaptive Follow-Ups:</strong> Evaluates answers in real time and probes deeper (Levels 1 through 5)</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                  <span><strong>Dual-Dimensional Scorecard:</strong> Detailed score breakdown for Project Defense and Subject Knowledge</span>
                </li>
              </ul>
            </div>

            <button
              onClick={() => handleAction('interview')}
              className="w-full py-3 rounded-xl font-semibold text-sm bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-600 hover:from-blue-500 hover:to-indigo-500 text-white flex items-center justify-center gap-2 transition-all shadow-md shadow-indigo-600/25"
            >
              Enter AI Interview Room
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* 3-Step Walkthrough Bar */}
        <div className="mt-14 p-8 rounded-2xl border border-white/10 bg-slate-900/60 backdrop-blur-md">
          <h3 className="text-center text-lg font-bold text-white mb-6">
            Three Steps to Interview Readiness
          </h3>
          <div className="grid md:grid-cols-3 gap-6">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-blue-500/15 border border-blue-500/30 flex items-center justify-center text-blue-400 font-bold text-xs shrink-0">
                1
              </div>
              <div>
                <h4 className="text-sm font-semibold text-white">Target Your Role</h4>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                  Select from top tech companies or paste any custom Job Description to generate topic profiles.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center text-indigo-400 font-bold text-xs shrink-0">
                2
              </div>
              <div>
                <h4 className="text-sm font-semibold text-white">Simulate Coding Assessments</h4>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                  Practice high-frequency topics or simulate full 60-minute assessments with VS Code Monaco editor.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-violet-500/15 border border-violet-500/30 flex items-center justify-center text-violet-400 font-bold text-xs shrink-0">
                3
              </div>
              <div>
                <h4 className="text-sm font-semibold text-white">Ace the AI Technical Interview</h4>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                  Speak out loud with continuous speech recognition and receive comprehensive audit scorecards.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
