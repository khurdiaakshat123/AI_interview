import React, { useEffect, useState } from 'react';
import { Clock, AlertTriangle } from 'lucide-react';

interface TimerProps {
  initialMinutes: number;
  onTimeExpired: () => void;
  isRunning?: boolean;
}

export const Timer: React.FC<TimerProps> = ({
  initialMinutes,
  onTimeExpired,
  isRunning = true
}) => {
  const [secondsRemaining, setSecondsRemaining] = useState(initialMinutes * 60);

  useEffect(() => {
    if (!isRunning) return;

    const interval = setInterval(() => {
      setSecondsRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          onTimeExpired();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [isRunning, onTimeExpired]);

  const minutes = Math.floor(secondsRemaining / 60);
  const seconds = secondsRemaining % 60;
  const isUrgent = secondsRemaining < 300; // less than 5 minutes

  return (
    <div
      className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border font-mono text-xs font-medium transition-colors ${
        isUrgent
          ? 'bg-danger/10 border-danger/40 text-danger animate-pulse'
          : 'bg-surface border-border text-text'
      }`}
    >
      {isUrgent ? (
        <AlertTriangle className="w-3.5 h-3.5 text-danger" />
      ) : (
        <Clock className="w-3.5 h-3.5 text-text-muted" />
      )}
      <span>
        {String(minutes).padStart(2, '0')}:{String(seconds).padStart(2, '0')}
      </span>
    </div>
  );
};
