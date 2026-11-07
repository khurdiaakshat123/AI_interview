import React, { useState, useEffect } from 'react';
import { 
  X, Clock, Sparkles, Layers, Code2, BookOpen, 
  Plus, Trash2, Check, Copy, ArrowRight, Share2, 
  HelpCircle, AlertCircle, Shuffle, ShieldCheck
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { api } from '../../services/api';
import { CustomSessionMetadata, CustomPracticeSessionData } from '../../types';

interface TimedPracticeConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialType?: 'mcq' | 'dsa' | 'both' | 'hybrid';
  initialTopic?: string;
}

interface SectionDraft {
  id: string;
  name: string;
  section_type: 'mcq' | 'dsa';
  topic: string;
  difficulty: string;
  count: number;
  pickMode: 'random' | 'specific';
  specific_ids: string;
}

export const TimedPracticeConfigModal: React.FC<TimedPracticeConfigModalProps> = ({
  isOpen,
  onClose,
  initialType = 'both',
  initialTopic
}) => {
  const navigate = useNavigate();

  // Selected Question Types: Both can be enabled simultaneously (no separate "hybrid" option!)
  const [includeMcq, setIncludeMcq] = useState<boolean>(initialType !== 'dsa');
  const [includeDsa, setIncludeDsa] = useState<boolean>(initialType !== 'mcq');

  const [title, setTitle] = useState<string>('Custom Timed Practice Assessment');
  const [durationMinutes, setDurationMinutes] = useState<number>(30);
  const [isCustomDuration, setIsCustomDuration] = useState<boolean>(false);

  // Metadata for dropdowns
  const [metadata, setMetadata] = useState<CustomSessionMetadata | null>(null);
  const [loadingMeta, setLoadingMeta] = useState<boolean>(true);

  // Dynamic Sections
  const [sections, setSections] = useState<SectionDraft[]>([]);

  // Preparation & Result State
  const [isPreparing, setIsPreparing] = useState<boolean>(false);
  const [preparedSession, setPreparedSession] = useState<CustomPracticeSessionData | null>(null);
  const [copiedLink, setCopiedLink] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Fetch metadata on mount
  useEffect(() => {
    if (!isOpen) return;

    let isMounted = true;
    api.getCustomSessionMetadata()
      .then(res => {
        if (isMounted) {
          setMetadata(res);
          setLoadingMeta(false);
        }
      })
      .catch(err => {
        console.error('Failed to load practice metadata:', err);
        if (isMounted) setLoadingMeta(false);
      });

    return () => { isMounted = false; };
  }, [isOpen]);

  // Re-initialize sections when selected types change
  useEffect(() => {
    if (includeMcq && includeDsa) {
      setTitle('Technical Assessment (MCQ & DSA)');
      setSections([
        {
          id: 'sec_1',
          name: 'Section 1: Multiple Choice Questions',
          section_type: 'mcq',
          topic: 'all',
          difficulty: 'all',
          count: 10,
          pickMode: 'random',
          specific_ids: ''
        },
        {
          id: 'sec_2',
          name: 'Section 2: Coding & DSA Problems',
          section_type: 'dsa',
          topic: 'all',
          difficulty: 'Medium',
          count: 2,
          pickMode: 'random',
          specific_ids: ''
        }
      ]);
    } else if (includeMcq) {
      setTitle('Multiple Choice Speed & Accuracy Assessment');
      setSections([
        {
          id: 'sec_1',
          name: 'Core Technical MCQs',
          section_type: 'mcq',
          topic: initialTopic || 'all',
          difficulty: 'all',
          count: 10,
          pickMode: 'random',
          specific_ids: ''
        }
      ]);
    } else {
      setTitle('Algorithmic Problem Solving Assessment');
      setSections([
        {
          id: 'sec_1',
          name: 'DSA Problem Solving',
          section_type: 'dsa',
          topic: initialTopic || 'all',
          difficulty: 'Medium',
          count: 2,
          pickMode: 'random',
          specific_ids: ''
        }
      ]);
    }
    setPreparedSession(null);
    setErrorMsg(null);
  }, [includeMcq, includeDsa, initialTopic]);

  if (!isOpen) return null;

  // Add Section Handler
  const handleAddSection = () => {
    const nextIdx = sections.length + 1;
    // Default type based on active selection
    let defaultType: 'mcq' | 'dsa' = 'mcq';
    if (!includeMcq && includeDsa) defaultType = 'dsa';
    else if (includeMcq && includeDsa) defaultType = nextIdx % 2 === 1 ? 'mcq' : 'dsa';

    setSections(prev => [
      ...prev,
      {
        id: `sec_${Date.now()}`,
        name: `Section ${nextIdx}: ${defaultType === 'mcq' ? 'MCQ Focus' : 'Coding Focus'}`,
        section_type: defaultType,
        topic: 'all',
        difficulty: defaultType === 'mcq' ? 'all' : 'Medium',
        count: defaultType === 'mcq' ? 5 : 1,
        pickMode: 'random',
        specific_ids: ''
      }
    ]);
  };

  const handleRemoveSection = (id: string) => {
    if (sections.length <= 1) return;
    setSections(prev => prev.filter(s => s.id !== id));
  };

  const updateSection = (id: string, updates: Partial<SectionDraft>) => {
    setSections(prev => prev.map(s => s.id === id ? { ...s, ...updates } : s));
  };

  // Total questions count calculation
  const totalQuestions = sections.reduce((sum, s) => {
    if (s.pickMode === 'specific' && s.specific_ids.trim()) {
      const ids = s.specific_ids.split(',').map(x => x.trim()).filter(Boolean);
      return sum + (ids.length > 0 ? ids.length : s.count);
    }
    return sum + (s.count || 1);
  }, 0);

  // Submit & Prepare Session
  const handlePrepareSession = async () => {
    setIsPreparing(true);
    setErrorMsg(null);

    try {
      const sessionType: 'mcq' | 'dsa' | 'hybrid' = includeMcq && includeDsa ? 'hybrid' : (includeMcq ? 'mcq' : 'dsa');
      const payload = {
        title: title.trim() || 'Custom Timed Practice',
        session_type: sessionType,
        duration_minutes: durationMinutes,
        marking_scheme: {
          mcq_correct: 1.0,
          mcq_negative: -0.25,
          coding_weight: 10.0
        },
        sections: sections.map((s, idx) => ({
          id: s.id || `sec_${idx + 1}`,
          name: s.name.trim() || `Section ${idx + 1}`,
          section_type: s.section_type,
          topic: s.topic,
          difficulty: s.difficulty,
          count: s.count,
          specific_question_ids: s.pickMode === 'specific' && s.specific_ids.trim()
            ? s.specific_ids.split(',').map(x => x.trim()).filter(Boolean)
            : undefined
        }))
      };

      const res = await api.prepareCustomSession(payload);
      setPreparedSession(res);
    } catch (err: any) {
      console.error('Failed to prepare session:', err);
      setErrorMsg(err.message || 'Failed to prepare custom practice session. Please try again.');
    } finally {
      setIsPreparing(false);
    }
  };

  const fullShareUrl = preparedSession 
    ? `${window.location.origin}${preparedSession.share_url}`
    : '';

  const handleCopyLink = () => {
    if (!fullShareUrl) return;
    navigator.clipboard.writeText(fullShareUrl);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2500);
  };

  const handleProceedToTest = () => {
    if (!preparedSession) return;
    onClose();
    navigate(preparedSession.share_url);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-xs flex items-center justify-center p-3 sm:p-5 overflow-y-auto">
      <div className="bg-surface border border-border rounded-2xl max-w-3xl w-full max-h-[92vh] flex flex-col shadow-2xl animate-in fade-in zoom-in-95 duration-150 overflow-hidden">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between shrink-0 bg-surface/80">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center text-accent">
              <Clock className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-text">Timed Practice & Assessment Studio</h2>
              <p className="text-xs text-text-muted">Select MCQ, DSA, or both questions with custom topic and difficulty quotas</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-text-muted hover:text-text hover:bg-surface-hover transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">

          {/* Question Types: Direct MCQ and DSA Selection (No separate "Hybrid" tab!) */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-xs font-mono font-medium text-text-muted uppercase tracking-wider">
                Select Question Types (Choose MCQ, DSA, or Both)
              </label>
              <span className="text-[11px] font-mono text-accent font-semibold">
                {includeMcq && includeDsa ? 'Both MCQ & DSA Selected' : includeMcq ? 'MCQ Only Selected' : 'DSA Only Selected'}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {/* MCQ Toggle Card */}
              <div
                onClick={() => {
                  if (includeMcq && !includeDsa) return; // Must have at least one active
                  setIncludeMcq(!includeMcq);
                }}
                className={`p-3.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between select-none ${
                  includeMcq
                    ? 'bg-blue-500/10 border-blue-500/50 text-text shadow-xs ring-1 ring-blue-500/30'
                    : 'bg-surface border-border hover:bg-surface-hover text-text-muted opacity-60'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-9 h-9 rounded-lg flex items-center justify-center font-bold text-xs ${
                    includeMcq ? 'bg-blue-500 text-white' : 'bg-bg border border-border text-text-muted'
                  }`}>
                    <BookOpen className="w-4 h-4" />
                  </div>
                  <div>
                    <span className="font-semibold text-xs text-text block">Multiple Choice (MCQ)</span>
                    <span className="text-[11px] text-text-muted font-mono">1,500 questions across 9 domains (+1 / -0.25)</span>
                  </div>
                </div>
                <div className={`w-5 h-5 rounded-md flex items-center justify-center border transition-colors ${
                  includeMcq ? 'bg-blue-500 border-blue-500 text-white' : 'bg-bg border-border'
                }`}>
                  {includeMcq && <Check className="w-3.5 h-3.5" />}
                </div>
              </div>

              {/* DSA Toggle Card */}
              <div
                onClick={() => {
                  if (includeDsa && !includeMcq) return; // Must have at least one active
                  setIncludeDsa(!includeDsa);
                }}
                className={`p-3.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between select-none ${
                  includeDsa
                    ? 'bg-amber-500/10 border-amber-500/50 text-text shadow-xs ring-1 ring-amber-500/30'
                    : 'bg-surface border-border hover:bg-surface-hover text-text-muted opacity-60'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-9 h-9 rounded-lg flex items-center justify-center font-bold text-xs ${
                    includeDsa ? 'bg-amber-500 text-white' : 'bg-bg border border-border text-text-muted'
                  }`}>
                    <Code2 className="w-4 h-4" />
                  </div>
                  <div>
                    <span className="font-semibold text-xs text-text block">Coding & DSA Problems</span>
                    <span className="text-[11px] text-text-muted font-mono">3,269 algorithmic & SQL questions</span>
                  </div>
                </div>
                <div className={`w-5 h-5 rounded-md flex items-center justify-center border transition-colors ${
                  includeDsa ? 'bg-amber-500 border-amber-500 text-white' : 'bg-bg border-border'
                }`}>
                  {includeDsa && <Check className="w-3.5 h-3.5" />}
                </div>
              </div>
            </div>
          </div>

          {/* Assessment Title & Duration */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-mono font-medium text-text-muted mb-1.5 uppercase tracking-wider">
                Assessment Title
              </label>
              <input
                type="text"
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder="e.g. Operating Systems & Algorithms Speedrun"
                className="w-full px-3 py-2 rounded-xl bg-bg border border-border text-xs text-text focus:outline-none focus:border-border-focus font-sans"
              />
            </div>

            <div>
              <label className="block text-xs font-mono font-medium text-text-muted mb-1.5 uppercase tracking-wider">
                Total Duration
              </label>
              <div className="flex items-center gap-2">
                {[15, 30, 45, 60].map(mins => (
                  <button
                    key={mins}
                    type="button"
                    onClick={() => {
                      setDurationMinutes(mins);
                      setIsCustomDuration(false);
                    }}
                    className={`flex-1 py-2 rounded-xl text-xs font-mono font-medium border transition-colors cursor-pointer ${
                      !isCustomDuration && durationMinutes === mins
                        ? 'bg-accent/15 text-accent border-accent'
                        : 'bg-bg text-text-muted border-border hover:text-text'
                    }`}
                  >
                    {mins}m
                  </button>
                ))}
                <button
                  type="button"
                  onClick={() => setIsCustomDuration(true)}
                  className={`px-3 py-2 rounded-xl text-xs font-mono font-medium border transition-colors cursor-pointer ${
                    isCustomDuration
                      ? 'bg-accent/15 text-accent border-accent'
                      : 'bg-bg text-text-muted border-border hover:text-text'
                  }`}
                >
                  Custom
                </button>
              </div>
              {isCustomDuration && (
                <div className="mt-2 flex items-center gap-2">
                  <input
                    type="number"
                    min={5}
                    max={240}
                    value={durationMinutes}
                    onChange={e => setDurationMinutes(Math.max(5, Math.min(240, parseInt(e.target.value) || 30)))}
                    className="w-24 px-3 py-1.5 rounded-lg bg-bg border border-border text-xs text-text font-mono"
                  />
                  <span className="text-xs text-text-muted font-mono">minutes (5 - 240 mins)</span>
                </div>
              )}
            </div>
          </div>

          {/* Marking Format Card */}
          <div className="p-3.5 rounded-xl bg-bg border border-border/80 flex items-start gap-3">
            <div className="p-1 rounded-md bg-accent/10 text-accent mt-0.5">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div className="text-xs space-y-0.5">
              <span className="font-semibold text-text">Standard Marking Scheme Active</span>
              <p className="text-text-muted">
                {includeMcq && includeDsa ? (
                  <>MCQ: <strong className="text-emerald-500 font-mono">+1.00</strong> for correct, <strong className="text-rose-500 font-mono">-0.25</strong> negative penalty for incorrect. DSA: Automated test cases (10.0 pts each).</>
                ) : includeMcq ? (
                  <>Multiple Choice features <strong className="text-emerald-500 font-mono">+1.00</strong> for correct answers and <strong className="text-rose-500 font-mono">-0.25</strong> negative penalty for incorrect answers.</>
                ) : (
                  <>Coding questions evaluate accuracy across automated test cases (10.0 pts each).</>
                )}
              </p>
            </div>
          </div>

          {/* Section & Permutation Builder */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-text">Section Configurations</h3>
                <p className="text-xs text-text-muted">Set independent topics, difficulties, and question quotas</p>
              </div>
              <button
                type="button"
                onClick={handleAddSection}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent/10 border border-accent/20 text-accent text-xs font-medium hover:bg-accent/20 transition-colors cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Section</span>
              </button>
            </div>

            <div className="space-y-3">
              {sections.map((sec, idx) => (
                <div key={sec.id} className="p-4 rounded-xl bg-bg border border-border space-y-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2 flex-1">
                      <span className="w-5 h-5 rounded-full bg-surface border border-border text-[11px] font-mono font-bold flex items-center justify-center text-text-muted">
                        {idx + 1}
                      </span>
                      <input
                        type="text"
                        value={sec.name}
                        onChange={e => updateSection(sec.id, { name: e.target.value })}
                        className="px-2.5 py-1 rounded-lg bg-surface border border-border text-xs font-semibold text-text focus:outline-none focus:border-border-focus flex-1 max-w-xs"
                      />
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase font-bold tracking-wider ${
                        sec.section_type === 'mcq'
                          ? 'bg-blue-500/10 text-blue-500 border border-blue-500/20'
                          : 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
                      }`}>
                        {sec.section_type.toUpperCase()}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      {/* Section Type Switcher (only if both MCQ and DSA are active) */}
                      {includeMcq && includeDsa && (
                        <select
                          value={sec.section_type}
                          onChange={e => updateSection(sec.id, { 
                            section_type: e.target.value as 'mcq' | 'dsa',
                            difficulty: e.target.value === 'mcq' ? 'all' : 'Medium',
                            topic: 'all',
                            count: e.target.value === 'mcq' ? 5 : 2
                          })}
                          className="px-2 py-1 rounded bg-surface border border-border text-xs text-text font-mono cursor-pointer"
                        >
                          <option value="mcq">MCQ Section</option>
                          <option value="dsa">DSA Section</option>
                        </select>
                      )}

                      {sections.length > 1 && (
                        <button
                          type="button"
                          onClick={() => handleRemoveSection(sec.id)}
                          className="p-1 rounded text-text-muted hover:text-rose-500 hover:bg-surface transition-colors cursor-pointer"
                          title="Remove Section"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Section Controls: Topic, Difficulty, Count */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {/* Topic Selector */}
                    <div>
                      <label className="block text-[11px] font-mono text-text-muted mb-1">Topic</label>
                      <select
                        value={sec.topic}
                        onChange={e => updateSection(sec.id, { topic: e.target.value })}
                        className="w-full px-2.5 py-1.5 rounded-lg bg-surface border border-border text-xs text-text focus:outline-none focus:border-border-focus cursor-pointer"
                      >
                        <option value="all">All Topics ({sec.section_type === 'mcq' ? 'All 9 Core Domains' : 'All 24 DSA Topics'})</option>
                        {sec.section_type === 'mcq' ? (
                          (metadata?.mcq_topics || []).map(t => (
                            <option key={t.id} value={t.id}>{t.name} ({t.count} Qs)</option>
                          ))
                        ) : (
                          (metadata?.dsa_topics || []).map(t => (
                            <option key={t.id} value={t.id}>{t.name}</option>
                          ))
                        )}
                      </select>
                    </div>

                    {/* Difficulty Selector */}
                    <div>
                      <label className="block text-[11px] font-mono text-text-muted mb-1">Difficulty</label>
                      <select
                        value={sec.difficulty}
                        onChange={e => updateSection(sec.id, { difficulty: e.target.value })}
                        className="w-full px-2.5 py-1.5 rounded-lg bg-surface border border-border text-xs text-text focus:outline-none focus:border-border-focus cursor-pointer"
                      >
                        <option value="all">All / Mixed Difficulties</option>
                        <option value="Easy">Easy Only</option>
                        <option value="Medium">Medium Only</option>
                        <option value="Hard">Hard Only</option>
                      </select>
                    </div>

                    {/* Count Stepper */}
                    <div>
                      <label className="block text-[11px] font-mono text-text-muted mb-1">
                        Number of Questions
                      </label>
                      <div className="flex items-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => updateSection(sec.id, { count: Math.max(1, sec.count - 1) })}
                          className="w-8 h-8 rounded-lg bg-surface border border-border text-text font-mono font-bold hover:bg-surface-hover flex items-center justify-center cursor-pointer"
                        >
                          -
                        </button>
                        <input
                          type="number"
                          min={1}
                          max={50}
                          value={sec.count}
                          onChange={e => updateSection(sec.id, { count: Math.max(1, Math.min(50, parseInt(e.target.value) || 1)) })}
                          className="flex-1 px-2 py-1.5 rounded-lg bg-surface border border-border text-xs text-text font-mono text-center"
                        />
                        <button
                          type="button"
                          onClick={() => updateSection(sec.id, { count: Math.min(50, sec.count + 1) })}
                          className="w-8 h-8 rounded-lg bg-surface border border-border text-text font-mono font-bold hover:bg-surface-hover flex items-center justify-center cursor-pointer"
                        >
                          +
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Pick Mode: Random vs Specific Question Numbers */}
                  <div className="pt-1 flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-t border-border/50">
                    <div className="flex items-center gap-3">
                      <label className="flex items-center gap-1.5 text-xs text-text-muted cursor-pointer">
                        <input
                          type="radio"
                          name={`pickMode_${sec.id}`}
                          checked={sec.pickMode === 'random'}
                          onChange={() => updateSection(sec.id, { pickMode: 'random' })}
                          className="text-accent cursor-pointer"
                        />
                        <span>Random with filters</span>
                      </label>

                      <label className="flex items-center gap-1.5 text-xs text-text-muted cursor-pointer">
                        <input
                          type="radio"
                          name={`pickMode_${sec.id}`}
                          checked={sec.pickMode === 'specific'}
                          onChange={() => updateSection(sec.id, { pickMode: 'specific' })}
                          className="text-accent cursor-pointer"
                        />
                        <span>Specific Question # or IDs</span>
                      </label>
                    </div>

                    {sec.pickMode === 'specific' && (
                      <div className="flex-1 max-w-sm">
                        <input
                          type="text"
                          value={sec.specific_ids}
                          onChange={e => updateSection(sec.id, { specific_ids: e.target.value })}
                          placeholder={sec.section_type === 'dsa' ? "Enter question # e.g. 1, 2, 15, 206" : "Enter IDs e.g. mcq_os_1, mcq_dbms_12"}
                          className="w-full px-2.5 py-1 rounded-md bg-surface border border-border text-xs text-text font-mono placeholder:text-text-muted/60"
                        />
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Prepared Session Success Box (Share URL) */}
          {preparedSession && (
            <div className="p-4 rounded-xl bg-accent/10 border border-accent/30 space-y-3 animate-in fade-in duration-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Check className="w-5 h-5 text-emerald-500" />
                  <span className="font-semibold text-text text-sm">Practice Session Prepared & Ready!</span>
                </div>
                <span className="text-xs font-mono text-accent font-medium">ID: {preparedSession.id}</span>
              </div>

              <p className="text-xs text-text-muted">
                Your assessment has been compiled with <strong>{preparedSession.total_questions} questions</strong> across {preparedSession.sections.length} sections ({preparedSession.duration_minutes} minutes allowed).
              </p>

              {/* Share URL Input & Copy Button */}
              <div className="flex items-center gap-2">
                <div className="flex-1 px-3 py-2 rounded-lg bg-bg border border-border text-xs font-mono text-text truncate select-all">
                  {fullShareUrl}
                </div>
                <button
                  type="button"
                  onClick={handleCopyLink}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-accent text-accent-contrast text-xs font-medium hover:bg-accent-hover transition-colors shrink-0 cursor-pointer"
                >
                  {copiedLink ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                  <span>{copiedLink ? 'Link Copied!' : 'Share Practice Link'}</span>
                </button>
              </div>
            </div>
          )}

          {errorMsg && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-500 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 border-t border-border flex items-center justify-between shrink-0 bg-surface/80">
          <div className="flex items-center gap-4 text-xs font-mono text-text-muted">
            <span>Total Qs: <strong className="text-text">{totalQuestions}</strong></span>
            <span>Duration: <strong className="text-text">{durationMinutes}m</strong></span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl border border-border text-text-muted text-xs font-medium hover:text-text hover:bg-surface transition-colors cursor-pointer"
            >
              Cancel
            </button>

            {!preparedSession ? (
              <button
                type="button"
                onClick={handlePrepareSession}
                disabled={isPreparing}
                className="flex items-center gap-2 px-5 py-2 rounded-xl bg-accent text-accent-contrast text-xs font-medium hover:bg-accent-hover transition-colors disabled:opacity-50 cursor-pointer shadow-sm"
              >
                {isPreparing ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Compiling Session...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Prepare Practice Session</span>
                  </>
                )}
              </button>
            ) : (
              <button
                type="button"
                onClick={handleProceedToTest}
                className="flex items-center gap-2 px-6 py-2 rounded-xl bg-emerald-600 text-white text-xs font-semibold hover:bg-emerald-500 transition-colors cursor-pointer shadow-sm animate-pulse"
              >
                <span>Proceed to Assessment</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

      </div>
    </div>
  );
};
