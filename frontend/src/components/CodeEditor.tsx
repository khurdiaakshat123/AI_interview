import React, { useState, useRef, useEffect } from 'react';
import Editor, { OnMount } from '@monaco-editor/react';
import { 
  RotateCcw, Copy, Check, Code2, Play, Sparkles, 
  Maximize2, Minimize2, CheckCheck 
} from 'lucide-react';

interface CodeEditorProps {
  value: string;
  onChange: (value: string) => void;
  language?: string;
  onReset?: () => void;
  readOnly?: boolean;
  height?: string | number;
  showLanguageSelector?: boolean;
  onLanguageChange?: (lang: string) => void;
  onRunCode?: () => void;
  isRunning?: boolean;
}

import { SUPPORTED_LANGUAGES } from '../utils/boilerplate_generator';

export const CodeEditor: React.FC<CodeEditorProps> = ({
  value,
  onChange,
  language = 'python',
  onReset,
  readOnly = false,
  height = '340px',
  showLanguageSelector = true,
  onLanguageChange,
  onRunCode,
  isRunning = false
}) => {
  const [copied, setCopied] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [selectedLang, setSelectedLang] = useState(language.toLowerCase());
  const [formatNotice, setFormatNotice] = useState(false);
  const editorRef = useRef<any>(null);
  const onRunCodeRef = useRef(onRunCode);

  useEffect(() => {
    onRunCodeRef.current = onRunCode;
  }, [onRunCode]);

  React.useEffect(() => {
    setSelectedLang(language.toLowerCase());
  }, [language]);

  const handleEditorDidMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;

    monaco.editor.defineTheme('intervyn-dark', {
      base: 'vs-dark',
      inherit: true,
      rules: [
        { token: 'comment', foreground: '6A9955', fontStyle: 'italic' },
        { token: 'keyword', foreground: '569CD6', fontStyle: 'bold' },
        { token: 'string', foreground: 'CE9178' },
        { token: 'number', foreground: 'B5CEA8' },
        { token: 'type', foreground: '4EC9B0' }
      ],
      colors: {
        'editor.background': '#020617',
        'editor.foreground': '#F8FAFC',
        'editorLineNumber.foreground': '#475569',
        'editorLineNumber.activeForeground': '#94A3B8',
        'editor.selectionBackground': '#3b82f633',
        'editor.inactiveSelectionBackground': '#3b82f61a',
        'editorCursor.foreground': '#60A5FA',
        'editorWhitespace.foreground': '#1E293B'
      }
    });
    monaco.editor.setTheme('intervyn-dark');

    // Bind Ctrl+Enter / Cmd+Enter to Run Code
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
      if (onRunCodeRef.current) {
        onRunCodeRef.current();
      }
    });
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleFormatCode = () => {
    if (editorRef.current) {
      try {
        editorRef.current.getAction('editor.action.formatDocument')?.run();
        setFormatNotice(true);
        setTimeout(() => setFormatNotice(false), 2000);
      } catch (err) {
        console.warn('Format action failed:', err);
      }
    }
  };

  const handleLangChange = (newLang: string) => {
    setSelectedLang(newLang);
    if (onLanguageChange) {
      onLanguageChange(newLang);
    }
  };

  const monacoLanguage = 
    selectedLang === 'sql' ? 'sql' :
    selectedLang.startsWith('cpp') || selectedLang === 'c++' ? 'cpp' :
    selectedLang === 'c' ? 'c' :
    selectedLang === 'java' ? 'java' :
    selectedLang === 'python' || selectedLang === 'py' ? 'python' :
    selectedLang === 'javascript' || selectedLang === 'js' ? 'javascript' :
    selectedLang === 'typescript' || selectedLang === 'ts' ? 'typescript' :
    selectedLang === 'go' ? 'go' :
    selectedLang === 'rust' ? 'rust' :
    selectedLang === 'csharp' || selectedLang === 'cs' ? 'csharp' : 'python';

  return (
    <div
      className={`rounded-2xl border border-slate-800 bg-slate-950 overflow-hidden shadow-lg flex flex-col font-mono transition-all ${
        isFullscreen ? 'fixed inset-4 z-50 shadow-2xl border-indigo-500/50' : 'relative'
      }`}
    >
      {/* Editor Header Bar */}
      <div className="flex flex-wrap items-center justify-between px-4 py-2.5 bg-slate-900/90 border-b border-slate-800/80 text-xs text-slate-400 gap-2">
        <div className="flex items-center gap-3">
          {/* Mac-style window controls */}
          <div className="flex gap-1.5 shrink-0">
            <div className="w-2.5 h-2.5 rounded-full bg-rose-500/80" />
            <div className="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
          </div>

          {/* Language Selector Dropdown */}
          {showLanguageSelector ? (
            <div className="flex items-center gap-1.5">
              <Code2 className="w-3.5 h-3.5 text-indigo-400" />
              <select
                value={selectedLang}
                onChange={(e) => handleLangChange(e.target.value)}
                disabled={readOnly}
                className="bg-slate-950 border border-slate-700/80 hover:border-slate-600 rounded-lg px-2.5 py-1 text-[11px] font-semibold text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500 cursor-pointer font-sans"
              >
                {SUPPORTED_LANGUAGES.map((l) => (
                  <option key={l.id} value={l.id} className="bg-slate-900 text-slate-200">
                    {l.label}
                  </option>
                ))}
              </select>
            </div>
          ) : (
            <span className="font-semibold text-slate-300 uppercase tracking-wider text-[11px]">
              {selectedLang}
            </span>
          )}

          {formatNotice && (
            <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400 font-sans">
              <CheckCheck className="w-3 h-3" />
              Formatted
            </span>
          )}
        </div>

        {/* Editor Actions */}
        <div className="flex items-center gap-1.5 ml-auto">
          {/* Format Code */}
          {!readOnly && (
            <button
              type="button"
              onClick={handleFormatCode}
              className="flex items-center gap-1 hover:text-slate-200 px-2 py-1 rounded-lg hover:bg-slate-800 text-[11px] transition-colors"
              title="Auto-format code document"
            >
              <Sparkles className="w-3 h-3 text-indigo-400" />
              <span className="hidden sm:inline">Format</span>
            </button>
          )}

          {/* Reset Code */}
          {onReset && !readOnly && (
            <button
              type="button"
              onClick={onReset}
              className="flex items-center gap-1 hover:text-slate-200 px-2 py-1 rounded-lg hover:bg-slate-800 text-[11px] transition-colors"
              title="Reset starter template code"
            >
              <RotateCcw className="w-3 h-3" />
              <span className="hidden sm:inline">Reset</span>
            </button>
          )}

          {/* Copy Code */}
          <button
            type="button"
            onClick={handleCopy}
            className="flex items-center gap-1 hover:text-slate-200 px-2 py-1 rounded-lg hover:bg-slate-800 text-[11px] transition-colors"
            title="Copy code to clipboard"
          >
            {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
            <span className="hidden sm:inline">{copied ? 'Copied' : 'Copy'}</span>
          </button>

          {/* Fullscreen Toggle */}
          <button
            type="button"
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-1.5 hover:text-slate-200 rounded-lg hover:bg-slate-800 transition-colors"
            title={isFullscreen ? 'Exit Fullscreen' : 'Expand Editor to Fullscreen'}
          >
            {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5 text-slate-400" />}
          </button>

          {/* Run Code Button */}
          {onRunCode && (
            <button
              type="button"
              onClick={onRunCode}
              disabled={isRunning}
              className="ml-2 flex items-center gap-1.5 px-3 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-[11px] font-bold shadow-sm transition-all"
              title="Execute code against test cases"
            >
              {isRunning ? (
                <div className="w-3 h-3 rounded-full border-2 border-white border-t-transparent animate-spin" />
              ) : (
                <Play className="w-3 h-3 fill-current" />
              )}
              <span>{isRunning ? 'Running...' : 'Run Code'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Monaco Editor Canvas */}
      <div className="relative flex-1 w-full" style={{ minHeight: isFullscreen ? 'calc(100vh - 120px)' : height }}>
        <Editor
          height={isFullscreen ? '100%' : height}
          language={monacoLanguage}
          value={value}
          onChange={(val) => onChange(val || '')}
          onMount={handleEditorDidMount}
          theme="vs-dark"
          options={{
            readOnly,
            minimap: { enabled: false },
            fontSize: 13,
            lineNumbers: 'on',
            lineNumbersMinChars: 3,
            glyphMargin: false,
            folding: true,
            scrollBeyondLastLine: false,
            automaticLayout: true,
            tabSize: 4,
            wordWrap: 'on',
            bracketPairColorization: { enabled: true },
            guides: {
              bracketPairs: true,
              indentation: true
            },
            cursorBlinking: 'smooth',
            cursorSmoothCaretAnimation: 'on',
            smoothScrolling: true,
            fontFamily: 'Consolas, "Fira Code", Monaco, "Courier New", monospace',
            padding: { top: 12, bottom: 12 }
          }}
          loading={
            <div className="flex flex-col items-center justify-center h-full min-h-[220px] bg-slate-950 text-slate-500 text-xs space-y-2">
              <div className="w-5 h-5 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
              <span>Loading VS Code Editor...</span>
            </div>
          }
        />
      </div>
    </div>
  );
};
