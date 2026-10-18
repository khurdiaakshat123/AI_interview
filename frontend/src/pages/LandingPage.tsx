import React, { useState, useEffect } from 'react';
import { Info, ArrowRight, X } from 'lucide-react';
import { PastInterviewsModal } from '../components/PastInterviewsModal';
import { PastOAReviewModal } from '../components/PastOAReviewModal';
import { DynamicInterviewPreview } from '../components/DynamicInterviewPreview';

interface LandingPageProps {
  onNavigate: (tab: string, state?: any) => void;
  currentUser?: any;
  onOpenAuth?: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onNavigate, currentUser, onOpenAuth }) => {
  const [showPastInterviews, setShowPastInterviews] = useState(false);
  const [showPastOAReview, setShowPastOAReview] = useState(false);
  const [infoPopup, setInfoPopup] = useState<'interviews' | 'practice' | 'assessments' | null>(null);

  // Close info popup on Escape key
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') setInfoPopup(null);
    }
    if (infoPopup) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [infoPopup]);

  const handleAction = (tab: string) => {
    if (!currentUser && onOpenAuth) {
      onOpenAuth();
      return;
    }
    onNavigate(tab);
  };

  const handleOpenPastInterviews = () => {
    if (!currentUser && onOpenAuth) {
      onOpenAuth();
      return;
    }
    setShowPastInterviews(true);
  };

  const handleOpenPastOAReview = () => {
    if (!currentUser && onOpenAuth) {
      onOpenAuth();
      return;
    }
    setShowPastOAReview(true);
  };

  const POPUP_DETAILS: Record<string, { title: string; desc: string; actionLabel: string; onAction: () => void }> = {
    interviews: {
      title: 'Past interviews',
      desc: 'Review your recorded interview sessions with the complete conversation transcript, follow-up probe depths, and evaluation feedback.',
      actionLabel: 'View past interviews',
      onAction: () => {
        setInfoPopup(null);
        handleOpenPastInterviews();
      }
    },
    practice: {
      title: 'Practice questions',
      desc: 'Paste a job description and get topics ranked by how much they matter. Work through coding questions on each, with hints when you get stuck.',
      actionLabel: 'Paste a job description',
      onAction: () => {
        setInfoPopup(null);
        handleAction('jd-intake');
      }
    },
    assessments: {
      title: 'Review assessments',
      desc: 'Review your completed OA attempts with detailed performance breakdowns: time taken, overall score, questions solved correctly vs failed, and complete question reviews.',
      actionLabel: 'Review assessments',
      onAction: () => {
        setInfoPopup(null);
        handleOpenPastOAReview();
      }
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex flex-col justify-start lg:justify-center px-4 sm:px-6 lg:px-8 pt-4 pb-6 sm:pt-6 sm:pb-8 lg:py-8 overflow-hidden">
      <div className="max-w-[1240px] w-full mx-auto">
        {/* Top Hero Section */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-start">
          {/* Left Hero Column */}
          <div className="lg:col-span-6 xl:col-span-5 flex flex-col pt-1 lg:pt-3">
            {/* Headline: Shifted upwards with strong editorial presence */}
            <h1 className="font-serif text-[clamp(28px,3.1vw,44px)] leading-[1.08] tracking-[-0.015em] text-text font-normal mb-4 [text-wrap:balance]">
              Get questioned on your own projects before a real interviewer does.
            </h1>

            {/* Subtext */}
            <p className="text-[14.5px] sm:text-[15.5px] leading-[1.62] text-text-muted max-w-[48ch] mb-6 font-sans">
              Upload your resume and a job description. The interviewer picks something you built, asks why, then keeps pushing until you run out of answers.
            </p>

            {/* Primary Action Buttons: Made bigger and prominent */}
            <div className="flex flex-wrap items-center gap-3.5 mb-7">
              <button
                onClick={() => handleAction('interview')}
                className="h-12 px-6 rounded-lg bg-[var(--btn-primary-bg)] text-[var(--btn-primary-text)] hover:opacity-90 text-[15px] font-medium transition-all shadow-sm cursor-pointer select-none"
              >
                Start an interview
              </button>

              <button
                onClick={() => handleAction('mock-oa')}
                className="h-12 px-6 rounded-lg border border-border bg-transparent text-text hover:bg-surface-hover hover:border-border-focus text-[15px] font-medium transition-colors cursor-pointer select-none"
              >
                Practice a timed OA
              </button>
            </div>

            {/* Three Feature Rows in Vertical Order Below Buttons: Bigger boxes & spacious alignment */}
            <div className="space-y-4 pt-6 border-t border-border/70 font-sans">
              {/* Row 1: Past interviews */}
              <div className="flex flex-wrap items-center gap-4">
                <button
                  type="button"
                  onClick={() => setInfoPopup('interviews')}
                  className="inline-flex items-center gap-2.5 h-12 px-5 sm:px-6 rounded-xl border border-border bg-surface hover:bg-surface-hover hover:border-accent/40 text-text text-[14.5px] font-medium transition-all cursor-pointer group shadow-xs"
                  title="Click to view details about Past Interviews"
                >
                  <span>Past interviews</span>
                  <Info className="w-4 h-4 text-accent/80 group-hover:text-accent transition-colors" />
                </button>

                <button
                  type="button"
                  onClick={handleOpenPastInterviews}
                  className="h-12 px-3 text-[14.5px] font-medium text-text hover:text-accent underline decoration-accent decoration-2 underline-offset-4 hover:opacity-90 transition-all cursor-pointer inline-flex items-center gap-1.5"
                  title="View past interviews"
                  aria-label="View past interviews"
                >
                  <span>View</span>
                  <ArrowRight className="w-4 h-4 text-accent" />
                </button>
              </div>

              {/* Row 2: Practice questions */}
              <div className="flex flex-wrap items-center gap-4">
                <button
                  type="button"
                  onClick={() => setInfoPopup('practice')}
                  className="inline-flex items-center gap-2.5 h-12 px-5 sm:px-6 rounded-xl border border-border bg-surface hover:bg-surface-hover hover:border-accent/40 text-text text-[14.5px] font-medium transition-all cursor-pointer group shadow-xs"
                  title="Click to view details about Practice Questions"
                >
                  <span>Practice questions</span>
                  <Info className="w-4 h-4 text-accent/80 group-hover:text-accent transition-colors" />
                </button>

                <button
                  type="button"
                  onClick={() => handleAction('jd-intake')}
                  className="h-12 px-3 text-[14.5px] font-medium text-text hover:text-accent underline decoration-accent decoration-2 underline-offset-4 hover:opacity-90 transition-all cursor-pointer inline-flex items-center gap-1.5"
                  title="View practice questions"
                  aria-label="View practice questions"
                >
                  <span>View</span>
                  <ArrowRight className="w-4 h-4 text-accent" />
                </button>
              </div>

              {/* Row 3: Review assessments */}
              <div className="flex flex-wrap items-center gap-4">
                <button
                  type="button"
                  onClick={() => setInfoPopup('assessments')}
                  className="inline-flex items-center gap-2.5 h-12 px-5 sm:px-6 rounded-xl border border-border bg-surface hover:bg-surface-hover hover:border-accent/40 text-text text-[14.5px] font-medium transition-all cursor-pointer group shadow-xs"
                  title="Click to view details about Review Assessments"
                >
                  <span>Review assessments</span>
                  <Info className="w-4 h-4 text-accent/80 group-hover:text-accent transition-colors" />
                </button>

                <button
                  type="button"
                  onClick={handleOpenPastOAReview}
                  className="h-12 px-3 text-[14.5px] font-medium text-text hover:text-accent underline decoration-accent decoration-2 underline-offset-4 hover:opacity-90 transition-all cursor-pointer inline-flex items-center gap-1.5"
                  title="View review assessments"
                  aria-label="View review assessments"
                >
                  <span>View</span>
                  <ArrowRight className="w-4 h-4 text-accent" />
                </button>
              </div>
            </div>
          </div>

          {/* Right Hero Column: Dynamic Moving Interactive Interview Preview */}
          <div className="lg:col-span-6 xl:col-span-7 flex justify-center lg:justify-end">
            <DynamicInterviewPreview />
          </div>
        </div>
      </div>

      {/* Feature Details Popups (for Past Interviews, Practice Questions, Review Assessments) */}
      {infoPopup && POPUP_DETAILS[infoPopup] && (
        <div 
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 animate-fadeIn"
          onClick={() => setInfoPopup(null)}
        >
          <div 
            className="bg-surface border border-border rounded-2xl p-7 sm:p-8 max-w-lg w-full shadow-2xl relative"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Close Button */}
            <button
              type="button"
              onClick={() => setInfoPopup(null)}
              className="absolute top-4 right-4 p-2 rounded-lg text-text-muted hover:text-text hover:bg-bg transition-colors cursor-pointer"
              aria-label="Close popup"
            >
              <X className="w-4 h-4" />
            </button>

            <h3 className="font-serif text-[24px] sm:text-[26px] text-text font-normal mb-3">
              {POPUP_DETAILS[infoPopup].title}
            </h3>

            <p className="text-[14.5px] leading-[1.65] text-text-muted mb-6 font-sans">
              {POPUP_DETAILS[infoPopup].desc}
            </p>

            <div className="flex items-center justify-end gap-3 font-sans">
              <button
                type="button"
                onClick={() => setInfoPopup(null)}
                className="h-10 px-4.5 rounded-lg border border-border bg-transparent text-text hover:bg-surface-hover text-[14px] font-medium transition-colors cursor-pointer"
              >
                Close
              </button>
              <button
                type="button"
                onClick={POPUP_DETAILS[infoPopup].onAction}
                className="h-10 px-5 rounded-lg bg-accent text-accent-contrast hover:opacity-90 text-[14px] font-medium transition-opacity cursor-pointer inline-flex items-center gap-1.5"
              >
                <span>{POPUP_DETAILS[infoPopup].actionLabel}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Past Interviews & Full Conversation Transcript Viewer Modal */}
      <PastInterviewsModal
        isOpen={showPastInterviews}
        onClose={() => setShowPastInterviews(false)}
        onNavigate={onNavigate}
      />

      {/* Review Past OA Assessments Performance & Questions Modal */}
      <PastOAReviewModal
        isOpen={showPastOAReview}
        onClose={() => setShowPastOAReview(false)}
        onNavigate={onNavigate}
      />
    </div>
  );
};
