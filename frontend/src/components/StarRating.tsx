import React from 'react';
import { Star } from 'lucide-react';

interface StarRatingProps {
  rating: number; // 0.0 to 5.0
  maxStars?: number;
  size?: 'sm' | 'md' | 'lg';
}

export const StarRating: React.FC<StarRatingProps> = ({
  rating,
  maxStars = 5,
  size = 'md'
}) => {
  const sizeClasses = {
    sm: 'w-3.5 h-3.5',
    md: 'w-4 h-4',
    lg: 'w-5 h-5'
  };

  return (
    <div className="flex items-center gap-1.5">
      <div className="flex items-center gap-0.5">
        {Array.from({ length: maxStars }).map((_, i) => {
          const fillPercentage = Math.max(0, Math.min(100, (rating - i) * 100));

          return (
            <div key={i} className="relative inline-block">
              {/* Background empty star */}
              <Star className={`${sizeClasses[size]} text-slate-700`} fill="currentColor" />
              {/* Foreground filled star with clip */}
              {fillPercentage > 0 && (
                <div
                  className="absolute top-0 left-0 overflow-hidden"
                  style={{ width: `${fillPercentage}%` }}
                >
                  <Star className={`${sizeClasses[size]} text-amber-400`} fill="currentColor" />
                </div>
              )}
            </div>
          );
        })}
      </div>
      <span className="text-xs font-mono font-bold text-amber-300 ml-1">
        {rating.toFixed(2)} / 5.0
      </span>
    </div>
  );
};
