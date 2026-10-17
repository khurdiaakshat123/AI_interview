import React from 'react';
import { ArrowRight, Terminal, Code2, Cpu } from 'lucide-react';

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
    <div className="py-8 sm:py-12 px-4 sm:px-6">
      <div className="max-w-[1100px] mx-auto">
        {/* Left-Aligned Editorial Hero Headline */}
        <div className="mb-10 sm:mb-12">
          <h1 className="font-serif text-[clamp(34px,4.2vw,46px)] leading-[1.15] tracking-[-0.01em] text-text font-normal max-w-[22ch] [text-wrap:balance]">
            Prepare for Company OAs &amp; 1-on-1 Technical Interviews
          </h1>
          <p className="mt-3 text-[15px] leading-[1.6] text-text-muted max-w-[60ch] font-sans">
            Timed assessments modeled on how each company hires, plus AI interviews that question you on your own resume projects.
          </p>
        </div>

        {/* Two-Column Grid: 5fr / 7fr with Interview as primary focus */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
          {/* Left Column (5fr): Practice & Timed Assessments */}
          <div className="lg:col-span-5 bg-surface border border-border rounded-[12px] p-8 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <span className="text-[12px] font-mono uppercase tracking-[0.06em] text-text-muted">
                  ASSESSMENTS
                </span>
              </div>

              <h2 className="text-[20px] font-semibold text-text tracking-tight mb-2 font-sans">
                Practice &amp; Timed Assessments
              </h2>
              
              <p className="text-[15px] leading-[1.6] text-text-muted mb-6 font-sans">
                Paste a job description, get topics ranked by weight, practice with hints, then sit a 60-minute timed OA.
              </p>

              <ul className="space-y-3 text-[14px] text-text-muted mb-8 font-sans">
                <li className="flex items-start gap-2.5">
                  <span className="text-text-muted select-none font-mono mt-0.5">—</span>
                  <span>Extracts core subjects with prioritized importance weights</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="text-text-muted select-none font-mono mt-0.5">—</span>
                  <span>Personalized hints, architectural approaches, and code solutions</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="text-text-muted select-none font-mono mt-0.5">—</span>
                  <span>60-minute exam simulation matching real 7-day hiring cycles</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="text-text-muted select-none font-mono mt-0.5">—</span>
                  <span>Monaco editor with hidden boundary and performance test cases</span>
                </li>
              </ul>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-auto pt-4">
              <button
                onClick={() => handleAction('practice')}
                className="h-10 px-4 rounded-md border border-border bg-transparent text-text hover:bg-surface-hover hover:border-border-focus font-sans text-[14px] font-medium flex items-center justify-center gap-2 transition-colors"
                title="Start personalized coding practice with hints and solutions"
              >
                <span>Skill Practice</span>
                <ArrowRight className="w-3.5 h-3.5 text-text-muted" />
              </button>

              <button
                onClick={() => handleAction('mock-oa')}
                className="h-10 px-4 rounded-md border border-border bg-transparent text-text hover:bg-surface-hover hover:border-border-focus font-sans text-[14px] font-medium flex items-center justify-center gap-2 transition-colors"
                title="Start a 60-minute realistic company coding assessment"
              >
                <span>Timed Assessment (OA)</span>
                <ArrowRight className="w-3.5 h-3.5 text-text-muted" />
              </button>
            </div>
          </div>

          {/* Right Column (7fr): AI Technical Interview - Primary Focus */}
          <div className="lg:col-span-7 bg-surface border border-border rounded-[12px] p-8 flex flex-col justify-between relative">
            <div>
              <div className="flex items-center justify-between mb-4">
                <span className="text-[12px] font-mono uppercase tracking-[0.06em] text-accent">
                  PRIMARY FOCUS
                </span>
                <span className="text-[12px] font-mono text-text-muted">
                  Adaptive 5-level depth
                </span>
              </div>

              <h2 className="text-[20px] font-semibold text-text tracking-tight mb-2 font-sans">
                AI Technical Interview
              </h2>

              <p className="text-[15px] leading-[1.6] text-text-muted mb-6 font-sans">
                Questions come from your own resume projects, with follow-ups up to five levels deep. You get two scores: project defense and CS fundamentals.
              </p>

              <ul className="space-y-3 text-[14px] text-text-muted mb-6 font-sans">
                <li className="flex items-start gap-2.5">
                  <span className="text-accent select-none font-mono mt-0.5">—</span>
                  <span>Rigorously probes architecture choices and production trade-offs</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="text-accent select-none font-mono mt-0.5">—</span>
                  <span>Probes OS internals, distributed locks, database transactions, and caching</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="text-accent select-none font-mono mt-0.5">—</span>
                  <span>Evaluates answers in real time and probes deeper (levels 1 through 5)</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="text-accent select-none font-mono mt-0.5">—</span>
                  <span>Dual-dimensional scorecard for project defense and subject knowledge</span>
                </li>
              </ul>

              {/* Sample Scorecard Static Preview */}
              <div className="mb-4 p-3.5 rounded-lg border border-border bg-bg/50 space-y-2.5">
                <div className="flex items-center justify-between text-[11px] font-mono uppercase tracking-[0.06em]">
                  <span className="text-text-muted">Scorecard Breakdown</span>
                  <span className="text-[10px] text-text-muted/60 lowercase tracking-normal">(sample data)</span>
                </div>
                <div className="space-y-2 font-mono text-[12px]">
                  <div>
                    <div className="flex justify-between text-text mb-1">
                      <span className="text-[11px]">Project defense</span>
                      <span className="text-[11px] text-accent">72/100</span>
                    </div>
                    <div className="h-1 w-full bg-surface rounded-full overflow-hidden border border-border/40">
                      <div className="h-full bg-accent rounded-full" style={{ width: '72%' }} />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-text mb-1">
                      <span className="text-[11px]">Fundamentals</span>
                      <span className="text-[11px] text-accent">64/100</span>
                    </div>
                    <div className="h-1 w-full bg-surface rounded-full overflow-hidden border border-border/40">
                      <div className="h-full bg-accent/80 rounded-full" style={{ width: '64%' }} />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-auto pt-4">
              <button
                onClick={() => handleAction('interview')}
                className="w-full h-11 px-6 rounded-md bg-accent hover:opacity-90 text-accent-contrast font-sans text-[14px] font-medium flex items-center justify-center gap-2 transition-opacity"
              >
                <span>Enter AI Interview Room</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Restrained 3-Step Walkthrough Bar */}
        <div className="mt-12 p-8 rounded-[12px] border border-border bg-surface">
          <div className="flex items-center justify-between mb-6 pb-3 border-b border-border">
            <h3 className="font-serif text-[22px] text-text font-normal">
              Preparation Workflow
            </h3>
            <span className="text-[12px] font-mono text-text-muted uppercase tracking-[0.06em]">
              3 Steps
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="space-y-1.5">
              <span className="font-mono text-[12px] text-accent">01</span>
              <h4 className="text-[15px] font-medium text-text">Target Your Role</h4>
              <p className="text-[13px] text-text-muted leading-[1.6]">
                Select from top tech companies or paste any custom Job Description to generate topic profiles.
              </p>
            </div>

            <div className="space-y-1.5">
              <span className="font-mono text-[12px] text-accent">02</span>
              <h4 className="text-[15px] font-medium text-text">Simulate Coding Assessments</h4>
              <p className="text-[13px] text-text-muted leading-[1.6]">
                Practice high-frequency topics or sit a realistic 60-minute exam with Monaco test runner.
              </p>
            </div>

            <div className="space-y-1.5">
              <span className="font-mono text-[12px] text-accent">03</span>
              <h4 className="text-[15px] font-medium text-text">Defend in Technical Interview</h4>
              <p className="text-[13px] text-text-muted leading-[1.6]">
                Answer spoken prompts and defend resume implementations with structured rubrics.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
