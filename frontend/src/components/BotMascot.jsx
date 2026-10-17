import './BotMascot.css';

export default function BotMascot() {
  return (
    <div className="bot-wrap" aria-hidden="true">
      <svg className="bot" viewBox="0 0 240 240" width="220" height="220">
        <ellipse className="sh" cx="120" cy="228" rx="44" ry="7" fill="#000" />
        <path className="tw" d="M206 60v12M200 66h12" stroke="#3FD08F" strokeWidth="3" strokeLinecap="round" fill="none" />
        <path className="tw" style={{ animationDelay: '.8s' }} d="M28 120v10M23 125h10" stroke="#46A7F0" strokeWidth="3" strokeLinecap="round" fill="none" />
        <path className="tw" style={{ animationDelay: '1.5s' }} d="M214 168v8M210 172h8" stroke="#46A7F0" strokeWidth="3" strokeLinecap="round" fill="none" />
        <g className="fl">
          <rect x="6" y="14" width="84" height="30" rx="12" fill="var(--surface)" stroke="var(--border)" />
          <text className="m1" x="48" y="33" textAnchor="middle" fontSize="12" fill="var(--text)">Ready?</text>
          <text className="m2" x="48" y="33" textAnchor="middle" fontSize="12" fill="var(--text)">Let's go</text>
          <line x1="120" y1="40" x2="120" y2="60" stroke="#46A7F0" strokeWidth="4" strokeLinecap="round" />
          <circle className="pu" cx="120" cy="34" r="7" fill="#3FD08F" />
          <g className="al" style={{ transformOrigin: '90px 150px' }}>
            <line x1="90" y1="150" x2="68" y2="180" stroke="#46A7F0" strokeWidth="10" strokeLinecap="round" />
            <circle cx="66" cy="183" r="8" fill="#46A7F0" />
          </g>
          <g className="aw" style={{ transformOrigin: '150px 150px' }}>
            <line x1="150" y1="150" x2="178" y2="128" stroke="#46A7F0" strokeWidth="10" strokeLinecap="round" />
            <circle cx="181" cy="125" r="8" fill="#46A7F0" />
          </g>
          <rect x="96" y="194" width="20" height="12" rx="6" fill="#46A7F0" />
          <rect x="124" y="194" width="20" height="12" rx="6" fill="#46A7F0" />
          <rect x="88" y="136" width="64" height="58" rx="20" fill="#3FD08F" />
          <rect x="102" y="150" width="36" height="26" rx="7" fill="#0B100E" />
          <rect className="bar" x="108" y="158" width="6" height="12" rx="2" fill="#7FE7FF" />
          <rect className="bar" style={{ animationDelay: '.3s' }} x="117" y="154" width="6" height="16" rx="2" fill="#7FE7FF" />
          <rect className="bar" style={{ animationDelay: '.6s' }} x="126" y="161" width="6" height="9" rx="2" fill="#7FE7FF" />
          <rect x="62" y="84" width="10" height="22" rx="5" fill="#3FD08F" />
          <rect x="168" y="84" width="10" height="22" rx="5" fill="#3FD08F" />
          <rect x="72" y="58" width="96" height="74" rx="24" fill="#46A7F0" />
          <rect x="84" y="70" width="72" height="50" rx="16" fill="#0B100E" />
          <g className="ey">
            <ellipse className="bl" cx="104" cy="92" rx="6" ry="8" fill="#7FE7FF" />
            <ellipse className="bl" cx="136" cy="92" rx="6" ry="8" fill="#7FE7FF" />
          </g>
          <path d="M111 107Q120 114 129 107" stroke="#3FD08F" strokeWidth="3" fill="none" strokeLinecap="round" />
        </g>
      </svg>
    </div>
  );
}
