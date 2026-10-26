import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { 
  Play, Pause, SkipBack, SkipForward, ChevronLeft, ChevronRight, 
  RotateCcw, Bug, ArrowLeft, CheckCircle2, AlertCircle, Clock, 
  Layers, Code2, Terminal, Variable, Database, Copy, Check, Sparkles, Sliders
} from 'lucide-react';
import { api } from '../services/api';
import { LCQuestionDetail, DebugStep, DebugTraceResult } from '../types';

export const PracticeDebugPage: React.FC = () => {
  const { problemSlug } = useParams<{ problemSlug: string }>();
  const navigate = useNavigate();
  const location = useLocation();

  // Retrieved state passed from PracticePage or stored locally
  const statePayload = location.state as {
    code?: string;
    language?: string;
    questionDetail?: LCQuestionDetail;
  } | undefined;

  const [questionDetail, setQuestionDetail] = useState<LCQuestionDetail | null>(
    statePayload?.questionDetail || null
  );
  const [loadingDetail, setLoadingDetail] = useState<boolean>(!statePayload?.questionDetail);

  // Debugger code & language
  const [code, setCode] = useState<string>(() => {
    if (statePayload?.code) return statePayload.code;
    return localStorage.getItem(`intervyn_lc_code_${problemSlug}`) || '';
  });
  const [selectedLang, setSelectedLang] = useState<string>(
    statePayload?.language || 'python3'
  );

  // Testcase setup
  const [testCases, setTestCases] = useState<string[]>([]);
  const [activeCaseTab, setActiveCaseTab] = useState<number>(0);
  const [isCustomCase, setIsCustomCase] = useState<boolean>(false);
  const [customInput, setCustomInput] = useState<string>('');

  // Trace State
  const [isTracing, setIsTracing] = useState<boolean>(false);
  const [traceResult, setTraceResult] = useState<DebugTraceResult | null>(null);
  const [currentStepIndex, setCurrentStepIndex] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(600); // ms per step
  const [copiedCode, setCopiedCode] = useState<boolean>(false);

  const playTimerRef = useRef<any>(null);
  const codeLinesRef = useRef<(HTMLDivElement | null)[]>([]);

  // Load question details if not passed via state
  useEffect(() => {
    if (!questionDetail && problemSlug) {
      setLoadingDetail(true);
      api.getLCQuestion(problemSlug)
        .then(q => {
          setQuestionDetail(q);
          if (!code) {
            const starter = q.starterCode?.[selectedLang] || q.starterCode?.['python3'] || '';
            setCode(starter);
          }
        })
        .catch(err => console.error('Failed to load question details for debug:', err))
        .finally(() => setLoadingDetail(false));
    }
  }, [problemSlug, questionDetail, code, selectedLang]);

  // Extract test cases from question
  useEffect(() => {
    if (questionDetail) {
      const cases: string[] = [];
      if (questionDetail.sampleCases && questionDetail.sampleCases.length > 0) {
        questionDetail.sampleCases.forEach(sc => cases.push(sc.input));
      } else if (questionDetail.examples && questionDetail.examples.length > 0) {
        questionDetail.examples.forEach(ex => cases.push(ex.input));
      }
      setTestCases(cases.length > 0 ? cases : ['[1, 2, 3]']);
      if (!customInput && cases.length > 0) {
        setCustomInput(cases[0]);
      }
    }
  }, [questionDetail]);

  // Active input to debug
  const activeInputData = useMemo(() => {
    if (isCustomCase) return customInput;
    return testCases[activeCaseTab] || customInput || '';
  }, [isCustomCase, customInput, testCases, activeCaseTab]);

  // Execute trace request
  const handleStartTrace = async () => {
    if (!problemSlug || !code) return;
    setIsTracing(true);
    setIsPlaying(false);
    clearInterval(playTimerRef.current);

    try {
      const res = await api.debugLCCode(
        problemSlug,
        code,
        selectedLang,
        activeInputData
      );
      setTraceResult(res);
      setCurrentStepIndex(0);
    } catch (err: any) {
      setTraceResult({
        status: 'ERROR',
        steps: [],
        total_steps: 0,
        max_steps_reached: false,
        error: err.message || 'Failed to start debugger trace.'
      });
    } finally {
      setIsTracing(false);
    }
  };

  // Auto-run trace on initial load once input & code are ready
  useEffect(() => {
    if (code && activeInputData && !traceResult && !isTracing && questionDetail) {
      handleStartTrace();
    }
  }, [code, activeInputData, questionDetail]);

  // Step navigation controls
  const steps = traceResult?.steps || [];
  const currentStep: DebugStep | undefined = steps[currentStepIndex];

  const handleStepNext = () => {
    if (currentStepIndex < steps.length - 1) {
      setCurrentStepIndex(prev => prev + 1);
    } else {
      setIsPlaying(false);
    }
  };

  const handleStepPrev = () => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex(prev => prev - 1);
    }
  };

  const handleJumpFirst = () => {
    setCurrentStepIndex(0);
    setIsPlaying(false);
  };

  const handleJumpLast = () => {
    if (steps.length > 0) {
      setCurrentStepIndex(steps.length - 1);
      setIsPlaying(false);
    }
  };

  const handleTogglePlay = () => {
    setIsPlaying(prev => !prev);
  };

  // Playback timer loop
  useEffect(() => {
    if (isPlaying) {
      playTimerRef.current = setInterval(() => {
        setCurrentStepIndex(prev => {
          if (prev >= steps.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, playbackSpeed);
    } else {
      clearInterval(playTimerRef.current);
    }
    return () => clearInterval(playTimerRef.current);
  }, [isPlaying, steps.length, playbackSpeed]);

  // Auto-scroll active code line into view
  useEffect(() => {
    if (currentStep && codeLinesRef.current[currentStep.line - 1]) {
      codeLinesRef.current[currentStep.line - 1]?.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest'
      });
    }
  }, [currentStepIndex, currentStep]);

  // Code line splitting
  const codeLines = useMemo(() => code.split('\n'), [code]);

  // Categorize variables in current step
  const categorizedVars = useMemo(() => {
    if (!currentStep || !currentStep.variables) return { primitives: [], arrays: [], maps: [], objects: [] };

    const primitives: { key: string; value: any; isChanged: boolean }[] = [];
    const arrays: { key: string; value: any[]; isChanged: boolean }[] = [];
    const maps: { key: string; value: Record<string, any>; isChanged: boolean }[] = [];
    const objects: { key: string; value: any; isChanged: boolean }[] = [];

    const changedSet = new Set(currentStep.changed_vars || []);

    for (const [k, v] of Object.entries(currentStep.variables)) {
      const isChanged = changedSet.has(k);

      if (v === null || typeof v === 'number' || typeof v === 'string' || typeof v === 'boolean') {
        primitives.push({ key: k, value: v, isChanged });
      } else if (Array.isArray(v)) {
        arrays.push({ key: k, value: v, isChanged });
      } else if (typeof v === 'object') {
        if (v.__type__ === 'ListNode' || v.__type__ === 'TreeNode') {
          objects.push({ key: k, value: v, isChanged });
        } else {
          maps.push({ key: k, value: v, isChanged });
        }
      } else {
        primitives.push({ key: k, value: String(v), isChanged });
      }
    }

    return { primitives, arrays, maps, objects };
  }, [currentStep]);

  // Pointers that point into arrays (e.g. i=2, anchor=0)
  const arrayPointers = useMemo(() => {
    if (!currentStep || !currentStep.variables) return {} as Record<string, { varName: string; index: number }[]>;
    const pointersMap: Record<string, { varName: string; index: number }[]> = {};

    for (const arr of categorizedVars.arrays) {
      pointersMap[arr.key] = [];
      for (const prim of categorizedVars.primitives) {
        if (typeof prim.value === 'number' && prim.value >= 0 && prim.value < arr.value.length) {
          pointersMap[arr.key].push({ varName: prim.key, index: prim.value });
        }
      }
    }
    return pointersMap;
  }, [currentStep, categorizedVars]);

  if (loadingDetail) {
    return (
      <div className="min-h-screen bg-bg flex items-center justify-center text-text font-mono">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-accent border-t-transparent rounded-full animate-spin"></div>
          <div className="text-xs text-text-muted">Loading visual debugger...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bg text-text flex flex-col font-sans selection:bg-accent/25 selection:text-text">
      {/* ===================================================================== */}
      {/* TOP HEADER: Breadcrumbs, Problem Title, Back to Solver               */}
      {/* ===================================================================== */}
      <header className="sticky top-0 z-40 bg-surface border-b border-border px-4 py-2.5 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate(`/practice/${problemSlug || questionDetail?.slug || questionDetail?.id}`)}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium text-text-muted hover:text-text hover:bg-surface-hover border border-border transition-colors cursor-pointer"
            title="Return to problem description and editor"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Solver</span>
          </button>

          <span className="text-border">|</span>

          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 text-xs font-mono font-semibold text-accent">
              <Bug className="w-4 h-4" />
              <span>Visual Debugger</span>
            </div>
            <span className="text-text-muted text-xs">/</span>
            <span className="text-xs font-medium text-text truncate max-w-[260px] sm:max-w-md">
              {questionDetail?.title || problemSlug}
            </span>
            {questionDetail?.difficulty && (
              <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full ${
                questionDetail.difficulty === 'Easy'
                  ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/30'
                  : questionDetail.difficulty === 'Medium'
                  ? 'bg-amber-500/10 text-amber-500 border border-amber-500/30'
                  : 'bg-rose-500/10 text-rose-500 border border-rose-500/30'
              }`}>
                {questionDetail.difficulty}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="px-2 py-0.5 rounded bg-bg border border-border text-[11px] font-mono text-text-muted uppercase">
            {selectedLang}
          </span>
          <button
            type="button"
            onClick={() => {
              navigator.clipboard.writeText(code);
              setCopiedCode(true);
              setTimeout(() => setCopiedCode(false), 2000);
            }}
            className="p-1.5 rounded hover:bg-surface-hover border border-border text-text-muted hover:text-text transition-colors cursor-pointer"
            title="Copy Code"
          >
            {copiedCode ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
        </div>
      </header>

      {/* ===================================================================== */}
      {/* PLAYBACK & TESTCASE CONTROL TOOLBAR                                    */}
      {/* ===================================================================== */}
      <div className="bg-surface/80 backdrop-blur-xs border-b border-border px-4 py-2.5 flex flex-wrap items-center justify-between gap-3">
        {/* Left: Testcase Selectors */}
        <div className="flex items-center gap-1.5 overflow-x-auto">
          <span className="text-xs text-text-muted font-medium mr-1 flex items-center gap-1">
            <Terminal className="w-3.5 h-3.5" />
            <span>Input:</span>
          </span>
          {testCases.map((tc, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => {
                setIsCustomCase(false);
                setActiveCaseTab(idx);
              }}
              className={`px-2.5 py-1 rounded text-xs font-mono transition-all cursor-pointer ${
                !isCustomCase && activeCaseTab === idx
                  ? 'bg-accent text-accent-contrast font-bold shadow-xs'
                  : 'bg-bg text-text-muted hover:text-text border border-border'
              }`}
            >
              Case {idx + 1}
            </button>
          ))}
          <button
            type="button"
            onClick={() => setIsCustomCase(true)}
            className={`px-2.5 py-1 rounded text-xs font-mono transition-all cursor-pointer ${
              isCustomCase
                ? 'bg-accent text-accent-contrast font-bold shadow-xs'
                : 'bg-bg text-text-muted hover:text-text border border-border'
            }`}
          >
            Custom Input
          </button>
        </div>

        {/* Center / Right: Stepping Controls */}
        <div className="flex items-center gap-2">
          {/* First */}
          <button
            type="button"
            disabled={!steps.length || currentStepIndex === 0}
            onClick={handleJumpFirst}
            className="p-1.5 rounded bg-bg hover:bg-surface-hover border border-border text-text-muted hover:text-text transition-colors cursor-pointer disabled:opacity-40"
            title="Jump to first line (Step 1)"
          >
            <SkipBack className="w-3.5 h-3.5" />
          </button>

          {/* Prev */}
          <button
            type="button"
            disabled={!steps.length || currentStepIndex === 0}
            onClick={handleStepPrev}
            className="flex items-center gap-1 px-2.5 py-1 rounded bg-bg hover:bg-surface-hover border border-border text-xs font-medium text-text transition-colors cursor-pointer disabled:opacity-40"
            title="Step back 1 line"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
            <span>Prev</span>
          </button>

          {/* Play / Pause */}
          <button
            type="button"
            disabled={!steps.length}
            onClick={handleTogglePlay}
            className="flex items-center gap-1.5 px-3 py-1 rounded bg-accent hover:bg-accent-hover text-accent-contrast text-xs font-semibold shadow-xs transition-colors cursor-pointer disabled:opacity-40"
            title={isPlaying ? "Pause execution" : "Auto-step execution"}
          >
            {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 fill-current" />}
            <span>{isPlaying ? 'Pause' : 'Play'}</span>
          </button>

          {/* Next */}
          <button
            type="button"
            disabled={!steps.length || currentStepIndex >= steps.length - 1}
            onClick={handleStepNext}
            className="flex items-center gap-1 px-2.5 py-1 rounded bg-bg hover:bg-surface-hover border border-border text-xs font-medium text-text transition-colors cursor-pointer disabled:opacity-40"
            title="Step next line"
          >
            <span>Next</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>

          {/* Last */}
          <button
            type="button"
            disabled={!steps.length || currentStepIndex >= steps.length - 1}
            onClick={handleJumpLast}
            className="p-1.5 rounded bg-bg hover:bg-surface-hover border border-border text-text-muted hover:text-text transition-colors cursor-pointer disabled:opacity-40"
            title="Jump to last line (Return)"
          >
            <SkipForward className="w-3.5 h-3.5" />
          </button>

          {/* Re-run button */}
          <button
            type="button"
            disabled={isTracing}
            onClick={handleStartTrace}
            className="flex items-center gap-1 px-2.5 py-1 rounded bg-surface hover:bg-surface-hover border border-border text-xs text-text-muted hover:text-text transition-colors cursor-pointer disabled:opacity-50"
            title="Re-run debug trace"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${isTracing ? 'animate-spin' : ''}`} />
            <span>Re-run</span>
          </button>

          {/* Playback speed toggle */}
          <select
            value={playbackSpeed}
            onChange={(e) => setPlaybackSpeed(Number(e.target.value))}
            className="px-2 py-1 rounded bg-bg border border-border text-xs font-mono text-text-muted focus:outline-none cursor-pointer"
            title="Playback speed"
          >
            <option value={1000}>0.5x</option>
            <option value={600}>1x</option>
            <option value={250}>2x</option>
          </select>
        </div>
      </div>

      {/* Custom Input Editor Bar (if custom input tab is active) */}
      {isCustomCase && (
        <div className="bg-bg border-b border-border px-4 py-2 flex items-center gap-3">
          <span className="text-xs text-text-muted font-mono whitespace-nowrap">Custom Case Input:</span>
          <input
            type="text"
            value={customInput}
            onChange={(e) => setCustomInput(e.target.value)}
            placeholder="e.g. [1, 3, 5, 4, 7] or 2, 4"
            className="flex-1 px-3 py-1 rounded bg-surface border border-border text-xs font-mono text-text focus:outline-none focus:border-accent"
          />
          <button
            type="button"
            onClick={handleStartTrace}
            disabled={isTracing}
            className="px-3 py-1 rounded bg-accent text-accent-contrast text-xs font-medium cursor-pointer shadow-xs"
          >
            Trace Input
          </button>
        </div>
      )}

      {/* Progress timeline scrubber */}
      <div className="bg-surface/50 border-b border-border px-4 py-1.5 flex items-center justify-between gap-4 text-xs">
        <div className="flex items-center gap-2 font-mono text-xs">
          <span className="font-bold text-accent">
            Step {steps.length ? currentStepIndex + 1 : 0}
          </span>
          <span className="text-text-muted">/ {steps.length}</span>
          {currentStep && (
            <span className="text-text-muted">
              (Line {currentStep.line} • <span className="text-accent">{currentStep.event}</span>)
            </span>
          )}
        </div>

        {/* Timeline Slider */}
        <input
          type="range"
          min={0}
          max={Math.max(0, steps.length - 1)}
          value={currentStepIndex}
          onChange={(e) => {
            setCurrentStepIndex(Number(e.target.value));
            setIsPlaying(false);
          }}
          disabled={!steps.length}
          className="flex-1 max-w-xl accent-accent cursor-pointer"
        />

        {traceResult?.max_steps_reached && (
          <span className="text-[11px] text-amber-500 font-mono">
            ⚠ Max steps limit reached (trace stopped)
          </span>
        )}
      </div>

      {/* ===================================================================== */}
      {/* MAIN TWO-COLUMN SPLIT: Code Stepper (Left) & Live Variables (Right)   */}
      {/* ===================================================================== */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 min-h-0 overflow-hidden">
        {/* =================================================================== */}
        {/* LEFT PANE: Handwritten Code with Real-Time Line Highlight          */}
        {/* =================================================================== */}
        <div className="lg:col-span-7 border-r border-border flex flex-col bg-[#18181b] overflow-hidden h-[calc(100vh-140px)]">
          <div className="px-4 py-2 border-b border-[#27272a] bg-[#141416] flex items-center justify-between text-xs text-[#a1a1aa] font-mono">
            <div className="flex items-center gap-2">
              <Code2 className="w-3.5 h-3.5 text-accent" />
              <span className="text-white font-medium">Source Execution View</span>
            </div>
            <span className="text-[11px] text-[#71717a]">
              Active line executes sequentially
            </span>
          </div>

          <div className="flex-1 overflow-y-auto font-mono text-xs text-[#e4e4e7] p-2 select-text">
            {codeLines.map((lineText, idx) => {
              const lineNum = idx + 1;
              const isActive = currentStep?.line === lineNum;
              const isException = isActive && currentStep?.event === 'exception';

              return (
                <div
                  key={lineNum}
                  ref={el => (codeLinesRef.current[idx] = el)}
                  className={`flex items-start transition-colors rounded px-2 py-0.5 ${
                    isException
                      ? 'bg-rose-500/25 border-l-4 border-rose-500 text-rose-200 font-bold'
                      : isActive
                      ? 'bg-accent/20 border-l-4 border-accent text-white font-bold shadow-xs'
                      : 'hover:bg-white/5 border-l-4 border-transparent'
                  }`}
                >
                  {/* Line Number & Pointer */}
                  <div className="w-12 shrink-0 flex items-center justify-between text-[#71717a] select-none pr-3">
                    <span>{lineNum}</span>
                    {isActive && (
                      <span className="text-accent animate-pulse font-bold text-xs">➔</span>
                    )}
                  </div>

                  {/* Code Line Content */}
                  <div className="flex-1 overflow-x-auto whitespace-pre font-mono leading-relaxed">
                    {lineText || ' '}
                  </div>

                  {/* Inline changed variable badges on active line */}
                  {isActive && currentStep?.changed_vars && currentStep.changed_vars.length > 0 && (
                    <div className="ml-3 shrink-0 flex items-center gap-1.5">
                      {currentStep.changed_vars.map(vName => (
                        <span
                          key={vName}
                          className="px-1.5 py-0.5 rounded bg-accent/25 text-accent border border-accent/40 text-[10px] font-mono shadow-xs animate-fadeIn"
                        >
                          {vName} = {JSON.stringify(currentStep.variables[vName])}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Exception Banner if runtime error */}
          {currentStep?.exception && (
            <div className="p-3 bg-rose-500/15 border-t border-rose-500/30 text-rose-400 font-mono text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />
              <span>{currentStep.exception}</span>
            </div>
          )}
        </div>

        {/* =================================================================== */}
        {/* RIGHT PANE: Live Variables, Arrays, Pointers & Call Stack           */}
        {/* =================================================================== */}
        <div className="lg:col-span-5 flex flex-col bg-surface overflow-y-auto h-[calc(100vh-140px)] p-4 space-y-4">
          {/* Error notice if trace failed */}
          {traceResult?.status === 'ERROR' && (
            <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-500 text-xs font-mono space-y-1">
              <div className="font-bold flex items-center gap-1.5">
                <AlertCircle className="w-4 h-4" />
                <span>Execution Error</span>
              </div>
              <p className="whitespace-pre-wrap">{traceResult.error}</p>
            </div>
          )}

          {/* SECTION 1: ARRAYS & LISTS VISUALIZER */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-text-muted font-mono">
              <div className="flex items-center gap-1.5 font-semibold text-text">
                <Database className="w-3.5 h-3.5 text-accent" />
                <span>Arrays & Sequences</span>
              </div>
              <span className="text-[11px] text-text-muted">Interactive memory cells</span>
            </div>

            {categorizedVars.arrays.length === 0 ? (
              <div className="p-4 rounded-xl bg-bg border border-border text-center text-xs text-text-muted font-mono">
                No active arrays in scope at this line
              </div>
            ) : (
              categorizedVars.arrays.map(arr => {
                const pointers = arrayPointers[arr.key] || [];

                return (
                  <div
                    key={arr.key}
                    className={`p-3.5 rounded-xl bg-bg border transition-all ${
                      arr.isChanged
                        ? 'border-accent shadow-xs ring-1 ring-accent/30'
                        : 'border-border'
                    }`}
                  >
                    <div className="flex items-center justify-between text-xs font-mono mb-2">
                      <span className="font-bold text-accent">{arr.key}</span>
                      <span className="text-[11px] text-text-muted">length: {arr.value.length}</span>
                    </div>

                    {/* Array Cells with Pointer Markers */}
                    <div className="overflow-x-auto pb-1">
                      <div className="flex items-end gap-1.5 min-w-max">
                        {arr.value.map((cellVal, idx) => {
                          const activePointers = pointers.filter(p => p.index === idx);

                          return (
                            <div key={idx} className="flex flex-col items-center">
                              {/* Pointer label if i or j points here */}
                              <div className="h-4 flex items-center justify-center text-[10px] font-mono text-accent font-bold">
                                {activePointers.map(p => p.varName).join(', ')}
                              </div>

                              {/* Pointer arrow */}
                              <div className="text-[10px] text-accent leading-none">
                                {activePointers.length > 0 ? '▼' : ' '}
                              </div>

                              {/* Cell Box */}
                              <div
                                className={`w-9 h-9 rounded-lg border flex items-center justify-center font-mono text-xs font-semibold shadow-xs transition-colors ${
                                  activePointers.length > 0
                                    ? 'bg-accent/20 border-accent text-accent'
                                    : 'bg-surface border-border text-text'
                                }`}
                              >
                                {String(cellVal)}
                              </div>

                              {/* Cell Index */}
                              <span className="text-[9px] font-mono text-text-muted/60 mt-1">
                                [{idx}]
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* SECTION 2: SCALAR VARIABLES (Primitives) */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-text-muted font-mono">
              <div className="flex items-center gap-1.5 font-semibold text-text">
                <Variable className="w-3.5 h-3.5 text-accent" />
                <span>Local Variables</span>
              </div>
              <span className="text-[11px] text-text-muted">Values & state mutations</span>
            </div>

            {categorizedVars.primitives.length === 0 ? (
              <div className="p-4 rounded-xl bg-bg border border-border text-center text-xs text-text-muted font-mono">
                No local variables declared yet
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {categorizedVars.primitives.map(prim => (
                  <div
                    key={prim.key}
                    className={`p-2.5 rounded-lg border transition-all ${
                      prim.isChanged
                        ? 'bg-accent/15 border-accent shadow-xs ring-1 ring-accent/40'
                        : 'bg-bg border-border'
                    }`}
                  >
                    <div className="text-[10px] font-mono text-text-muted flex items-center justify-between">
                      <span className="truncate">{prim.key}</span>
                      {prim.isChanged && (
                        <span className="text-[9px] text-accent font-bold uppercase">Updated</span>
                      )}
                    </div>
                    <div className="text-sm font-bold font-mono text-text truncate mt-0.5">
                      {String(prim.value)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* SECTION 3: COMPLEX OBJECTS (LinkedLists / HashMaps) */}
          {categorizedVars.objects.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-text font-mono">
                <Layers className="w-3.5 h-3.5 text-accent" />
                <span>Data Structures (Nodes)</span>
              </div>
              {categorizedVars.objects.map(obj => (
                <div key={obj.key} className="p-3 rounded-xl bg-bg border border-border space-y-1.5 font-mono text-xs">
                  <div className="font-bold text-accent">{obj.key} ({obj.value.__type__})</div>
                  {obj.value.nodes && (
                    <div className="flex items-center gap-1 text-xs text-text">
                      {obj.value.nodes.map((nVal: any, nIdx: number) => (
                        <React.Fragment key={nIdx}>
                          <span className="px-2 py-1 rounded bg-surface border border-border font-bold">{nVal}</span>
                          {nIdx < obj.value.nodes.length - 1 && <span className="text-accent font-bold">➔</span>}
                        </React.Fragment>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* SECTION 4: CALL STACK & ACTIVE FUNCTION */}
          <div className="space-y-2">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-text font-mono">
              <Layers className="w-3.5 h-3.5 text-accent" />
              <span>Call Stack & Frame</span>
            </div>
            <div className="p-3 rounded-xl bg-bg border border-border font-mono text-xs space-y-1">
              {currentStep?.call_stack && currentStep.call_stack.length > 0 ? (
                currentStep.call_stack.map((frame, fIdx) => (
                  <div key={fIdx} className="flex items-center gap-2 text-text-muted">
                    <span className="text-accent text-[11px] font-bold">#{fIdx}</span>
                    <span className="text-text">{frame}</span>
                  </div>
                ))
              ) : (
                <div className="text-text-muted text-xs">Global Execution Scope</div>
              )}
            </div>
          </div>

          {/* SECTION 5: RETURN VALUE & STANDARD OUTPUT */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-text-muted font-mono">
              <div className="flex items-center gap-1.5 font-semibold text-text">
                <Terminal className="w-3.5 h-3.5 text-accent" />
                <span>Execution Output & Return</span>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-bg border border-border font-mono text-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-text-muted text-[11px]">Final Return:</span>
                <span className="font-bold text-emerald-500">
                  {traceResult?.return_value !== undefined ? JSON.stringify(traceResult.return_value) : 'Pending...'}
                </span>
              </div>
              {currentStep?.stdout && (
                <div className="pt-2 border-t border-border">
                  <span className="text-text-muted text-[10px] block mb-1">Standard Output:</span>
                  <pre className="p-2 rounded bg-surface text-text text-[11px] overflow-x-auto whitespace-pre-wrap">
                    {currentStep.stdout}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
