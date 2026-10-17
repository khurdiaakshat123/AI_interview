import React from 'react';
import { 
  Code2, Cpu, ArrowRight, CheckCircle2,
  Terminal
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
    <div className="relative overflow-hidden pt-4 sm:pt-6 pb-16">
      {/* Ambient Background Glows */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[850px] h-[380px] bg-gradient-to-tr from-blue-600/20 via-indigo-600/15 to-violet-600/10 blur-[140px] pointer-events-none -z-10" />
      <div className="absolute top-[320px] left-1/4 w-[400px] h-[280px] bg-cyan-500/10 blur-[120px] pointer-events-none -z-10" />

      {/* Hero Title Section */}
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center pt-2 sm:pt-4 pb-5 sm:pb-6">
        <h1 className="text-3xl sm:text-4xl md:text-5xl font-extrabold text-white tracking-tight leading-[1.15]">
          Crack Company Coding OAs & <br />
          <span className="bg-gradient-to-r from-sky-400 via-indigo-300 to-violet-400 bg-clip-text text-transparent">
            Master 1-on-1 Technical Interviews
          </span>
        </h1>
      </div>

      {/* Dual Options Section - Visible on front screen without scrolling */}
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid md:grid-cols-2 gap-5 sm:gap-6">
          {/* Pillar 1: Coding Assessments & Practice */}
          <div className="rounded-2xl border border-white/10 bg-gradient-to-b from-slate-900/85 to-slate-950/95 p-5 sm:p-6 flex flex-col justify-between hover:border-white/20 transition-all shadow-xl shadow-black/40">
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="w-10 h-10 rounded-xl bg-sky-500/10 border border-sky-500/30 flex items-center justify-center shadow-md shadow-sky-500/10">
                  <Code2 className="w-5 h-5 text-sky-400" />
                </div>
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-sky-950/50 border border-sky-500/20 text-[11px] font-semibold text-sky-400">
                  <span>Pillar 1</span>
                  <span className="text-sky-600">•</span>
                  <span>Coding Assessments</span>
                </div>
              </div>

              <h3 className="text-lg sm:text-xl font-bold text-white mb-2">
                Targeted Practice & Timed Assessments
              </h3>
              <p className="text-slate-300 text-xs sm:text-sm leading-relaxed mb-4">
                Parse job specifications to extract topic weights, practice with hints and full solutions, and take realistic 60-minute timed assessments matching real hiring cycles.
              </p>

              <ul className="space-y-2 text-xs sm:text-sm text-slate-300 mb-6">
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
                  <span><strong>Role Topic Profiling:</strong> Extracts core subjects with prioritized importance weights</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
                  <span><strong>Personalized Practice:</strong> Structured hints, architectural approaches, and code solutions</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
                  <span><strong>Timed Exam Simulation:</strong> Realistic 60-minute exam environment synchronized across 7-day windows</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
                  <span><strong>Automated Test Runner:</strong> Monaco VS Code experience with hidden boundary & performance test cases</span>
                </li>
              </ul>
            </div>

            <div className="grid sm:grid-cols-2 gap-3 pt-1">
              <button
                onClick={() => handleAction('practice')}
                className="py-2.5 px-3 rounded-xl font-semibold text-xs sm:text-sm bg-slate-800 hover:bg-slate-700 text-sky-300 border border-sky-500/30 flex items-center justify-center gap-2 transition-all shadow-sm group"
                title="Start personalized coding practice with hints and solutions"
              >
                <Code2 className="w-4 h-4 text-sky-400 group-hover:scale-110 transition-transform" />
                <span>Skill Practice</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>

              <button
                onClick={() => handleAction('mock-oa')}
                className="py-2.5 px-3 rounded-xl font-semibold text-xs sm:text-sm bg-gradient-to-r from-sky-600/30 via-indigo-600/30 to-blue-600/30 hover:from-sky-600/45 hover:to-indigo-600/45 text-sky-200 border border-sky-400/40 flex items-center justify-center gap-2 transition-all shadow-sm group"
                title="Start a 60-minute realistic company coding assessment"
              >
                <Terminal className="w-4 h-4 text-cyan-400 group-hover:scale-110 transition-transform" />
                <span>Timed Assessment (OA)</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Pillar 2: 1-on-1 AI Technical Interview */}
          <div className="rounded-2xl border border-white/10 bg-gradient-to-b from-slate-900/85 to-slate-950/95 p-5 sm:p-6 flex flex-col justify-between hover:border-white/20 transition-all shadow-xl shadow-black/40">
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center shadow-md shadow-indigo-500/10">
                  <Cpu className="w-5 h-5 text-indigo-400" />
                </div>
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-indigo-950/50 border border-indigo-500/20 text-[11px] font-semibold text-indigo-400">
                  <span>Pillar 2</span>
                  <span className="text-indigo-600">•</span>
                  <span>Interactive Interview</span>
                </div>
              </div>

              <h3 className="text-lg sm:text-xl font-bold text-white mb-2">
                1-on-1 AI Technical Interview
              </h3>
              <p className="text-slate-300 text-xs sm:text-sm leading-relaxed mb-4">
                Experience an interview that sounds, feels, and questions like a senior staff engineer. Defend your real resume projects, explain trade-offs, and tackle adaptive follow-up depths.
              </p>

              <ul className="space-y-2 text-xs sm:text-sm text-slate-300 mb-6">
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                  <span><strong>Resume Project Defense:</strong> Rigorously probes architecture choices and production trade-offs</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                  <span><strong>Computer Science Fundamentals:</strong> OS internals, distributed locks, database transactions, and caching</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                  <span><strong>Adaptive Follow-Ups:</strong> Evaluates answers in real time and probes deeper (Levels 1 through 5)</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                  <span><strong>Dual-Dimensional Scorecard:</strong> Detailed score breakdown for Project Defense and Subject Knowledge</span>
                </li>
              </ul>
            </div>

            <div className="pt-1">
              <button
                onClick={() => handleAction('interview')}
                className="w-full py-2.5 rounded-xl font-semibold text-xs sm:text-sm bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-600 hover:from-blue-500 hover:to-indigo-500 text-white flex items-center justify-center gap-2 transition-all shadow-md shadow-indigo-600/25 group"
              >
                <Cpu className="w-4 h-4 text-white group-hover:scale-110 transition-transform" />
                <span>Enter AI Interview Room</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
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
