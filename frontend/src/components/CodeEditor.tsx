import React from 'react';
import { RotateCcw, Copy, Check } from 'lucide-react';

interface CodeEditorProps {
  value: string;
  onChange: (value: string) => void;
  language?: string;
  onReset?: () => void;
  readOnly?: boolean;
}

export const CodeEditor: React.FC<CodeEditorProps> = ({
  value,
  onChange,
  language = 'python',
  onReset,
  readOnly = false
}) => {
  const [copied, setCopied] = React.useState(false);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Tab') {
      e.preventDefault();
      const target = e.target as HTMLTextAreaElement;
      const start = target.selectionStart;
      const end = target.selectionEnd;

      // Insert 4 spaces
      const newValue = value.substring(0, start) + '    ' + value.substring(end);
      onChange(newValue);

      // Reposition cursor
      setTimeout(() => {
        target.selectionStart = target.selectionEnd = start + 4;
      }, 0);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const lineCount = Math.max(8, value.split('\n').length);

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950 overflow-hidden shadow-md flex flex-col font-mono">
      {/* Editor Header Bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-900 border-b border-slate-800 text-xs text-slate-400">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-rose-500/80" />
            <div className="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
          </div>
          <span className="ml-2 font-semibold text-slate-300 uppercase">{language}</span>
        </div>

        <div className="flex items-center gap-2">
          {onReset && !readOnly && (
            <button
              onClick={onReset}
              className="flex items-center gap-1 hover:text-slate-200 px-2 py-1 rounded hover:bg-slate-800 transition-colors"
              title="Reset starter code"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset</span>
            </button>
          )}

          <button
            onClick={handleCopy}
            className="flex items-center gap-1 hover:text-slate-200 px-2 py-1 rounded hover:bg-slate-800 transition-colors"
            title="Copy code"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>
        </div>
      </div>

      {/* Editor Body with Line Numbers */}
      <div className="relative flex flex-1 min-h-[220px]">
        {/* Line Numbers */}
        <div className="select-none py-3 px-3 text-right bg-slate-900/40 border-r border-slate-800/60 text-slate-600 text-xs leading-6 font-mono w-12">
          {Array.from({ length: lineCount }).map((_, i) => (
            <div key={i}>{i + 1}</div>
          ))}
        </div>

        {/* Textarea */}
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          readOnly={readOnly}
          spellCheck={false}
          className="flex-1 p-3 bg-transparent text-slate-100 text-xs leading-6 font-mono resize-y outline-none selection:bg-brand-500/30 selection:text-white placeholder:text-slate-600"
          placeholder="# Write your optimal solution here..."
        />
      </div>
    </div>
  );
};
