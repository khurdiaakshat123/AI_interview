import React, { useState } from 'react';
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
    <div className="py-12 sm:py-16 md:py-20 px-4 sm:px-6 lg:px-8">
      <div className="max-w-[1240px] mx-auto">
        {/* Top Hero Section */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-12 items-center">
          {/* Left Hero Column */}
          <div className="lg:col-span-6 xl:col-span-5">
            <h1 className="font-serif text-[clamp(38px,4.6vw,56px)] leading-[1.08] tracking-[-0.015em] text-text font-normal mb-6 [text-wrap:balance]">
              Get questioned on your own projects before a real interviewer does.
            </h1>

            <p className="text-[16px] sm:text-[17px] leading-[1.65] text-text-muted max-w-[48ch] mb-8 font-sans">
              Upload your resume and a job description. The interviewer picks something you built, asks why, then keeps pushing until you run out of answers.
            </p>

            <div className="flex flex-wrap items-center gap-3.5">
              <button
                onClick={() => handleAction('interview')}
                className="h-11 px-5 rounded-md bg-[#18181A] text-[#FAFAFA] dark:bg-[#EDEDED] dark:text-[#0E0E10] text-[14px] font-medium hover:opacity-90 transition-opacity shadow-sm cursor-pointer"
              >
                Start an interview
              </button>

              <button
                onClick={() => handleAction('mock-oa')}
                className="h-11 px-5 rounded-md border border-border bg-transparent text-text hover:bg-surface-hover text-[14px] font-medium transition-colors cursor-pointer"
              >
                Practice a timed OA
              </button>
            </div>
          </div>

          {/* Right Hero Column: Dynamic Moving Interactive Interview Preview */}
          <div className="lg:col-span-6 xl:col-span-7 flex justify-center lg:justify-end">
            <DynamicInterviewPreview />
          </div>
        </div>

        {/* Horizontal Divider Across Page */}
        <div className="border-t border-border mt-16 sm:mt-20 mb-12 sm:mb-14" />

        {/* Bottom 3-Column Editorial Feature Links */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-10 md:gap-12">
          {/* Column 1: Past interviews */}
          <div>
            <h2 className="font-serif text-[26px] text-text font-normal mb-3">
              Past interviews
            </h2>
            <p className="text-[14px] leading-[1.65] text-text-muted mb-5 font-sans">
              Review your recorded interview sessions with the complete conversation transcript, follow-up probe depths, and evaluation feedback.
            </p>
            <button
              onClick={handleOpenPastInterviews}
              className="text-[14px] font-medium text-text underline decoration-accent decoration-2 underline-offset-4 hover:opacity-80 transition-opacity text-left font-sans cursor-pointer"
            >
              View past interviews
            </button>
          </div>

          {/* Column 2: Practice questions */}
          <div>
            <h2 className="font-serif text-[26px] text-text font-normal mb-3">
              Practice questions
            </h2>
            <p className="text-[14px] leading-[1.65] text-text-muted mb-5 font-sans">
              Paste a job description and get topics ranked by how much they matter. Work through coding questions on each, with hints when you get stuck.
            </p>
            <button
              onClick={() => handleAction('jd-intake')}
              className="text-[14px] font-medium text-text underline decoration-accent decoration-2 underline-offset-4 hover:opacity-80 transition-opacity text-left font-sans cursor-pointer"
            >
              Paste a job description
            </button>
          </div>

          {/* Column 3: Review Assessments */}
          <div>
            <h2 className="font-serif text-[26px] text-text font-normal mb-3">
              Review assessments
            </h2>
            <p className="text-[14px] leading-[1.65] text-text-muted mb-5 font-sans">
              Review your completed OA attempts with detailed performance breakdowns: time taken, overall score, questions solved correctly vs failed, and complete question reviews.
            </p>
            <button
              onClick={handleOpenPastOAReview}
              className="text-[14px] font-medium text-text underline decoration-accent decoration-2 underline-offset-4 hover:opacity-80 transition-opacity text-left font-sans cursor-pointer"
            >
              Review assessments
            </button>
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
