import React, { useState } from 'react';
import { ArrowRight } from 'lucide-react';
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

            {/* Three Feature Rows: One clickable line per destination with muted description & right-aligned arrow */}
            <div className="space-y-3 pt-6 border-t border-border/70 font-sans">
              {/* Row 1: View past interviews */}
              <button
                type="button"
                onClick={handleOpenPastInterviews}
                className="w-full group flex items-center justify-between p-3.5 sm:px-4 sm:py-3 rounded-xl border border-border bg-surface hover:bg-surface-hover hover:border-accent/40 transition-all text-left cursor-pointer shadow-xs"
                title="View past interviews"
                aria-label="View past interviews"
              >
                <div className="space-y-0.5">
                  <div className="text-[14.5px] sm:text-[15px] font-medium text-text group-hover:text-accent transition-colors">
                    View past interviews
                  </div>
                  <p className="text-[12.5px] sm:text-[13px] text-text-muted">
                    Transcripts, probe depth, and feedback
                  </p>
                </div>
                <ArrowRight className="w-4 h-4 text-text-muted group-hover:text-accent group-hover:translate-x-1 transition-all shrink-0 ml-4" />
              </button>

              {/* Row 2: Paste a job description */}
              <button
                type="button"
                onClick={() => handleAction('jd-intake')}
                className="w-full group flex items-center justify-between p-3.5 sm:px-4 sm:py-3 rounded-xl border border-border bg-surface hover:bg-surface-hover hover:border-accent/40 transition-all text-left cursor-pointer shadow-xs"
                title="Paste a job description"
                aria-label="Paste a job description"
              >
                <div className="space-y-0.5">
                  <div className="text-[14.5px] sm:text-[15px] font-medium text-text group-hover:text-accent transition-colors">
                    Paste a job description
                  </div>
                  <p className="text-[12.5px] sm:text-[13px] text-text-muted">
                    Practice questions, ranked topics, and hints
                  </p>
                </div>
                <ArrowRight className="w-4 h-4 text-text-muted group-hover:text-accent group-hover:translate-x-1 transition-all shrink-0 ml-4" />
              </button>

              {/* Row 3: Review assessments */}
              <button
                type="button"
                onClick={handleOpenPastOAReview}
                className="w-full group flex items-center justify-between p-3.5 sm:px-4 sm:py-3 rounded-xl border border-border bg-surface hover:bg-surface-hover hover:border-accent/40 transition-all text-left cursor-pointer shadow-xs"
                title="Review assessments"
                aria-label="Review assessments"
              >
                <div className="space-y-0.5">
                  <div className="text-[14.5px] sm:text-[15px] font-medium text-text group-hover:text-accent transition-colors">
                    Review assessments
                  </div>
                  <p className="text-[12.5px] sm:text-[13px] text-text-muted">
                    Scores, question breakdowns, and time analysis
                  </p>
                </div>
                <ArrowRight className="w-4 h-4 text-text-muted group-hover:text-accent group-hover:translate-x-1 transition-all shrink-0 ml-4" />
              </button>
            </div>
          </div>

          {/* Right Hero Column: Dynamic Moving Interactive Interview Preview */}
          <div className="lg:col-span-6 xl:col-span-7 flex justify-center lg:justify-end">
            <DynamicInterviewPreview />
          </div>
        </div>
      </div>

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
