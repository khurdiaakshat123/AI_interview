import React from 'react';

interface LogoProps {
  /** Size in pixels for width & height of the mark (default 28) */
  size?: number;
  /** Whether to render the wordmark text next to the mark */
  showWordmark?: boolean;
  /** Custom class for the wrapper */
  className?: string;
  /** Custom class for the mark SVG */
  markClassName?: string;
  /** Custom class for the wordmark text */
  wordmarkClassName?: string;
  /** Whether clicking navigates or triggers an action */
  onClick?: () => void;
}

export const Logo: React.FC<LogoProps> = ({
  size = 28,
  showWordmark = false,
  className = '',
  markClassName = '',
  wordmarkClassName = '',
  onClick,
}) => {
  return (
    <div
      className={`inline-flex items-center gap-[10px] select-none ${onClick ? 'cursor-pointer group' : ''} ${className}`}
      onClick={onClick}
    >
      {/* Intervyn Brand Mark (IV Nexus) */}
      <svg
        width={size}
        height={size}
        viewBox="0 0 28 28"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={`shrink-0 transition-transform duration-200 group-hover:scale-[1.03] ${markClassName}`}
      >
        <defs>
          <linearGradient id="iv-v-grad" x1="14.1" y1="7.5" x2="20.9" y2="20.6" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#E57350" />
            <stop offset="100%" stopColor="var(--accent)" />
          </linearGradient>
          <linearGradient id="iv-bg-grad" x1="0" y1="0" x2="28" y2="28" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="var(--surface-hover)" />
            <stop offset="100%" stopColor="var(--surface)" />
          </linearGradient>
        </defs>

        {/* Squircle Badge Container */}
        <rect
          x="0.75"
          y="0.75"
          width="26.5"
          height="26.5"
          rx="7"
          fill="url(#iv-bg-grad)"
          stroke="var(--border)"
          strokeWidth="1.2"
          className="transition-colors duration-200 group-hover:stroke-accent/50"
        />

        {/* Live Intelligence / Telemetry Node */}
        <circle
          cx="7.2"
          cy="7.2"
          r="1.6"
          fill="var(--success)"
          className="transition-opacity duration-200 group-hover:opacity-90"
        />

        {/* I Stem Pillar (Grounding & Evaluation Standard) */}
        <rect
          x="5.8"
          y="10.8"
          width="2.8"
          height="9.8"
          rx="1.4"
          fill="var(--text)"
        />

        {/* V Dynamic Vector Chevron (Adaptive Depth & Dialogue) */}
        <path
          d="M14.1 7.5 L17.5 20.6 L20.9 7.5"
          stroke="url(#iv-v-grad)"
          strokeWidth="2.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>

      {/* Intervyn Wordmark */}
      {showWordmark && (
        <span
          className={`font-serif text-[26px] text-text tracking-tight font-normal leading-none ${wordmarkClassName}`}
        >
          Intervyn
        </span>
      )}
    </div>
  );
};

export default Logo;
