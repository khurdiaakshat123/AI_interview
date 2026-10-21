import React from 'react';
import { LCAnalytics } from '../../types';
import { Trophy, Code2, Database, Star, Flame } from 'lucide-react';

interface LCAnalyticsCardProps {
  analytics: LCAnalytics | null;
  loading?: boolean;
}

export const LCAnalyticsCard: React.FC<LCAnalyticsCardProps> = ({ analytics, loading }) => {
  if (loading || !analytics) {
    return (
      <div className="p-6 rounded-[12px] bg-surface border border-border animate-pulse">
        <div className="h-4 bg-border/40 rounded w-1/4 mb-4"></div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="h-16 bg-border/20 rounded"></div>
          <div className="h-16 bg-border/20 rounded"></div>
          <div className="h-16 bg-border/20 rounded"></div>
          <div className="h-16 bg-border/20 rounded"></div>
        </div>
      </div>
    );
  }

  const { totalQuestions, solvedCount, attemptedCount, starredCount, dsa, database, difficulty } = analytics;
  const overallPercentage = totalQuestions > 0 ? ((solvedCount / totalQuestions) * 100).toFixed(1) : '0';

  const easyTotal = difficulty?.easy?.total || 0;
  const easySolved = difficulty?.easy?.solved || 0;
  const easyPct = easyTotal > 0 ? (easySolved / easyTotal) * 100 : 0;

  const medTotal = difficulty?.medium?.total || 0;
  const medSolved = difficulty?.medium?.solved || 0;
  const medPct = medTotal > 0 ? (medSolved / medTotal) * 100 : 0;

  const hardTotal = difficulty?.hard?.total || 0;
  const hardSolved = difficulty?.hard?.solved || 0;
  const hardPct = hardTotal > 0 ? (hardSolved / hardTotal) * 100 : 0;

  return (
    <div className="p-6 rounded-[12px] bg-surface border border-border shadow-xs">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
        {/* Left Column: Overall Circular / Progress Gauge */}
        <div className="lg:col-span-4 flex items-center gap-5 sm:border-r sm:border-border sm:pr-6">
          {/* Circular Chart Representation */}
          <div className="relative w-24 h-24 shrink-0 flex items-center justify-center">
            <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
              {/* Background circle */}
              <circle
                cx="50"
                cy="50"
                r="40"
                className="stroke-border"
                strokeWidth="8"
                fill="none"
              />
              {/* Progress stroke */}
              <circle
                cx="50"
                cy="50"
                r="40"
                className="stroke-accent transition-all duration-700 ease-out"
                strokeWidth="8"
                strokeDasharray="251.2"
                strokeDashoffset={251.2 - (251.2 * Number(overallPercentage)) / 100}
                strokeLinecap="round"
                fill="none"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
              <span className="text-xl font-bold font-mono text-text leading-none">{solvedCount}</span>
              <span className="text-[10px] text-text-muted font-mono mt-0.5">/ {totalQuestions}</span>
            </div>
          </div>

          <div className="space-y-1">
            <div className="flex items-center gap-1.5 text-xs font-mono uppercase tracking-wider text-text-muted">
              <Trophy className="w-3.5 h-3.5 text-accent" />
              <span>Solved Progress</span>
            </div>
            <div className="text-[18px] font-semibold text-text font-sans">
              {overallPercentage}% Completed
            </div>
            <div className="flex items-center gap-3 text-xs text-text-muted font-mono">
              <span className="flex items-center gap-1">
                <Flame className="w-3 h-3 text-amber-500" />
                {attemptedCount} Attempted
              </span>
              <span>·</span>
              <span className="flex items-center gap-1">
                <Star className="w-3 h-3 text-amber-400 fill-amber-400" />
                {starredCount} Saved
              </span>
            </div>
          </div>
        </div>

        {/* Center Column: Difficulty Breakdown Bars */}
        <div className="lg:col-span-5 space-y-3 lg:border-r lg:border-border lg:pr-6">
          <div className="text-xs font-mono uppercase tracking-wider text-text-muted flex justify-between">
            <span>Difficulty Breakdown</span>
            <span>Target Mastery</span>
          </div>

          {/* Easy Bar */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs font-mono">
              <span className="text-emerald-500 font-medium">Easy</span>
              <span className="text-text-muted">
                <strong className="text-text font-bold">{easySolved}</strong> / {easyTotal}
              </span>
            </div>
            <div className="h-1.5 w-full bg-bg rounded-full overflow-hidden border border-border/50">
              <div 
                className="h-full bg-emerald-500 rounded-full transition-all duration-500" 
                style={{ width: `${Math.max(easyPct, easySolved > 0 ? 3 : 0)}%` }} 
              />
            </div>
          </div>

          {/* Medium Bar */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs font-mono">
              <span className="text-amber-500 font-medium">Medium</span>
              <span className="text-text-muted">
                <strong className="text-text font-bold">{medSolved}</strong> / {medTotal}
              </span>
            </div>
            <div className="h-1.5 w-full bg-bg rounded-full overflow-hidden border border-border/50">
              <div 
                className="h-full bg-amber-500 rounded-full transition-all duration-500" 
                style={{ width: `${Math.max(medPct, medSolved > 0 ? 3 : 0)}%` }} 
              />
            </div>
          </div>

          {/* Hard Bar */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs font-mono">
              <span className="text-rose-500 font-medium">Hard</span>
              <span className="text-text-muted">
                <strong className="text-text font-bold">{hardSolved}</strong> / {hardTotal}
              </span>
            </div>
            <div className="h-1.5 w-full bg-bg rounded-full overflow-hidden border border-border/50">
              <div 
                className="h-full bg-rose-500 rounded-full transition-all duration-500" 
                style={{ width: `${Math.max(hardPct, hardSolved > 0 ? 3 : 0)}%` }} 
              />
            </div>
          </div>
        </div>

        {/* Right Column: Category Split (DSA & Database) */}
        <div className="lg:col-span-3 grid grid-cols-2 lg:grid-cols-1 gap-3">
          {/* DSA Card */}
          <div className="p-3 rounded-lg bg-bg border border-border flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-md bg-surface flex items-center justify-center border border-border text-accent">
                <Code2 className="w-4 h-4" />
              </div>
              <div>
                <div className="text-[13px] font-medium text-text">Algorithms</div>
                <div className="text-[11px] text-text-muted font-mono">{dsa?.solved || 0} / {dsa?.total || 0} Solved</div>
              </div>
            </div>
            <span className="text-xs font-mono font-semibold text-text">{dsa?.percentage || 0}%</span>
          </div>

          {/* Database Card */}
          <div className="p-3 rounded-lg bg-bg border border-border flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-md bg-surface flex items-center justify-center border border-border text-amber-500">
                <Database className="w-4 h-4" />
              </div>
              <div>
                <div className="text-[13px] font-medium text-text">Database (SQL)</div>
                <div className="text-[11px] text-text-muted font-mono">{database?.solved || 0} / {database?.total || 0} Solved</div>
              </div>
            </div>
            <span className="text-xs font-mono font-semibold text-text">{database?.percentage || 0}%</span>
          </div>
        </div>
      </div>
    </div>
  );
};
