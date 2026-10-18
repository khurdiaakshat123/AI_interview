import React, { useState } from 'react';
import { PastInterviewsModal } from '../components/PastInterviewsModal';

interface LandingPageProps {
  onNavigate: (tab: string, state?: any) => void;
  currentUser?: any;
  onOpenAuth?: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onNavigate, currentUser, onOpenAuth }) => {
  const [showPastInterviews, setShowPastInterviews] = useState(false);

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

  return (
    <div className="py-12 sm:py-16 md:py-20 px-4 sm:px-6 lg:px-8">
      <div className="max-w-[1100px] mx-auto">
        {/* Top Hero Section */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-14 items-start">
          {/* Left Hero Column */}
          <div className="lg:col-span-7">
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

          {/* Right Hero Column: Interactive Example Interview Card */}
          <div className="lg:col-span-5 flex justify-center lg:justify-end">
            <div className="bg-surface border border-border rounded-xl p-6 sm:p-7 shadow-[0_1px_3px_rgba(0,0,0,0.04)] w-full max-w-[480px]">
              {/* Card Header */}
              <div className="flex items-center justify-between text-xs mb-5 font-sans">
                <span className="font-semibold text-text text-[13px]">
                  Example: your support chatbot project
                </span>
                <span className="text-text-muted text-[12px]">
                  Follow-up 3 of 5
                </span>
              </div>

              {/* Dialogue Transcript */}
              <div className="space-y-4 font-sans">
                {/* Exchange 1 */}
                <div>
                  <div className="text-[12px] font-semibold text-accent mb-1">
                    Interviewer
                  </div>
                  <p className="text-[13.5px] leading-[1.55] text-text font-normal">
                    You stored embeddings in Postgres with pgvector. Why not a dedicated vector database?
                  </p>
                </div>

                {/* Exchange 2 */}
                <div>
                  <div className="text-[12px] font-medium text-text-muted mb-1">
                    You
                  </div>
                  <p className="text-[13.5px] leading-[1.55] text-text-muted font-normal">
                    The data was small and already in Postgres, so it was one less service to run.
                  </p>
                </div>

                {/* Exchange 3 */}
                <div>
                  <div className="text-[12px] font-semibold text-accent mb-1">
                    Interviewer
                  </div>
                  <p className="text-[13.5px] leading-[1.55] text-text font-normal">
                    At what corpus size does that stop being true, and what breaks first?
                  </p>
                </div>
              </div>

              {/* Subtle Divider */}
              <div className="border-t border-border mt-5 mb-4" />

              {/* Depth Level Indicator */}
              <div className="flex items-center gap-3 font-sans">
                <span className="text-[12px] text-text-muted font-normal">Depth</span>
                <div className="flex items-center gap-1.5">
                  <div className="w-5 h-[3px] rounded-full bg-accent" />
                  <div className="w-5 h-[3px] rounded-full bg-accent" />
                  <div className="w-5 h-[3px] rounded-full bg-accent" />
                  <div className="w-5 h-[3px] rounded-full bg-border" />
                  <div className="w-5 h-[3px] rounded-full bg-border" />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Horizontal Divider Across Page */}
        <div className="border-t border-border mt-16 sm:mt-20 mb-12 sm:mb-14" />

        {/* Bottom 3-Column Editorial Feature Links */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-10 md:gap-12">
          {/* Column 1: Past interviews (replaces duplicate mock interview link) */}
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

          {/* Column 3: Timed OA */}
          <div>
            <h2 className="font-serif text-[26px] text-text font-normal mb-3">
              Timed OA
            </h2>
            <p className="text-[14px] leading-[1.65] text-text-muted mb-5 font-sans">
              Sit a 60-minute online assessment in the code editor, with no hints, like the real round. Hidden test cases are checked when you submit.
            </p>
            <button
              onClick={() => handleAction('mock-oa')}
              className="text-[14px] font-medium text-text underline decoration-accent decoration-2 underline-offset-4 hover:opacity-80 transition-opacity text-left font-sans cursor-pointer"
            >
              Start a 60-minute OA
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
    </div>
  );
};
