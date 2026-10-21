import React, { useState, useEffect, useRef } from 'react';
import { Play, Pause, RotateCcw } from 'lucide-react';

interface LCTimerProps {
  questionId: string;
}

export const LCTimer: React.FC<LCTimerProps> = ({ questionId }) => {
  const [seconds, setSeconds] = useState<number>(0);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const intervalRef = useRef<any>(null);

  // Load saved timer state for this question
  useEffect(() => {
    try {
      const saved = localStorage.getItem(`intervyn_lc_timer_${questionId}`);
      if (saved) {
        const parsed = JSON.parse(saved);
        setSeconds(parsed.seconds || 0);
        setIsRunning(parsed.isRunning || false);
      } else {
        setSeconds(0);
        setIsRunning(false);
      }
    } catch {
      setSeconds(0);
      setIsRunning(false);
    }
  }, [questionId]);

  // Save timer state
  useEffect(() => {
    try {
      localStorage.setItem(`intervyn_lc_timer_${questionId}`, JSON.stringify({
        seconds,
        isRunning
      }));
    } catch {}
  }, [seconds, isRunning, questionId]);

  // Timer tick
  useEffect(() => {
    if (isRunning) {
      intervalRef.current = setInterval(() => {
        setSeconds(prev => prev + 1);
      }, 1000);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
    }

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isRunning]);

  const toggleRunning = () => {
    setIsRunning(prev => !prev);
  };

  const handleReset = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsRunning(false);
    setSeconds(0);
  };

  // Format HH:MM:SS
  const formatTime = (totalSec: number) => {
    const hrs = Math.floor(totalSec / 3600);
    const mins = Math.floor((totalSec % 3600) / 60);
    const secs = totalSec % 60;
    const pad = (n: number) => n.toString().padStart(2, '0');
    return `${pad(hrs)}:${pad(mins)}:${pad(secs)}`;
  };

  return (
    <div 
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono transition-colors border ${
        isRunning 
          ? 'bg-accent/10 border-accent/40 text-accent' 
          : 'bg-surface border-border text-text-muted hover:text-text'
      }`}
      title="Question Timer (LeetCode Style)"
    >
      <button
        type="button"
        onClick={toggleRunning}
        className="p-0.5 rounded hover:bg-surface-hover text-inherit transition-colors cursor-pointer"
        title={isRunning ? "Pause Timer" : "Start Timer"}
      >
        {isRunning ? (
          <Pause className="w-3 h-3 fill-current" />
        ) : (
          <Play className="w-3 h-3 fill-current" />
        )}
      </button>

      <span className="font-semibold tracking-wider select-none text-[11.5px]">
        {formatTime(seconds)}
      </span>

      <button
        type="button"
        onClick={handleReset}
        className="p-0.5 rounded hover:bg-surface-hover text-text-muted hover:text-text transition-colors cursor-pointer"
        title="Reset Timer"
      >
        <RotateCcw className="w-3 h-3" />
      </button>
    </div>
  );
};
