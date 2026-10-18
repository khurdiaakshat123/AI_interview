import React, { useState, useEffect, useRef } from 'react';
import { Bot, User, Play, Pause, RotateCcw } from 'lucide-react';

interface PreviewTurn {
  id: string;
  sender: 'INTERVIEWER' | 'CANDIDATE';
  speakerLabel: string;
  badge?: string;
  timestamp: string;
  text: string;
  evalPrev?: {
    evidence: string;
    points: string;
  };
  depth: number;
}

const PREVIEW_SCRIPT: PreviewTurn[] = [
  {
    id: 'turn-1',
    sender: 'INTERVIEWER',
    speakerLabel: 'AI Technical Interviewer',
    badge: 'Backend Engineer (Support Chatbot)',
    timestamp: '10:45 PM',
    text: 'You stored embeddings in Postgres with pgvector. Why not a dedicated vector database?',
    depth: 1
  },
  {
    id: 'turn-2',
    sender: 'CANDIDATE',
    speakerLabel: 'You',
    timestamp: '10:45 PM',
    text: 'The data was small and already in Postgres, so it was one less service to run.',
    depth: 2
  },
  {
    id: 'turn-3',
    sender: 'INTERVIEWER',
    speakerLabel: 'AI Technical Interviewer',
    badge: 'Architecture & Scale',
    timestamp: '10:46 PM',
    text: 'At what corpus size does that stop being true, and what breaks first?',
    evalPrev: {
      evidence: '84% Evidence',
      points: '+4.2 / 5.0 pts'
    },
    depth: 3
  },
  {
    id: 'turn-4',
    sender: 'CANDIDATE',
    speakerLabel: 'You',
    timestamp: '10:46 PM',
    text: 'Around ~500k 1536-dim vectors. Buffer cache saturation and VACUUM overhead degrade HNSW build latency before query latency spikes.',
    depth: 4
  }
];

export const DynamicInterviewPreview: React.FC = () => {
  // Step indicates how many messages are revealed (0 to PREVIEW_SCRIPT.length)
  const [step, setStep] = useState<number>(1);
  const [isTyping, setIsTyping] = useState<boolean>(false);
  const [typingSender, setTypingSender] = useState<'INTERVIEWER' | 'CANDIDATE'>('CANDIDATE');
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll inside preview container on new messages or typing
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [step, isTyping]);

  // Main animation / dynamic sequence controller
  useEffect(() => {
    if (!isPlaying) return;

    let timer: ReturnType<typeof setTimeout>;

    if (step === 0) {
      // Start with interviewer asking initial question
      timer = setTimeout(() => {
        setStep(1);
      }, 600);
    } else if (step === 1) {
      // Pause, then candidate starts typing
      timer = setTimeout(() => {
        setTypingSender('CANDIDATE');
        setIsTyping(true);
        timer = setTimeout(() => {
          setIsTyping(false);
          setStep(2);
        }, 1300);
      }, 1400);
    } else if (step === 2) {
      // Pause, then interviewer analyzes & starts formulating follow up
      timer = setTimeout(() => {
        setTypingSender('INTERVIEWER');
        setIsTyping(true);
        timer = setTimeout(() => {
          setIsTyping(false);
          setStep(3);
        }, 1400);
      }, 1500);
    } else if (step === 3) {
      // Pause, then candidate provides deeper follow-up answer
      timer = setTimeout(() => {
        setTypingSender('CANDIDATE');
        setIsTyping(true);
        timer = setTimeout(() => {
          setIsTyping(false);
          setStep(4);
        }, 1400);
      }, 1600);
    } else if (step >= PREVIEW_SCRIPT.length) {
      // Hold complete conversation for 6 seconds, then smoothly loop
      timer = setTimeout(() => {
        setStep(1);
      }, 6500);
    }

    return () => clearTimeout(timer);
  }, [step, isPlaying]);

  const handleRestart = () => {
    setIsTyping(false);
    setStep(1);
    setIsPlaying(true);
  };

  const handleTogglePlay = () => {
    setIsPlaying(prev => !prev);
  };

  // Determine current depth level (1 to 5)
  const currentDepth = step > 0 ? PREVIEW_SCRIPT[Math.min(step - 1, PREVIEW_SCRIPT.length - 1)].depth : 1;

  return (
    <div className="bg-surface border border-border rounded-xl shadow-[0_2px_8px_rgba(0,0,0,0.06)] w-full max-w-[600px] flex flex-col overflow-hidden transition-all duration-300">
      {/* Dynamic Simulated Window Header */}
      <div className="px-4 sm:px-5 py-3 border-b border-border bg-bg/50 flex items-center justify-between gap-3 select-none">
        <div className="flex items-center gap-2.5">
          {/* Subtle OS window dots */}
          <div className="flex items-center gap-1.5 mr-1">
            <span className="w-2.5 h-2.5 rounded-full bg-border" />
            <span className="w-2.5 h-2.5 rounded-full bg-border" />
            <span className="w-2.5 h-2.5 rounded-full bg-border" />
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-surface border border-border text-[11px] sm:text-[11.5px] font-mono text-text-muted">
            <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
            <span className="font-medium text-text">Live Technical Probe</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-[11px] sm:text-[11.5px] font-mono text-text-muted">
            Follow-up {currentDepth} of 5
          </span>

          <div className="flex items-center gap-1 border-l border-border pl-2.5">
            <button
              type="button"
              onClick={handleTogglePlay}
              className="p-1.5 rounded-md text-text-muted hover:text-text hover:bg-surface transition-colors cursor-pointer"
              title={isPlaying ? "Pause simulation" : "Play simulation"}
              aria-label={isPlaying ? "Pause simulation" : "Play simulation"}
            >
              {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            </button>
            <button
              type="button"
              onClick={handleRestart}
              className="p-1.5 rounded-md text-text-muted hover:text-text hover:bg-surface transition-colors cursor-pointer"
              title="Restart preview"
              aria-label="Restart preview"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Dynamic Chat Messages Area with Real Interview Spacing */}
      <div 
        ref={scrollRef}
        className="p-4 sm:p-5 h-[360px] sm:h-[390px] xl:h-[410px] overflow-y-auto space-y-4 font-sans scroll-smooth"
      >
        {PREVIEW_SCRIPT.slice(0, step).map((turn) => {
          const isInterviewer = turn.sender === 'INTERVIEWER';

          return (
            <div
              key={turn.id}
              className={`flex items-start gap-3 animate-fadeIn ${
                isInterviewer ? 'justify-start' : 'justify-end'
              }`}
            >
              {/* Interviewer Avatar (Left) */}
              {isInterviewer && (
                <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-bg border border-border flex items-center justify-center shrink-0 mt-0.5 text-accent shadow-xs">
                  <Bot className="w-4.5 h-4.5" />
                </div>
              )}

              {/* Message Bubble + Header */}
              <div className={`max-w-[86%] space-y-1.5 ${isInterviewer ? 'items-start' : 'items-end'}`}>
                {/* Header row with speaker info & timestamp */}
                <div 
                  className={`flex items-center gap-2 text-[11.5px] sm:text-[12px] text-text-muted px-1 font-mono ${
                    isInterviewer ? 'justify-start' : 'justify-end'
                  }`}
                >
                  {isInterviewer ? (
                    <>
                      <span className="font-medium text-text">
                        {turn.speakerLabel}
                      </span>
                      {turn.badge && (
                        <span className="text-[10.5px] px-2 py-0.5 rounded-md bg-bg border border-border text-text-muted truncate max-w-[160px] sm:max-w-none">
                          {turn.badge}
                        </span>
                      )}
                      <span>{turn.timestamp}</span>
                    </>
                  ) : (
                    <>
                      <span>{turn.timestamp}</span>
                      <span className="font-medium text-text">
                        {turn.speakerLabel}
                      </span>
                    </>
                  )}
                </div>

                {/* Speech Bubble */}
                <div
                  className={`p-4 sm:p-4.5 rounded-2xl text-[14px] sm:text-[14.5px] leading-[1.6] transition-colors ${
                    isInterviewer
                      ? 'bg-bg border border-border text-text rounded-tl-xs shadow-xs'
                      : 'bg-surface border border-accent/40 text-text rounded-tr-xs shadow-xs'
                  }`}
                >
                  <p className="font-normal">{turn.text}</p>
                </div>

                {/* Real-time Turn Evaluation Badge (when follow-up evaluates previous answer) */}
                {turn.evalPrev && (
                  <div className="p-2.5 sm:p-3 rounded-xl bg-bg border border-border text-[11.5px] sm:text-[12px] text-text-muted flex items-center justify-between gap-3 mt-1.5 font-mono">
                    <div className="flex items-center gap-2">
                      <span>Evaluated:</span>
                      <span className="text-text font-medium">{turn.evalPrev.evidence}</span>
                    </div>
                    <span className="text-success font-medium">{turn.evalPrev.points}</span>
                  </div>
                )}
              </div>

              {/* Candidate Avatar (Right) */}
              {!isInterviewer && (
                <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-bg border border-border flex items-center justify-center shrink-0 mt-0.5 text-text-muted shadow-xs">
                  <User className="w-4.5 h-4.5" />
                </div>
              )}
            </div>
          );
        })}

        {/* Live Typing & Evaluating Indicators */}
        {isTyping && (
          <div className="animate-fadeIn">
            {typingSender === 'CANDIDATE' ? (
              <div className="flex items-center justify-end gap-2.5 text-text-muted">
                <span className="text-[11.5px] font-mono">You are replying...</span>
                <div className="flex items-center gap-1.5 px-3 py-2 rounded-2xl bg-surface border border-accent/30 shadow-xs">
                  <span className="w-1.5 h-1.5 rounded-full bg-accent/80 animate-bounce [animation-delay:0ms]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-accent/80 animate-bounce [animation-delay:150ms]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-accent/80 animate-bounce [animation-delay:300ms]" />
                </div>
                <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-bg border border-border flex items-center justify-center text-text-muted">
                  <User className="w-4.5 h-4.5" />
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-3 text-[11.5px] font-mono text-text-muted p-1">
                <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-bg border border-border flex items-center justify-center text-accent shrink-0">
                  <Bot className="w-4.5 h-4.5" />
                </div>
                <div className="flex items-center gap-2.5">
                  <div className="w-4 h-4 rounded-full border-2 border-accent border-t-transparent animate-spin" />
                  <span>Interviewer evaluating technical depth & adapting probe...</span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer: Dynamic Depth Meter & Step Progress */}
      <div className="px-5 sm:px-6 py-3.5 border-t border-border bg-bg/40 flex items-center justify-between font-sans text-xs sm:text-[13px]">
        <div className="flex items-center gap-3.5">
          <span className="text-text-muted font-normal text-[12.5px]">Depth</span>
          <div className="flex items-center gap-1.5">
            {[1, 2, 3, 4, 5].map((level) => {
              const isFilled = level <= currentDepth;
              return (
                <div
                  key={level}
                  className={`w-7 h-[4px] rounded-full transition-all duration-300 ${
                    isFilled ? 'bg-accent' : 'bg-border'
                  }`}
                />
              );
            })}
          </div>
        </div>

        <div className="flex items-center gap-1.5 text-[11.5px] text-text-muted font-mono">
          <span>Project:</span>
          <span className="text-text font-medium">support chatbot</span>
        </div>
      </div>
    </div>
  );
};
