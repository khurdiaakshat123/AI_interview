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
    badge: 'Veracity Solutions · Azure DevOps',
    timestamp: '10:45 PM',
    text: 'Welcome! Great to meet you. At Veracity Solutions, you reduced deployment times by 40% with Azure DevOps. How did you structure your pipeline caching to achieve that?',
    depth: 1
  },
  {
    id: 'turn-2',
    sender: 'CANDIDATE',
    speakerLabel: 'You',
    timestamp: '10:45 PM',
    text: 'We used ACR layer caching with parallel build stages across ephemeral agents, backed by automated canary validation gates.',
    depth: 2
  },
  {
    id: 'turn-3',
    sender: 'INTERVIEWER',
    speakerLabel: 'AI Technical Interviewer',
    badge: 'Reliability & Canary Gates',
    timestamp: '10:46 PM',
    text: 'If a canary fails under live traffic, how do you handle zero-downtime rollbacks with database schema changes?',
    evalPrev: {
      evidence: '88% Evidence',
      points: '+4.4 / 5.0 pts'
    },
    depth: 3
  },
  {
    id: 'turn-4',
    sender: 'CANDIDATE',
    speakerLabel: 'You',
    timestamp: '10:46 PM',
    text: 'We enforce expand-and-contract migrations. The API supports dual schemas, traffic reverts via Azure Front Door, and old columns drop only after validation.',
    depth: 4
  },
  {
    id: 'turn-5',
    sender: 'INTERVIEWER',
    speakerLabel: 'AI Technical Interviewer',
    badge: 'Telemetry & Gate Automation',
    timestamp: '10:47 PM',
    text: 'Solid strategy. How do you configure Application Insights alerts to trigger that Front Door rollback automatically before error spikes reach users?',
    evalPrev: {
      evidence: '94% Evidence',
      points: '+4.8 / 5.0 pts'
    },
    depth: 5
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

  // Main animation / dynamic sequence controller (3 questions + 2 answers = 5 depths)
  useEffect(() => {
    if (!isPlaying) return;

    let timer: ReturnType<typeof setTimeout>;

    if (step === 0) {
      // Start with interviewer asking initial warm question
      timer = setTimeout(() => {
        setStep(1);
      }, 500);
    } else if (step === 1) {
      // Candidate types answer 1
      timer = setTimeout(() => {
        setTypingSender('CANDIDATE');
        setIsTyping(true);
        timer = setTimeout(() => {
          setIsTyping(false);
          setStep(2);
        }, 1200);
      }, 1400);
    } else if (step === 2) {
      // Interviewer evaluates and asks follow-up question 2
      timer = setTimeout(() => {
        setTypingSender('INTERVIEWER');
        setIsTyping(true);
        timer = setTimeout(() => {
          setIsTyping(false);
          setStep(3);
        }, 1300);
      }, 1400);
    } else if (step === 3) {
      // Candidate types answer 2
      timer = setTimeout(() => {
        setTypingSender('CANDIDATE');
        setIsTyping(true);
        timer = setTimeout(() => {
          setIsTyping(false);
          setStep(4);
        }, 1200);
      }, 1400);
    } else if (step === 4) {
      // Interviewer evaluates and asks follow-up question 3 (depth 5)
      timer = setTimeout(() => {
        setTypingSender('INTERVIEWER');
        setIsTyping(true);
        timer = setTimeout(() => {
          setIsTyping(false);
          setStep(5);
        }, 1300);
      }, 1400);
    } else if (step >= PREVIEW_SCRIPT.length) {
      // Hold complete 5-depth conversation for 6.5 seconds, then smoothly loop
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
    <div className="bg-surface border border-border rounded-xl shadow-[0_2px_8px_rgba(0,0,0,0.06)] w-full max-w-[620px] flex flex-col overflow-hidden transition-all duration-300">
      {/* Dynamic Simulated Window Header */}
      <div className="px-4 sm:px-5 py-3 border-b border-border bg-bg/50 flex items-center justify-between gap-3 select-none">
        <div className="flex items-center gap-2 sm:gap-2.5">
          {/* Subtle OS window dots */}
          <div className="flex items-center gap-1.5 mr-1">
            <span className="w-2.5 h-2.5 rounded-full bg-border" />
            <span className="w-2.5 h-2.5 rounded-full bg-border" />
            <span className="w-2.5 h-2.5 rounded-full bg-border" />
          </div>

          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-surface border border-border text-[10px] sm:text-[11px] font-mono text-text-muted">
            <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
            <span className="font-medium text-text">Live Technical Probe</span>
          </div>
        </div>

        <div className="flex items-center gap-2.5 sm:gap-3">
          <span className="text-[10px] sm:text-[11px] font-mono text-text-muted">
            Depth {currentDepth} of 5
          </span>

          <div className="flex items-center gap-1 border-l border-border pl-2 sm:pl-2.5">
            <button
              type="button"
              onClick={handleTogglePlay}
              className="p-1 rounded-md text-text-muted hover:text-text hover:bg-surface transition-colors cursor-pointer"
              title={isPlaying ? "Pause simulation" : "Play simulation"}
              aria-label={isPlaying ? "Pause simulation" : "Play simulation"}
            >
              {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            </button>
            <button
              type="button"
              onClick={handleRestart}
              className="p-1 rounded-md text-text-muted hover:text-text hover:bg-surface transition-colors cursor-pointer"
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
        className="p-4 sm:p-5 h-[430px] sm:h-[460px] xl:h-[490px] overflow-y-auto space-y-3.5 font-sans scroll-smooth"
      >
        {PREVIEW_SCRIPT.slice(0, step).map((turn) => {
          const isInterviewer = turn.sender === 'INTERVIEWER';

          return (
            <div
              key={turn.id}
              className={`flex items-start gap-2.5 sm:gap-3 animate-fadeIn ${
                isInterviewer ? 'justify-start' : 'justify-end'
              }`}
            >
              {/* Interviewer Avatar (Left) */}
              {isInterviewer && (
                <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-bg border border-border flex items-center justify-center shrink-0 mt-0.5 text-accent shadow-xs">
                  <Bot className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                </div>
              )}

              {/* Message Bubble + Header */}
              <div className={`max-w-[88%] space-y-1 ${isInterviewer ? 'items-start' : 'items-end'}`}>
                {/* Header row with speaker info & timestamp */}
                <div 
                  className={`flex items-center gap-1.5 sm:gap-2 text-[10.5px] sm:text-[11px] text-text-muted px-1 font-mono ${
                    isInterviewer ? 'justify-start' : 'justify-end'
                  }`}
                >
                  {isInterviewer ? (
                    <>
                      <span className="font-medium text-text">
                        {turn.speakerLabel}
                      </span>
                      {turn.badge && (
                        <span className="text-[9.5px] sm:text-[10px] px-1.5 py-0.5 rounded bg-bg border border-border text-text-muted truncate max-w-[150px] sm:max-w-none">
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

                {/* Speech Bubble: Decreased font size for crisp, compact reading */}
                <div
                  className={`px-3.5 py-2.5 sm:px-4 sm:py-3 rounded-xl sm:rounded-2xl text-[12.5px] sm:text-[13px] leading-[1.5] transition-colors ${
                    isInterviewer
                      ? 'bg-bg/80 border border-border text-text rounded-tl-xs shadow-xs'
                      : 'bg-surface-hover border border-accent/40 text-text rounded-tr-xs shadow-xs'
                  }`}
                >
                  <p className="font-normal">{turn.text}</p>
                </div>

                {/* Real-time Turn Evaluation Badge */}
                {turn.evalPrev && (
                  <div className="px-2.5 py-1.5 sm:px-3 sm:py-2 rounded-lg bg-bg border border-border text-[10px] sm:text-[10.5px] text-text-muted flex items-center justify-between gap-2.5 mt-1 font-mono">
                    <div className="flex items-center gap-1.5">
                      <span>Evaluated:</span>
                      <span className="text-text font-medium">{turn.evalPrev.evidence}</span>
                    </div>
                    <span className="text-success font-medium">{turn.evalPrev.points}</span>
                  </div>
                )}
              </div>

              {/* Candidate Avatar (Right) */}
              {!isInterviewer && (
                <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-bg border border-border flex items-center justify-center shrink-0 mt-0.5 text-text-muted shadow-xs">
                  <User className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
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
                <span className="text-[10.5px] sm:text-[11px] font-mono">You are replying...</span>
                <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-surface border border-accent/30 shadow-xs">
                  <span className="w-1.5 h-1.5 rounded-full bg-accent/80 animate-bounce [animation-delay:0ms]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-accent/80 animate-bounce [animation-delay:150ms]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-accent/80 animate-bounce [animation-delay:300ms]" />
                </div>
                <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-bg border border-border flex items-center justify-center text-text-muted">
                  <User className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2.5 text-[10.5px] sm:text-[11px] font-mono text-text-muted p-0.5">
                <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-bg border border-border flex items-center justify-center text-accent shrink-0">
                  <Bot className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3.5 h-3.5 rounded-full border-2 border-accent border-t-transparent animate-spin" />
                  <span>Evaluating technical depth & adapting probe...</span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer: Dynamic Depth Meter & Step Progress (1 to 5) */}
      <div className="px-4 sm:px-5 py-3 border-t border-border bg-bg/40 flex items-center justify-between font-sans">
        <div className="flex items-center gap-3">
          <span className="text-text-muted font-normal text-[11px] sm:text-[11.5px]">Depth</span>
          <div className="flex items-center gap-1.5">
            {[1, 2, 3, 4, 5].map((level) => {
              const isFilled = level <= currentDepth;
              return (
                <div
                  key={level}
                  className={`w-6 h-[3.5px] rounded-full transition-all duration-300 ${
                    isFilled ? 'bg-accent' : 'bg-border'
                  }`}
                />
              );
            })}
          </div>
        </div>

        <div className="flex items-center gap-1.5 text-[10.5px] sm:text-[11px] text-text-muted font-mono">
          <span>Target:</span>
          <span className="text-text font-medium">Veracity Solutions · Azure</span>
        </div>
      </div>
    </div>
  );
};
