import React from 'react';
import { ArrowRight } from 'lucide-react';

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
    <div className="py-16 sm:py-20 px-4 sm:px-6">
      <div className="max-w-[1100px] mx-auto">
        {/* HERO */}
        <div className="mb-20">
          <p className="text-[11px] font-mono uppercase tracking-[0.1em] text-text-muted mb-5">
            Technical Interview Preparation
          </p>
          <h1
            className="text-[clamp(36px,4.5vw,52px)] leading-[1.1] tracking-[-0.02em] text-text font-semibold max-w-[18ch] mb-7"
            style={{ fontFamily: 'var(--font-sans)' }}
          >
            Prepare for company OAs &amp; technical interviews
          </h1>
          <p
            className="text-[16px] leading-[1.7] text-text-muted max-w-[52ch] mb-10"
            style={{ fontFamily: 'var(--font-sans)' }}
          >
            Resume-grounded AI interviews. Timed coding assessments. Adaptive depth up to five follow-up levels. Built for engineers targeting top-tier roles.
          </p>
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => handleAction('interview')}
              className="h-11 px-6 rounded-md bg-accent text-accent-contrast text-[14px] font-medium flex items-center gap-2 hover:opacity-90 transition-opacity"
              style={{ fontFamily: 'var(--font-sans)' }}
            >
              Enter AI Interview Room
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => handleAction('mock-oa')}
              className="h-11 px-6 rounded-md border border-border bg-transparent text-text text-[14px] font-medium flex items-center gap-2 hover:bg-surface-hover transition-colors"
              style={{ fontFamily: 'var(--font-sans)' }}
            >
              Timed Assessment (OA)
              <ArrowRight className="w-4 h-4 text-text-muted" />
            </button>
          </div>
        </div>
        {/* FEATURE COLUMNS */}
        <div className="border-t border-border pt-12 grid grid-cols-1 md:grid-cols-2 gap-12 md:gap-16">
          {/* Column 1: Mock Interview */}
          <div>
            <p className="text-[11px] font-mono uppercase tracking-[0.1em] text-text-muted mb-5">
              Mock Interview
            </p>
            <h2
              className="text-[18px] font-semibold text-text mb-3"
              style={{ fontFamily: 'var(--font-sans)' }}
            >
              AI-powered 1-on-1 technical interview
            </h2>
            <p
              className="text-[14px] leading-[1.7] text-text-muted mb-6"
              style={{ fontFamily: 'var(--font-sans)' }}
            >
              Questions come from your own resume projects, with follow-ups up to five levels deep. You receive two scores: project defense and CS fundamentals.
            </p>
            <ul className="space-y-2 text-[14px] text-text-muted mb-8" style={{ fontFamily: 'var(--font-sans)' }}>
              <li className="flex items-start gap-2.5">
                <span className="text-text-muted select-none font-mono mt-0.5 shrink-0">—</span>
                <span>Probes architecture choices and production trade-offs</span>
              </li>
              <li className="flex items-start gap-2.5">
                <span className="text-text-muted select-none font-mono mt-0.5 shrink-0">—</span>
                <span>OS internals, distributed locks, DB transactions, caching</span>
              </li>
              <li className="flex items-start gap-2.5">
                <span className="text-text-muted select-none font-mono mt-0.5 shrink-0">—</span>
                <span>Adaptive depth — evaluates and probes levels 1 through 5</span>
              </li>
              <li className="flex items-start gap-2.5">
                <span className="text-text-muted select-none font-mono mt-0.5 shrink-0">—</span>
                <span>Dual-dimensional scorecard on completion</span>
              </li>
            </ul>
            <button
              onClick={() => handleAction('interview')}
              className="text-[13px] font-medium text-accent hover:underline underline-offset-4 flex items-center gap-1.5 transition-colors"
              style={{ fontFamily: 'var(--font-sans)' }}
            >
              Start an interview <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
          {/* Column 2: Timed Assessments + Skill Practice */}
          <div>
            <p className="text-[11px] font-mono uppercase tracking-[0.1em] text-text-muted mb-5">
              Coding Assessments
            </p>
            <h2
              className="text-[18px] font-semibold text-text mb-3"
              style={{ fontFamily: 'var(--font-sans)' }}
            >
              Timed OAs &amp; targeted skill practice
            </h2>
            <p
              className="text-[14px] leading-[1.7] text-text-muted mb-6"
              style={{ fontFamily: 'var(--font-sans)' }}
            >
              Paste a job description, get topics ranked by weight, practice with hints, then sit a 60-minute timed OA with Monaco editor and hidden test cases.
            </p>
            <ul className="space-y-2 text-[14px] text-text-muted mb-8" style={{ fontFamily: 'var(--font-sans)' }}>
              <li className="flex items-start gap-2.5">
                <span className="text-text-muted select-none font-mono mt-0.5 shrink-0">—</span>
                <span>Extracts core subjects with prioritized importance weights</span>
              </li>
              <li className="flex items-start gap-2.5">
                <span className="text-text-muted select-none font-mono mt-0.5 shrink-0">—</span>
                <span>Personalized hints, architectural approaches, code solutions</span>
              </li>
              <li className="flex items-start gap-2.5">
                <span className="text-text-muted select-none font-mono mt-0.5 shrink-0">—</span>
                <span>60-minute exam simulation matching real 7-day hiring cycles</span>
              </li>
              <li className="flex items-start gap-2.5">
                <span className="text-text-muted select-none font-mono mt-0.5 shrink-0">—</span>
                <span>Monaco editor with hidden boundary and performance test cases</span>
              </li>
            </ul>
            <div className="flex flex-wrap gap-6">
              <button
                onClick={() => handleAction('practice')}
                className="text-[13px] font-medium text-accent hover:underline underline-offset-4 flex items-center gap-1.5 transition-colors"
                style={{ fontFamily: 'var(--font-sans)' }}
              >
                Skill Practice <ArrowRight className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => handleAction('mock-oa')}
                className="text-[13px] font-medium text-accent hover:underline underline-offset-4 flex items-center gap-1.5 transition-colors"
                style={{ fontFamily: 'var(--font-sans)' }}
              >
                Timed Assessment <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
