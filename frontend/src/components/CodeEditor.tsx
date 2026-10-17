import React, { useState, useRef, useEffect } from 'react';
import Editor, { OnMount } from '@monaco-editor/react';
import { 
  RotateCcw, Copy, Check, Code2, Play, Sparkles, 
  Maximize2, Minimize2, CheckCheck 
} from 'lucide-react';
import { SUPPORTED_LANGUAGES } from '../utils/boilerplate_generator';

export const EDITOR_THEMES = [
  { id: 'intervyn-dark', label: 'Intervyn Dark' },
  { id: 'intervyn-light', label: 'Intervyn Light' },
  { id: 'vs-dark', label: 'Dark (VS Code)' },
  { id: 'vs-light', label: 'Light' },
  { id: 'hc-black', label: 'High Contrast' }
];

interface CodeEditorProps {
  value: string;
  onChange: (value: string) => void;
  language?: string;
  theme?: string;
  onThemeChange?: (theme: string) => void;
  onReset?: () => void;
  readOnly?: boolean;
  height?: string | number;
  showLanguageSelector?: boolean;
  onLanguageChange?: (lang: string) => void;
  onRunCode?: () => void;
  isRunning?: boolean;
  hideHeader?: boolean;
  showFooterStatus?: boolean;
  onCursorChange?: (line: number, col: number) => void;
}

export const CodeEditor: React.FC<CodeEditorProps> = ({
  value,
  onChange,
  language = 'python',
  theme = 'intervyn-dark',
  onThemeChange,
  onReset,
  readOnly = false,
  height = '340px',
  showLanguageSelector = true,
  onLanguageChange,
  onRunCode,
  isRunning = false,
  hideHeader = false,
  showFooterStatus = true,
  onCursorChange
}) => {
  const [copied, setCopied] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [selectedLang, setSelectedLang] = useState(language.toLowerCase());
  const [selectedTheme, setSelectedTheme] = useState(theme);
  const [formatNotice, setFormatNotice] = useState(false);
  const [cursorPos, setCursorPos] = useState({ line: 1, col: 1 });
  const editorRef = useRef<any>(null);
  const monacoRef = useRef<any>(null);
  const onRunCodeRef = useRef(onRunCode);

  useEffect(() => {
    onRunCodeRef.current = onRunCode;
  }, [onRunCode]);

  useEffect(() => {
    setSelectedLang(language.toLowerCase());
  }, [language]);

  useEffect(() => {
    setSelectedTheme(theme);
    if (monacoRef.current) {
      monacoRef.current.editor.setTheme(theme);
    }
  }, [theme]);

  // Synchronize Monaco theme with data-theme when using intervyn themes
  useEffect(() => {
    const handleThemeChange = () => {
      const docTheme = document.documentElement.getAttribute('data-theme') || 'dark';
      const targetTheme = docTheme === 'light' ? 'intervyn-light' : 'intervyn-dark';
      if (!theme || theme.startsWith('intervyn-')) {
        setSelectedTheme(targetTheme);
        if (monacoRef.current) {
          monacoRef.current.editor.setTheme(targetTheme);
        }
        if (onThemeChange) {
          onThemeChange(targetTheme);
        }
      }
    };

    window.addEventListener('intervyn-theme-change', handleThemeChange);
    const observer = new MutationObserver((mutations) => {
      for (const m of mutations) {
        if (m.type === 'attributes' && m.attributeName === 'data-theme') {
          handleThemeChange();
        }
      }
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

    return () => {
      window.removeEventListener('intervyn-theme-change', handleThemeChange);
      observer.disconnect();
    };
  }, [theme, onThemeChange]);

  const handleEditorDidMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;
    monacoRef.current = monaco;

    // Custom dark theme definition matching intervyn dark tokens
    monaco.editor.defineTheme('intervyn-dark', {
      base: 'vs-dark',
      inherit: true,
      rules: [
        { token: 'comment', foreground: '8F8D88', fontStyle: 'italic' },
        { token: 'keyword', foreground: 'E8603C', fontStyle: 'bold' },
        { token: 'string', foreground: '529B72' },
        { token: 'number', foreground: 'E8603C' },
        { token: 'type', foreground: 'EDEBE6' }
      ],
      colors: {
        'editor.background': '#0E0E10',
        'editor.foreground': '#EDEBE6',
        'editorLineNumber.foreground': '#5C5B57',
        'editorLineNumber.activeForeground': '#EDEBE6',
        'editor.selectionBackground': '#E8603C33',
        'editor.inactiveSelectionBackground': '#E8603C1A',
        'editorCursor.foreground': '#E8603C',
        'editorWhitespace.foreground': '#2A2A2D',
        'editor.lineHighlightBackground': '#161618',
        'editorGutter.background': '#0E0E10'
      }
    });

    // Custom light theme definition matching intervyn light tokens
    monaco.editor.defineTheme('intervyn-light', {
      base: 'vs',
      inherit: true,
      rules: [
        { token: 'comment', foreground: '6B6963', fontStyle: 'italic' },
        { token: 'keyword', foreground: 'C4421F', fontStyle: 'bold' },
        { token: 'string', foreground: '3B7A57' },
        { token: 'number', foreground: 'C4421F' },
        { token: 'type', foreground: '1A1A1A' }
      ],
      colors: {
        'editor.background': '#F7F5F0',
        'editor.foreground': '#1A1A1A',
        'editorLineNumber.foreground': '#9E9C96',
        'editorLineNumber.activeForeground': '#1A1A1A',
        'editor.selectionBackground': '#C4421F26',
        'editor.inactiveSelectionBackground': '#C4421F14',
        'editorCursor.foreground': '#C4421F',
        'editorWhitespace.foreground': '#E2DFD7',
        'editor.lineHighlightBackground': '#F0EDE6',
        'editorGutter.background': '#F7F5F0'
      }
    });

    const docTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    let activeTheme = selectedTheme;
    if (activeTheme === 'intervyn-dark' || activeTheme === 'intervyn-light') {
      activeTheme = docTheme === 'light' ? 'intervyn-light' : 'intervyn-dark';
    }
    monaco.editor.setTheme(activeTheme);

    // Track cursor movements
    editor.onDidChangeCursorPosition((e) => {
      const pos = { line: e.position.lineNumber, col: e.position.column };
      setCursorPos(pos);
      if (onCursorChange) {
        onCursorChange(pos.line, pos.col);
      }
    });

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

  const handleThemeChange = (newTheme: string) => {
    setSelectedTheme(newTheme);
    if (monacoRef.current) {
      monacoRef.current.editor.setTheme(newTheme);
    }
    if (onThemeChange) {
      onThemeChange(newTheme);
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
      className={`rounded-card border border-border bg-bg overflow-hidden flex flex-col font-mono transition-all ${
        isFullscreen ? 'fixed inset-4 z-50 border-accent' : 'relative h-full'
      }`}
    >
      {/* Editor Header Bar */}
      {!hideHeader && (
        <div className="flex flex-wrap items-center justify-between px-3.5 py-2 bg-surface border-b border-border text-xs text-text-muted gap-2 shrink-0">
          <div className="flex items-center gap-3">
            {/* Language Selector Dropdown */}
            {showLanguageSelector ? (
              <div className="flex items-center gap-1.5">
                <Code2 className="w-3.5 h-3.5 text-accent" />
                <select
                  value={selectedLang}
                  onChange={(e) => handleLangChange(e.target.value)}
                  disabled={readOnly}
                  className="bg-bg border border-border hover:border-border-focus rounded px-2.5 py-1 text-[11px] font-medium text-text focus:outline-none focus:border-accent cursor-pointer font-mono"
                >
                  {SUPPORTED_LANGUAGES.map((l) => (
                    <option key={l.id} value={l.id} className="bg-surface text-text">
                      {l.label}
                    </option>
                  ))}
                </select>
              </div>
            ) : (
              <span className="font-mono text-text uppercase tracking-wider text-[11px]">
                {selectedLang}
              </span>
            )}

            {/* Theme Selector */}
            <div className="hidden sm:flex items-center gap-1 text-[11px]">
              <span className="text-text-muted font-sans">Theme:</span>
              <select
                value={selectedTheme}
                onChange={(e) => handleThemeChange(e.target.value)}
                className="bg-bg border border-border hover:border-border-focus rounded px-2 py-0.5 text-[11px] text-text focus:outline-none font-mono"
              >
                {EDITOR_THEMES.map((t) => (
                  <option key={t.id} value={t.id} className="bg-surface text-text">
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            {formatNotice && (
              <span className="inline-flex items-center gap-1 text-[10px] text-success font-mono">
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
                className="flex items-center gap-1 hover:text-text px-2 py-1 rounded hover:bg-surface-hover text-[11px] text-text-muted transition-colors"
                title="Auto-format code document"
              >
                <span className="hidden sm:inline">Format</span>
              </button>
            )}

            {/* Reset Code */}
            {onReset && !readOnly && (
              <button
                type="button"
                onClick={onReset}
                className="flex items-center gap-1 hover:text-text px-2 py-1 rounded hover:bg-surface-hover text-[11px] text-text-muted transition-colors"
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
              className="flex items-center gap-1 hover:text-text px-2 py-1 rounded hover:bg-surface-hover text-[11px] text-text-muted transition-colors"
              title="Copy code to clipboard"
            >
              {copied ? <Check className="w-3 h-3 text-success" /> : <Copy className="w-3 h-3" />}
              <span className="hidden sm:inline">{copied ? 'Copied' : 'Copy'}</span>
            </button>

            {/* Fullscreen Toggle */}
            <button
              type="button"
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="p-1 text-text-muted hover:text-text rounded hover:bg-surface-hover transition-colors"
              title={isFullscreen ? 'Exit Fullscreen' : 'Expand Editor to Fullscreen'}
            >
              {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
            </button>

            {/* Run Code Button */}
            {onRunCode && (
              <button
                type="button"
                onClick={onRunCode}
                disabled={isRunning}
                className="ml-2 flex items-center gap-1.5 px-3 py-1 rounded bg-accent hover:bg-accent-hover disabled:opacity-50 text-accent-contrast text-[11px] font-medium transition-colors"
                title="Execute code against test cases"
              >
                {isRunning ? (
                  <div className="w-3 h-3 rounded-full border-2 border-accent-contrast border-t-transparent animate-spin" />
                ) : (
                  <Play className="w-3 h-3 fill-current" />
                )}
                <span>{isRunning ? 'Running...' : 'Run Code'}</span>
              </button>
            )}
          </div>
        </div>
      )}

      {/* Monaco Editor Canvas */}
      <div className="relative flex-1 w-full min-h-0">
        <Editor
          height={isFullscreen ? '100%' : (height === '100%' ? '100%' : height)}
          language={monacoLanguage}
          value={value}
          onChange={(val) => onChange(val || '')}
          onMount={handleEditorDidMount}
          theme={selectedTheme}
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
            padding: { top: 12, bottom: 12 },
            // VS Code Autocomplete & IntelliSense capabilities
            quickSuggestions: { other: true, comments: false, strings: true },
            wordBasedSuggestions: 'allDocuments',
            suggestOnTriggerCharacters: true,
            parameterHints: { enabled: true },
            autoClosingBrackets: 'always',
            autoClosingQuotes: 'always',
            autoClosingOvertype: 'always',
            autoIndent: 'full',
            formatOnPaste: true,
            formatOnType: true,
            tabCompletion: 'on'
          }}
          loading={
            <div className="flex flex-col items-center justify-center h-full min-h-[220px] bg-bg text-text-muted text-xs space-y-2">
              <div className="w-5 h-5 rounded-full border-2 border-accent border-t-transparent animate-spin" />
              <span>Loading VS Code Editor...</span>
            </div>
          }
        />
      </div>

      {/* HackerRank / Monaco Bottom Status Bar */}
      {showFooterStatus && (
        <div className="h-6 shrink-0 px-3 bg-surface border-t border-border flex items-center justify-end text-[11px] text-text-muted font-mono select-none">
          <span>Line: {cursorPos.line} Col: {cursorPos.col}</span>
        </div>
      )}
    </div>
  );
};
