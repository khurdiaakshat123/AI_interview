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
    <div className="bg-surface border border-border rounded-xl shadow-[0_1px_3px_rgba(0,0,0,0.04)] w-full max-w-[500px] flex flex-col overflow-hidden transition-all duration-300">
      {/* Dynamic Simulated Window Header */}
      <div className="px-4 py-3 border-b border-border bg-bg/50 flex items-center justify-between gap-2 select-none">
        <div className="flex items-center gap-2">
          {/* Subtle OS window dots */}
          <div className="flex items-center gap-1.5 mr-1">
            <span className="w-2.5 h-2.5 rounded-full bg-border" />
            <span className="w-2.5 h-2.5 rounded-full bg-border" />
            <span className="w-2.5 h-2.5 rounded-full bg-border" />
          </div>

          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-surface border border-border text-[11px] font-mono text-text-muted">
            <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
            <span className="font-medium text-text">Live Technical Probe</span>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <span className="text-[11px] font-mono text-text-muted">
            Follow-up {currentDepth} of 5
          </span>

          <div className="flex items-center gap-1 border-l border-border pl-2">
            <button
              type="button"
              onClick={handleTogglePlay}
              className="p-1 rounded text-text-muted hover:text-text hover:bg-surface transition-colors cursor-pointer"
              title={isPlaying ? "Pause simulation" : "Play simulation"}
              aria-label={isPlaying ? "Pause simulation" : "Play simulation"}
            >
              {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            </button>
            <button
              type="button"
              onClick={handleRestart}
              className="p-1 rounded text-text-muted hover:text-text hover:bg-surface transition-colors cursor-pointer"
              title="Restart preview"
              aria-label="Restart preview"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Dynamic Chat Messages Area with Real Interview Spacing */}
      <div 
        ref={scrollRef}
        className="p-4 sm:p-5 h-[375px] overflow-y-auto space-y-4 font-sans scroll-smooth"
      >
        {PREVIEW_SCRIPT.slice(0, step).map((turn) => {
          const isInterviewer = turn.sender === 'INTERVIEWER';

          return (
            <div
              key={turn.id}
              className={`flex items-start gap-2.5 animate-fadeIn ${
                isInterviewer ? 'justify-start' : 'justify-end'
              }`}
            >
              {/* Interviewer Avatar (Left) */}
              {isInterviewer && (
                <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-bg border border-border flex items-center justify-center shrink-0 mt-0.5 text-accent">
                  <Bot className="w-4 h-4" />
                </div>
              )}

              {/* Message Bubble + Header */}
              <div className={`max-w-[85%] space-y-1.5 ${isInterviewer ? 'items-start' : 'items-end'}`}>
                {/* Header row with speaker info & timestamp */}
                <div 
                  className={`flex items-center gap-1.5 text-[11px] text-text-muted px-1 font-mono ${
                    isInterviewer ? 'justify-start' : 'justify-end'
                  }`}
                >
                  {isInterviewer ? (
                    <>
                      <span className="font-medium text-text">
                        {turn.speakerLabel}
                      </span>
                      {turn.badge && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-bg border border-border text-text-muted truncate max-w-[140px] sm:max-w-none">
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
                  className={`p-3.5 sm:p-4 rounded-xl text-[13px] sm:text-[13.5px] leading-relaxed transition-colors ${
                    isInterviewer
                      ? 'bg-bg border border-border text-text rounded-tl-sm shadow-sm'
                      : 'bg-surface border border-accent/40 text-text rounded-tr-sm shadow-sm'
                  }`}
                >
                  <p className="font-normal">{turn.text}</p>
                </div>

                {/* Real-time Turn Evaluation Badge (when follow-up evaluates previous answer) */}
                {turn.evalPrev && (
                  <div className="p-2 sm:p-2.5 rounded-lg bg-bg border border-border text-[11px] text-text-muted flex items-center justify-between gap-2 mt-1 font-mono">
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
                <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-bg border border-border flex items-center justify-center shrink-0 mt-0.5 text-text-muted">
                  <User className="w-4 h-4" />
                </div>
              )}
            </div>
          );
        })}

        {/* Live Typing & Evaluating Indicators */}
        {isTyping && (
          <div className="animate-fadeIn">
            {typingSender === 'CANDIDATE' ? (
              <div className="flex items-center justify-end gap-2 text-text-muted">
                <span className="text-[11px] font-mono">You are replying...</span>
                <div className="flex items-center gap-1 px-2.5 py-2 rounded-xl bg-surface border border-accent/30">
                  <span className="w-1.5 h-1.5 rounded-full bg-accent/80 animate-bounce [animation-delay:0ms]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-accent/80 animate-bounce [animation-delay:150ms]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-accent/80 animate-bounce [animation-delay:300ms]" />
                </div>
                <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-bg border border-border flex items-center justify-center text-text-muted">
                  <User className="w-4 h-4" />
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2.5 text-[11px] font-mono text-text-muted p-1">
                <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-bg border border-border flex items-center justify-center text-accent shrink-0">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3.5 h-3.5 rounded-full border-2 border-accent border-t-transparent animate-spin" />
                  <span>Interviewer evaluating technical depth & adapting probe...</span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer: Dynamic Depth Meter & Step Progress */}
      <div className="px-4 sm:px-5 py-3 border-t border-border bg-bg/40 flex items-center justify-between font-sans text-xs">
        <div className="flex items-center gap-3">
          <span className="text-text-muted font-normal text-[12px]">Depth</span>
          <div className="flex items-center gap-1.5">
            {[1, 2, 3, 4, 5].map((level) => {
              const isFilled = level <= currentDepth;
              return (
                <div
                  key={level}
                  className={`w-5 h-[3px] rounded-full transition-all duration-300 ${
                    isFilled ? 'bg-accent' : 'bg-border'
                  }`}
                />
              );
            })}
          </div>
        </div>

        <div className="flex items-center gap-1.5 text-[11px] text-text-muted font-mono">
          <span>Project:</span>
          <span className="text-text font-medium">support chatbot</span>
        </div>
      </div>
    </div>
  );
};
