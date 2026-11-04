import React, { useState } from 'react';
import { Copy, Check, Terminal } from 'lucide-react';

interface MCQCodeBlockProps {
  code: string;
  title?: string;
  language?: string;
}

export const MCQCodeBlock: React.FC<MCQCodeBlockProps> = ({ code, title = "Code Snippet / Execution Trace", language }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const lines = code.split('\n');

  return (
    <div className="my-3.5 rounded-lg border border-border bg-bg/95 overflow-hidden shadow-xs">
      {/* Code Header Bar */}
      <div className="flex items-center justify-between px-3.5 py-1.5 bg-surface/90 border-b border-border text-[11px] font-mono text-text-muted">
        <div className="flex items-center gap-1.5">
          <Terminal className="w-3.5 h-3.5 text-accent" />
          <span className="font-medium text-text">{title}</span>
          {language && (
            <span className="px-1.5 py-0.2 rounded bg-surface border border-border/80 text-[10px] uppercase tracking-wider text-text-muted">
              {language}
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={handleCopy}
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs text-text-muted hover:text-text hover:bg-surface-hover transition-colors cursor-pointer"
          title="Copy code to clipboard"
        >
          {copied ? (
            <>
              <Check className="w-3 h-3 text-emerald-500" />
              <span className="text-[11px] text-emerald-500">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" />
              <span className="text-[11px]">Copy</span>
            </>
          )}
        </button>
      </div>

      {/* Code Content with Line Numbers & Strict Indentation */}
      <div className="overflow-x-auto p-3.5 text-[13px] leading-relaxed font-mono">
        <table className="w-full border-collapse">
          <tbody>
            {lines.map((line, idx) => (
              <tr key={idx} className="hover:bg-surface/40 transition-colors">
                <td className="pr-3.5 select-none text-right text-text-muted/50 text-[11px] w-6 align-top font-mono">
                  {idx + 1}
                </td>
                <td className="whitespace-pre font-mono text-text selection:bg-accent/30 align-top">
                  {line || ' '}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
