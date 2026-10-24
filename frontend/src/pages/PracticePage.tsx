import React, { useState, useEffect, useCallback, useRef } from 'react';
import { 
  Code2, Database, Search, Star, Filter, RotateCcw, 
  ChevronLeft, ChevronRight, Play, CloudUpload, CheckCircle2, 
  AlertCircle, Clock, BookOpen, Lightbulb, FileText, 
  Layers, ExternalLink, ArrowLeft, Maximize2, Minimize2, 
  Sparkles, Check, Copy, HelpCircle, X, ChevronDown, ListFilter, Shuffle
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { api } from '../services/api';
import { 
  LCQuestionSummary, LCQuestionDetail, LCAnalytics, 
  LCRunResult, LCSubmitResult, LCSubmission 
} from '../types';
import { LCMarkdownViewer } from '../components/LCMarkdownViewer';
import { LCTimer } from '../components/practice/LCTimer';
import { LCAnalyticsCard } from '../components/practice/LCAnalyticsCard';
import Editor, { OnMount } from '@monaco-editor/react';

interface PracticePageProps {
  initialQuestionId?: string;
  onNavigate?: (tab: string, state?: any) => void;
}

const DSA_TOPICS = [
  { slug: 'all', label: 'All DSA Topics' },
  { slug: 'arrays', label: 'Arrays' },
  { slug: 'two-pointers', label: 'Two Pointers' },
  { slug: 'sliding-window', label: 'Sliding Window' },
  { slug: 'hashing', label: 'Hash Table' },
  { slug: 'stacks-queues', label: 'Stack & Queue' },
  { slug: 'linked-lists', label: 'Linked List' },
  { slug: 'binary-search', label: 'Binary Search' },
  { slug: 'trees', label: 'Trees' },
  { slug: 'heaps', label: 'Heap' },
  { slug: 'recursion-backtracking', label: 'Backtracking' },
  { slug: 'dynamic-programming', label: 'Dynamic Programming' },
  { slug: 'graphs', label: 'Graphs' },
  { slug: 'greedy', label: 'Greedy' },
  { slug: 'tries', label: 'Trie' },
  { slug: 'bit-manipulation', label: 'Bit Manipulation' },
  { slug: 'mathematics', label: 'Math' },
  { slug: 'sorting', label: 'Sorting' },
  { slug: 'prefix-sum', label: 'Prefix Sum' },
  { slug: 'divide-and-conquer', label: 'Divide & Conquer' },
  { slug: 'simulation', label: 'Simulation' },
  { slug: 'design', label: 'Design' },
  { slug: 'advanced-data-structures', label: 'Advanced DS' },
  { slug: 'strings', label: 'Strings' },
];

const DB_TOPICS = [
  { slug: 'all', label: 'All SQL Topics' },
  { slug: 'select-filtering', label: 'Select & Filtering' },
  { slug: 'joins', label: 'Joins' },
  { slug: 'aggregation', label: 'Aggregation' },
  { slug: 'window-functions', label: 'Window Functions' },
  { slug: 'date-time', label: 'Date & Time' },
  { slug: 'null-handling', label: 'Null Handling' },
  { slug: 'set-operations', label: 'Set Operations' },
  { slug: 'string-functions', label: 'String Functions' },
];

const DSA_LANGUAGES = [
  { id: 'python3', label: 'Python 3', monacoLang: 'python' },
  { id: 'python', label: 'Python', monacoLang: 'python' },
  { id: 'cpp', label: 'C++', monacoLang: 'cpp' },
  { id: 'java', label: 'Java', monacoLang: 'java' },
  { id: 'javascript', label: 'JavaScript', monacoLang: 'javascript' },
  { id: 'typescript', label: 'TypeScript', monacoLang: 'typescript' },
];

const DB_LANGUAGES = [
  { id: 'mysql', label: 'MySQL', monacoLang: 'sql' },
  { id: 'postgresql', label: 'PostgreSQL', monacoLang: 'sql' },
  { id: 'mssql', label: 'MS SQL Server', monacoLang: 'sql' },
  { id: 'oraclesql', label: 'Oracle SQL', monacoLang: 'sql' },
  { id: 'pythondata', label: 'Pandas', monacoLang: 'python' },
];

export const PracticePage: React.FC<PracticePageProps> = ({ initialQuestionId, onNavigate }) => {
  // Mode: Explorer (list) vs Solver (workspace)
  const [activeQuestionId, setActiveQuestionId] = useState<string | null>(initialQuestionId || null);

  // Explorer State
  const [category, setCategory] = useState<'all' | 'dsa' | 'database'>('all');
  const [selectedSubcategory, setSelectedSubcategory] = useState<string>('all');
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [debouncedSearch, setDebouncedSearch] = useState<string>('');
  const [myListOnly, setMyListOnly] = useState<boolean>(false);
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(50);

  // Data lists
  const [questions, setQuestions] = useState<LCQuestionSummary[]>([]);
  const [totalQuestions, setTotalQuestions] = useState<number>(0);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [loadingList, setLoadingList] = useState<boolean>(true);
  const [analytics, setAnalytics] = useState<LCAnalytics | null>(null);
  const [loadingAnalytics, setLoadingAnalytics] = useState<boolean>(true);

  // Solver State
  const [questionDetail, setQuestionDetail] = useState<LCQuestionDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState<boolean>(false);
  const [solverTab, setSolverTab] = useState<'description' | 'editorial' | 'hints' | 'submissions'>('description');
  const [selectedLang, setSelectedLang] = useState<string>('python3');
  const [code, setCode] = useState<string>('');
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [runResult, setRunResult] = useState<LCRunResult | null>(null);
  const [submitResult, setSubmitResult] = useState<LCSubmitResult | null>(null);
  const [activeCaseTab, setActiveCaseTab] = useState<number>(0);
  const [bottomConsoleTab, setBottomConsoleTab] = useState<'testcase' | 'result'>('testcase');
  const [revealedHints, setRevealedHints] = useState<Record<number, boolean>>({});
  const [viewingSubmissionCode, setViewingSubmissionCode] = useState<LCSubmission | null>(null);
  const [showSqlSchemaModal, setShowSqlSchemaModal] = useState<boolean>(false);
  const [copiedCode, setCopiedCode] = useState<boolean>(false);
  const [editorTheme, setEditorTheme] = useState<string>('vs-dark');

  const editorRef = useRef<any>(null);

  // Search debounce
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setPage(1);
    }, 250);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Load Analytics
  const loadAnalytics = useCallback(async () => {
    try {
      setLoadingAnalytics(true);
      const data = await api.getLCAnalytics();
      setAnalytics(data);
    } catch (e) {
      console.error('Failed to load LC analytics:', e);
    } finally {
      setLoadingAnalytics(false);
    }
  }, []);

  useEffect(() => {
    loadAnalytics();
  }, [loadAnalytics]);

  // Load Questions List
  const loadQuestions = useCallback(async () => {
    try {
      setLoadingList(true);
      const res = await api.getLCQuestions({
        category: category !== 'all' ? category : undefined,
        subcategory: selectedSubcategory !== 'all' ? selectedSubcategory : undefined,
        difficulty: selectedDifficulty !== 'all' ? selectedDifficulty : undefined,
        status: selectedStatus !== 'all' ? selectedStatus : undefined,
        search: debouncedSearch.trim() || undefined,
        my_list_only: myListOnly || undefined,
        page,
        limit: pageSize,
        sort_by: 'id',
        order: 'asc'
      });
      setQuestions(res.questions);
      setTotalQuestions(res.total);
      setTotalPages(res.totalPages);
    } catch (e) {
      console.error('Failed to load LC questions:', e);
    } finally {
      setLoadingList(false);
    }
  }, [category, selectedSubcategory, selectedDifficulty, selectedStatus, debouncedSearch, myListOnly, page, pageSize]);

  useEffect(() => {
    if (!activeQuestionId) {
      loadQuestions();
    }
  }, [loadQuestions, activeQuestionId]);

  // Detect Theme for Monaco
  useEffect(() => {
    const updateTheme = () => {
      const theme = document.documentElement.getAttribute('data-theme');
      setEditorTheme(theme === 'light' ? 'vs-light' : 'vs-dark');
    };
    updateTheme();
    window.addEventListener('intervyn-theme-change', updateTheme);
    return () => window.removeEventListener('intervyn-theme-change', updateTheme);
  }, []);

  // Load Single Question Details for Solver
  const loadQuestionDetail = useCallback(async (idOrSlug: string) => {
    try {
      setLoadingDetail(true);
      setRunResult(null);
      setSubmitResult(null);
      setRevealedHints({});
      setActiveCaseTab(0);
      setBottomConsoleTab('testcase');

      const data = await api.getLCQuestion(idOrSlug);
      setQuestionDetail(data);

      // Default language based on category
      const defaultLang = data.category === 'database' ? 'mysql' : 'python3';
      setSelectedLang(defaultLang);

      // Starter code
      const initialCode = data.starterCode?.[defaultLang] || 
        (data.category === 'database' ? '# Write your MySQL query statement below\n' : '# Write your solution below\n');
      setCode(initialCode);
    } catch (e) {
      console.error('Failed to load question details:', e);
    } finally {
      setLoadingDetail(false);
    }
  }, []);

  useEffect(() => {
    if (activeQuestionId) {
      loadQuestionDetail(activeQuestionId);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, [activeQuestionId, loadQuestionDetail]);

  // Handle Language Change in Solver
  const handleLanguageChange = (lang: string) => {
    setSelectedLang(lang);
    if (questionDetail) {
      const langStarter = questionDetail.starterCode?.[lang];
      if (langStarter) {
        setCode(langStarter);
      }
    }
  };

  // Toggle Star / My List
  const handleToggleStar = async (id: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    try {
      const res = await api.toggleLCStar(id);
      
      // Update list state
      setQuestions(prev => prev.map(q => q.id === id ? { ...q, isStarred: res.isStarred } : q));
      
      // Update solver state
      if (questionDetail && questionDetail.id === id) {
        setQuestionDetail({ ...questionDetail, isStarred: res.isStarred });
      }

      // Refresh analytics
      loadAnalytics();
    } catch (err) {
      console.error('Failed to toggle star:', err);
    }
  };

  // Run Code
  const handleRunCode = async () => {
    if (!questionDetail || isRunning || isSubmitting) return;
    setIsRunning(true);
    setBottomConsoleTab('result');

    try {
      const res = await api.runLCCode(questionDetail.id, code, selectedLang);
      setRunResult(res);
      setSubmitResult(null);
    } catch (e: any) {
      setRunResult({
        status: 'Runtime Error',
        is_correct: false,
        error: e?.message || 'Execution error'
      });
    } finally {
      setIsRunning(false);
    }
  };

  // Submit Code
  const handleSubmitCode = async () => {
    if (!questionDetail || isRunning || isSubmitting) return;
    setIsSubmitting(true);
    setBottomConsoleTab('result');

    try {
      const res = await api.submitLCCode(questionDetail.id, code, selectedLang);
      setSubmitResult(res);
      setRunResult(null);

      if (res.is_correct) {
        confetti({
          particleCount: 100,
          spread: 80,
          origin: { y: 0.6 }
        });

        // Update question status
        setQuestionDetail(prev => prev ? { ...prev, status: 'solved' } : prev);
        setQuestions(prev => prev.map(q => q.id === questionDetail.id ? { ...q, status: 'solved' } : q));
      } else {
        setQuestionDetail(prev => prev ? { ...prev, status: 'attempted' } : prev);
        setQuestions(prev => prev.map(q => q.id === questionDetail.id && q.status !== 'solved' ? { ...q, status: 'attempted' } : q));
      }

      // Refresh submissions
      const subsRes = await api.getLCSubmissions(questionDetail.id);
      setQuestionDetail(prev => prev ? { ...prev, prevSubmissions: subsRes.submissions } : prev);

      // Refresh overall analytics
      loadAnalytics();
    } catch (e: any) {
      setSubmitResult({
        submission_id: 'err',
        status: 'Compilation / Server Error',
        is_correct: false,
        runtime_ms: null,
        memory_mb: null,
        passed_test_cases: 0,
        total_test_cases: 0,
        submitted_at: new Date().toISOString()
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Reset Code
  const handleResetCode = () => {
    if (!questionDetail) return;
    const starter = questionDetail.starterCode?.[selectedLang] || '';
    setCode(starter);
  };

  // Copy Code
  const handleCopyCode = () => {
    navigator.clipboard.writeText(code);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  // Navigate Questions (Prev / Next / Random)
  const handleNavigateRelative = (direction: 'prev' | 'next') => {
    if (!questionDetail) return;
    const currentNum = questionDetail.num;
    const currentIndex = questions.findIndex(q => q.id === questionDetail.id);

    if (currentIndex !== -1) {
      const nextIndex = direction === 'next' ? currentIndex + 1 : currentIndex - 1;
      if (nextIndex >= 0 && nextIndex < questions.length) {
        setActiveQuestionId(questions[nextIndex].id);
        return;
      }
    }

    // Fallback by sequential numerical ID
    const targetNum = direction === 'next' ? currentNum + 1 : Math.max(1, currentNum - 1);
    setActiveQuestionId(String(targetNum));
  };

  const handlePickRandom = async () => {
    if (questions.length > 0) {
      const randomIndex = Math.floor(Math.random() * questions.length);
      setActiveQuestionId(questions[randomIndex].id);
    } else {
      setActiveQuestionId(String(Math.floor(Math.random() * 3269) + 1));
    }
  };

  // Helpers for topic lists
  const currentTopics = category === 'database' ? DB_TOPICS : DSA_TOPICS;

  // Monaco on mount
  const handleEditorMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;
  };

  // =========================================================================
  // VIEW 1: LEETCODE QUESTION EXPLORER / CATALOG
  // =========================================================================
  if (!activeQuestionId) {
    return (
      <div className="min-h-screen bg-bg text-text pb-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 space-y-6">
          {/* Header Title & Breadcrumb */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-border">
            <div>
              <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-accent mb-1">
                <Code2 className="w-3.5 h-3.5" />
                <span>Interview Practice Bank</span>
              </div>
              <h1 className="text-2xl sm:text-3xl font-serif text-text tracking-tight">
                Problems
              </h1>
              <p className="text-xs sm:text-[13px] text-text-muted mt-0.5">
                Practice 3,269 official algorithmic and database questions with real-time test execution.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handlePickRandom}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-surface hover:bg-surface-hover text-xs font-medium text-text transition-colors shadow-xs cursor-pointer"
                title="Pick a random problem"
              >
                <Shuffle className="w-3.5 h-3.5 text-accent" />
                <span>Pick Random</span>
              </button>
            </div>
          </div>

          {/* Top Analytics Cards */}
          <LCAnalyticsCard analytics={analytics} loading={loadingAnalytics} />

          {/* Category Tabs: All / DSA / Database */}
          <div className="flex items-center justify-between border-b border-border pb-3">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => { setCategory('all'); setSelectedSubcategory('all'); setPage(1); }}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all cursor-pointer ${
                  category === 'all'
                    ? 'bg-accent text-accent-contrast shadow-xs'
                    : 'bg-surface text-text-muted hover:text-text hover:bg-surface-hover border border-border'
                }`}
              >
                All Categories (3,269)
              </button>
              <button
                type="button"
                onClick={() => { setCategory('dsa'); setSelectedSubcategory('all'); setPage(1); }}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all flex items-center gap-1.5 cursor-pointer ${
                  category === 'dsa'
                    ? 'bg-accent text-accent-contrast shadow-xs'
                    : 'bg-surface text-text-muted hover:text-text hover:bg-surface-hover border border-border'
                }`}
              >
                <Code2 className="w-3.5 h-3.5" />
                <span>DSA Algorithms (3,164)</span>
              </button>
              <button
                type="button"
                onClick={() => { setCategory('database'); setSelectedSubcategory('all'); setPage(1); }}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all flex items-center gap-1.5 cursor-pointer ${
                  category === 'database'
                    ? 'bg-accent text-accent-contrast shadow-xs'
                    : 'bg-surface text-text-muted hover:text-text hover:bg-surface-hover border border-border'
                }`}
              >
                <Database className="w-3.5 h-3.5" />
                <span>Database SQL (105)</span>
              </button>
            </div>

            {/* My List Filter Button */}
            <button
              type="button"
              onClick={() => { setMyListOnly(prev => !prev); setPage(1); }}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all flex items-center gap-1.5 border cursor-pointer ${
                myListOnly
                  ? 'bg-amber-500/15 border-amber-500/50 text-amber-500'
                  : 'bg-surface border-border text-text-muted hover:text-text hover:bg-surface-hover'
              }`}
            >
              <Star className={`w-3.5 h-3.5 ${myListOnly ? 'fill-amber-500 text-amber-500' : ''}`} />
              <span>My List</span>
            </button>
          </div>

          {/* Subcategory / Topic Pills (Horizontal Scrollable) */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none text-xs">
            {currentTopics.map(topic => {
              const isSelected = selectedSubcategory === topic.slug;
              return (
                <button
                  key={topic.slug}
                  type="button"
                  onClick={() => { setSelectedSubcategory(topic.slug); setPage(1); }}
                  className={`px-3 py-1 rounded-full whitespace-nowrap transition-colors cursor-pointer text-xs ${
                    isSelected
                      ? 'bg-text text-bg font-semibold'
                      : 'bg-surface border border-border text-text-muted hover:text-text hover:bg-surface-hover'
                  }`}
                >
                  {topic.label}
                </button>
              );
            })}
          </div>

          {/* Search & Filters Row */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-3 rounded-[12px] bg-surface border border-border">
            {/* Search Input */}
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-text-muted absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search questions by title, # number, or tag (e.g. 'Two Sum', '207', 'Graph')..."
                className="w-full pl-9 pr-4 py-1.5 rounded-lg bg-bg border border-border text-xs text-text placeholder:text-text-muted/60 focus:outline-none focus:border-border-focus"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-muted hover:text-text p-0.5"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {/* Filter Dropdowns */}
            <div className="flex items-center gap-2">
              {/* Difficulty */}
              <select
                value={selectedDifficulty}
                onChange={(e) => { setSelectedDifficulty(e.target.value); setPage(1); }}
                className="px-3 py-1.5 rounded-lg bg-bg border border-border text-xs text-text focus:outline-none focus:border-border-focus cursor-pointer"
              >
                <option value="all">Difficulty: All</option>
                <option value="Easy">Easy</option>
                <option value="Medium">Medium</option>
                <option value="Hard">Hard</option>
              </select>

              {/* Status */}
              <select
                value={selectedStatus}
                onChange={(e) => { setSelectedStatus(e.target.value); setPage(1); }}
                className="px-3 py-1.5 rounded-lg bg-bg border border-border text-xs text-text focus:outline-none focus:border-border-focus cursor-pointer"
              >
                <option value="all">Status: All</option>
                <option value="solved">Solved</option>
                <option value="attempted">Attempted</option>
                <option value="todo">Todo</option>
              </select>

              {/* Reset Filters */}
              {(selectedDifficulty !== 'all' || selectedStatus !== 'all' || selectedSubcategory !== 'all' || myListOnly || searchQuery) && (
                <button
                  type="button"
                  onClick={() => {
                    setSelectedDifficulty('all');
                    setSelectedStatus('all');
                    setSelectedSubcategory('all');
                    setMyListOnly(false);
                    setSearchQuery('');
                    setPage(1);
                  }}
                  className="p-2 rounded-lg bg-bg border border-border text-text-muted hover:text-text transition-colors"
                  title="Reset all filters"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>

          {/* Numbered Questions Table */}
          <div className="rounded-[12px] bg-surface border border-border overflow-hidden shadow-xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-border bg-bg/50 text-text-muted font-mono uppercase tracking-wider text-[11px]">
                    <th className="py-3 px-3 w-10 text-center">Status</th>
                    <th className="py-3 px-2 w-10 text-center">Star</th>
                    <th className="py-3 px-3 w-16 text-center">#</th>
                    <th className="py-3 px-4">Title</th>
                    <th className="py-3 px-4">Topics</th>
                    <th className="py-3 px-3 w-24">Difficulty</th>
                    <th className="py-3 px-4 w-32">Time Complexity</th>
                    <th className="py-3 px-4 w-32">Space Complexity</th>
                    <th className="py-3 px-3 w-20 text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {loadingList ? (
                    <tr>
                      <td colSpan={9} className="py-16 text-center text-text-muted font-mono">
                        <div className="inline-flex items-center gap-2">
                          <span className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin"></span>
                          <span>Loading questions from problem repository...</span>
                        </div>
                      </td>
                    </tr>
                  ) : questions.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="py-16 text-center text-text-muted">
                        <div className="max-w-md mx-auto space-y-2">
                          <FileText className="w-8 h-8 text-text-muted mx-auto opacity-50" />
                          <div className="text-sm font-medium text-text">No questions match your current filters</div>
                          <p className="text-xs text-text-muted">
                            Try adjusting your search terms, changing the subcategory, or clearing filters.
                          </p>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    questions.map((q) => {
                      const isSolved = q.status === 'solved';
                      const isAttempted = q.status === 'attempted';

                      return (
                        <tr 
                          key={q.id}
                          onClick={() => setActiveQuestionId(q.id)}
                          className="hover:bg-surface-hover/70 transition-colors cursor-pointer group"
                        >
                          {/* Status Icon */}
                          <td className="py-3 px-3 text-center">
                            {isSolved ? (
                              <span title="Solved">
                                <CheckCircle2 className="w-4 h-4 text-emerald-500 inline-block" />
                              </span>
                            ) : isAttempted ? (
                              <span title="Attempted">
                                <div className="w-3.5 h-3.5 rounded-full border-2 border-amber-500 inline-block" />
                              </span>
                            ) : (
                              <span className="text-text-muted/40 font-mono text-xs">—</span>
                            )}
                          </td>

                          {/* Star Toggle */}
                          <td className="py-3 px-2 text-center" onClick={(e) => handleToggleStar(q.id, e)}>
                            <button
                              type="button"
                              className="p-1 rounded hover:bg-bg transition-colors"
                              title={q.isStarred ? "Remove from My List" : "Add to My List"}
                            >
                              <Star className={`w-3.5 h-3.5 ${q.isStarred ? 'text-amber-400 fill-amber-400' : 'text-text-muted hover:text-text'}`} />
                            </button>
                          </td>

                          {/* Numeric # */}
                          <td className="py-3 px-3 font-mono text-center text-text-muted font-medium">
                            {q.id}
                          </td>

                          {/* Title */}
                          <td className="py-3 px-4 font-medium text-text group-hover:text-accent transition-colors">
                            <div className="flex items-center gap-2">
                              <span>{q.title}</span>
                              {q.category === 'database' && (
                                <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-amber-500/10 text-amber-500 border border-amber-500/20">
                                  SQL
                                </span>
                              )}
                            </div>
                          </td>

                          {/* Topics / Subcategory Badge */}
                          <td className="py-3 px-4">
                            <span className="inline-block px-2 py-0.5 rounded text-[11px] font-mono bg-bg border border-border text-text-muted">
                              {q.subcategory.replace(/-/g, ' ')}
                            </span>
                          </td>

                          {/* Difficulty Badge */}
                          <td className="py-3 px-3">
                            <span className={`inline-block px-2 py-0.5 rounded text-[11px] font-medium font-mono ${
                              q.difficulty === 'Easy'
                                ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'
                                : q.difficulty === 'Medium'
                                ? 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
                                : 'bg-rose-500/10 text-rose-500 border border-rose-500/20'
                            }`}>
                              {q.difficulty}
                            </span>
                          </td>

                          {/* Time Complexity */}
                          <td className="py-3 px-4 font-mono text-[11.5px] text-text-muted">
                            <span className="text-text/80">{q.timeComplexity}</span>
                          </td>

                          {/* Space Complexity */}
                          <td className="py-3 px-4 font-mono text-[11.5px] text-text-muted">
                            <span className="text-text/80">{q.spaceComplexity}</span>
                          </td>

                          {/* Action Button */}
                          <td className="py-3 px-3 text-center">
                            <button
                              type="button"
                              className="px-2.5 py-1 rounded-md text-[11px] font-medium bg-bg border border-border group-hover:border-accent group-hover:text-accent transition-all cursor-pointer"
                            >
                              Solve
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 border-t border-border bg-bg/40 text-xs">
              <div className="text-text-muted font-mono">
                Showing <strong className="text-text">{questions.length > 0 ? (page - 1) * pageSize + 1 : 0}</strong> -{' '}
                <strong className="text-text">{Math.min(page * pageSize, totalQuestions)}</strong> of{' '}
                <strong className="text-text">{totalQuestions}</strong> questions
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={page <= 1}
                  onClick={() => setPage(prev => Math.max(1, prev - 1))}
                  className="px-2.5 py-1 rounded border border-border bg-surface text-text hover:bg-surface-hover disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronLeft className="w-3.5 h-3.5 inline mr-1" />
                  Prev
                </button>

                <span className="px-2 font-mono text-text-muted">
                  Page <strong className="text-text">{page}</strong> of <strong className="text-text">{totalPages}</strong>
                </span>

                <button
                  type="button"
                  disabled={page >= totalPages}
                  onClick={() => setPage(prev => Math.min(totalPages, prev + 1))}
                  className="px-2.5 py-1 rounded border border-border bg-surface text-text hover:bg-surface-hover disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  Next
                  <ChevronRight className="w-3.5 h-3.5 inline ml-1" />
                </button>

                {/* Page Size Selector */}
                <select
                  value={pageSize}
                  onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}
                  className="ml-2 px-2 py-1 rounded border border-border bg-surface text-xs text-text focus:outline-none cursor-pointer"
                >
                  <option value={50}>50 / page</option>
                  <option value={100}>100 / page</option>
                </select>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // =========================================================================
  // VIEW 2: LEETCODE QUESTION SOLVER WORKSPACE
  // =========================================================================
  if (loadingDetail || !questionDetail) {
    return (
      <div className="min-h-screen bg-bg flex items-center justify-center text-text font-mono">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-accent border-t-transparent rounded-full animate-spin"></div>
          <div className="text-xs text-text-muted">Loading Question #{activeQuestionId}...</div>
        </div>
      </div>
    );
  }

  const isDsa = questionDetail.category !== 'database';
  const availableLangs = isDsa ? DSA_LANGUAGES : DB_LANGUAGES;

  return (
    <div className="min-h-screen bg-bg text-text flex flex-col">
      {/* Top LeetCode Navigation Bar */}
      <header className="sticky top-0 z-40 bg-surface border-b border-border px-4 py-2 flex items-center justify-between gap-4">
        {/* Left: Back to Problem List & Question Navigator */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setActiveQuestionId(null)}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium text-text-muted hover:text-text hover:bg-surface-hover border border-border transition-colors cursor-pointer"
            title="Back to All Problems"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Problems</span>
          </button>

          <span className="text-border">|</span>

          {/* Subcategory Pill */}
          <span className="text-xs font-mono text-accent capitalize hidden md:inline">
            {questionDetail.subcategory.replace(/-/g, ' ')}
          </span>

          {/* Prev / Next / Random */}
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => handleNavigateRelative('prev')}
              className="p-1 rounded text-text-muted hover:text-text hover:bg-surface-hover transition-colors"
              title="Previous Problem"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={() => handleNavigateRelative('next')}
              className="p-1 rounded text-text-muted hover:text-text hover:bg-surface-hover transition-colors"
              title="Next Problem"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={handlePickRandom}
              className="p-1 rounded text-text-muted hover:text-text hover:bg-surface-hover transition-colors"
              title="Pick Random Problem"
            >
              <Shuffle className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Center: Run & Submit Actions */}
        <div className="flex items-center gap-2">
          {/* Run Code Button */}
          <button
            type="button"
            disabled={isRunning || isSubmitting}
            onClick={handleRunCode}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-bg hover:bg-surface-hover text-xs font-medium text-text transition-colors shadow-xs cursor-pointer disabled:opacity-50"
            title="Run against sample test cases (Ctrl + Enter)"
          >
            {isRunning ? (
              <span className="w-3.5 h-3.5 border-2 border-accent border-t-transparent rounded-full animate-spin"></span>
            ) : (
              <Play className="w-3.5 h-3.5 fill-emerald-500 text-emerald-500" />
            )}
            <span>Run</span>
          </button>

          {/* Submit Code Button */}
          <button
            type="button"
            disabled={isRunning || isSubmitting}
            onClick={handleSubmitCode}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition-colors shadow-xs cursor-pointer disabled:opacity-50"
            title="Submit solution for full automated evaluation"
          >
            {isSubmitting ? (
              <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
            ) : (
              <CloudUpload className="w-3.5 h-3.5" />
            )}
            <span>Submit</span>
          </button>
        </div>

        {/* Right: Timer & Star Bookmark */}
        <div className="flex items-center gap-3">
          {/* LeetCode Styled Timer */}
          <LCTimer questionId={questionDetail.id} />

          {/* Star Toggle */}
          <button
            type="button"
            onClick={(e) => handleToggleStar(questionDetail.id, e)}
            className="p-1.5 rounded-md hover:bg-surface-hover transition-colors cursor-pointer"
            title={questionDetail.isStarred ? "Remove Star" : "Star Problem"}
          >
            <Star className={`w-4 h-4 ${questionDetail.isStarred ? 'text-amber-400 fill-amber-400' : 'text-text-muted hover:text-text'}`} />
          </button>
        </div>
      </header>

      {/* Main Two-Column Split Workspace */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 min-h-0">
        {/* ================================================================= */}
        {/* LEFT PANE: Problem Statement, Editorial, Hints, Submissions */}
        {/* ================================================================= */}
        <div className="lg:col-span-5 border-r border-border flex flex-col bg-bg overflow-hidden h-[calc(100vh-50px)]">
          {/* Top Left Navigation Tabs */}
          <div className="flex items-center border-b border-border bg-surface px-2">
            <button
              type="button"
              onClick={() => setSolverTab('description')}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors cursor-pointer ${
                solverTab === 'description'
                  ? 'border-accent text-accent'
                  : 'border-transparent text-text-muted hover:text-text'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Description</span>
            </button>

            <button
              type="button"
              onClick={() => setSolverTab('editorial')}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors cursor-pointer ${
                solverTab === 'editorial'
                  ? 'border-accent text-accent'
                  : 'border-transparent text-text-muted hover:text-text'
              }`}
            >
              <BookOpen className="w-3.5 h-3.5" />
              <span>Approach</span>
            </button>

            <button
              type="button"
              onClick={() => setSolverTab('hints')}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors cursor-pointer ${
                solverTab === 'hints'
                  ? 'border-accent text-accent'
                  : 'border-transparent text-text-muted hover:text-text'
              }`}
            >
              <Lightbulb className="w-3.5 h-3.5" />
              <span>Hints</span>
              {questionDetail.hints && questionDetail.hints.length > 0 && (
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-accent/20 text-accent font-mono">
                  {questionDetail.hints.length}
                </span>
              )}
            </button>

            <button
              type="button"
              onClick={() => setSolverTab('submissions')}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors cursor-pointer ${
                solverTab === 'submissions'
                  ? 'border-accent text-accent'
                  : 'border-transparent text-text-muted hover:text-text'
              }`}
            >
              <Clock className="w-3.5 h-3.5" />
              <span>Submissions</span>
              {questionDetail.prevSubmissions && questionDetail.prevSubmissions.length > 0 && (
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-surface-hover text-text-muted font-mono">
                  {questionDetail.prevSubmissions.length}
                </span>
              )}
            </button>
          </div>

          {/* Left Pane Content Body */}
          <div className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-5">
            {/* TAB: DESCRIPTION */}
            {solverTab === 'description' && (
              <div className="space-y-5 animate-fadeIn">
                {/* Title & Status */}
                <div>
                  <div className="flex items-center justify-between gap-2">
                    <h2 className="text-xl sm:text-2xl font-semibold text-text font-sans tracking-tight">
                      {questionDetail.num}. {questionDetail.title}
                    </h2>
                    {questionDetail.status === 'solved' && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-mono font-medium bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                        <Check className="w-3 h-3" /> Solved
                      </span>
                    )}
                  </div>

                  {/* Pills Row: Difficulty, Topics, Time, Space */}
                  <div className="flex flex-wrap items-center gap-2 mt-3 text-xs">
                    {/* Difficulty */}
                    <span className={`px-2.5 py-0.5 rounded-full font-medium font-mono text-[11px] ${
                      questionDetail.difficulty === 'Easy'
                        ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'
                        : questionDetail.difficulty === 'Medium'
                        ? 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
                        : 'bg-rose-500/10 text-rose-500 border border-rose-500/20'
                    }`}>
                      {questionDetail.difficulty}
                    </span>

                    {/* Time Complexity */}
                    <span className="px-2.5 py-0.5 rounded-full font-mono text-[11px] bg-surface border border-border text-text-muted">
                      ⏱ Time: <strong className="text-text">{questionDetail.timeComplexity}</strong>
                    </span>

                    {/* Space Complexity */}
                    <span className="px-2.5 py-0.5 rounded-full font-mono text-[11px] bg-surface border border-border text-text-muted">
                      📦 Space: <strong className="text-text">{questionDetail.spaceComplexity}</strong>
                    </span>

                    {/* SQL Schema button if database */}
                    {questionDetail.sqlSchema && (
                      <button
                        type="button"
                        onClick={() => setShowSqlSchemaModal(true)}
                        className="px-2.5 py-0.5 rounded-full font-mono text-[11px] bg-amber-500/10 border border-amber-500/30 text-amber-500 hover:bg-amber-500/20 transition-colors cursor-pointer"
                      >
                        💾 SQL Schema
                      </button>
                    )}
                  </div>

                  {/* Tags */}
                  {questionDetail.tags && questionDetail.tags.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5 mt-2">
                      {questionDetail.tags.map((tag, tIdx) => (
                        <span key={tIdx} className="px-2 py-0.5 rounded text-[10px] font-mono bg-surface border border-border text-text-muted">
                          #{tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <hr className="border-border" />

                {/* Question Statement Markdown with Diagrams */}
                <LCMarkdownViewer content={questionDetail.statement} />

                {/* Examples */}
                {questionDetail.examples && questionDetail.examples.length > 0 && (
                  <div className="space-y-4 pt-2">
                    <h3 className="text-sm font-semibold text-text uppercase tracking-wider font-mono">
                      Examples
                    </h3>
                    {questionDetail.examples.map((ex, idx) => (
                      <div key={idx} className="p-3.5 rounded-lg bg-surface border border-border space-y-1.5 font-mono text-xs">
                        <div className="font-semibold text-text font-sans text-xs">
                          Example {idx + 1}:
                        </div>
                        <div>
                          <span className="text-text-muted font-bold">Input: </span>
                          <span className="text-text">{ex.input}</span>
                        </div>
                        <div>
                          <span className="text-text-muted font-bold">Output: </span>
                          <span className="text-text">{ex.output}</span>
                        </div>
                        {ex.explanation && (
                          <div className="text-text-muted font-sans text-[12px] pt-1 border-t border-border/50">
                            <strong>Explanation: </strong>{ex.explanation}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Constraints */}
                {questionDetail.constraints && questionDetail.constraints.length > 0 && (
                  <div className="space-y-2 pt-2">
                    <h3 className="text-sm font-semibold text-text uppercase tracking-wider font-mono">
                      Constraints
                    </h3>
                    <ul className="list-disc pl-5 space-y-1 text-xs font-mono text-text-muted">
                      {questionDetail.constraints.map((c, idx) => (
                        <li key={idx} className="text-text">
                          <code className="bg-surface px-1.5 py-0.5 rounded border border-border text-text">
                            {c}
                          </code>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* TAB: EDITORIAL / APPROACH */}
            {solverTab === 'editorial' && (
              <div className="space-y-4 animate-fadeIn">
                <div className="p-4 rounded-lg bg-surface border border-border space-y-2">
                  <div className="flex items-center gap-2 text-accent font-semibold text-sm">
                    <Sparkles className="w-4 h-4" />
                    <span>Intuition & Algorithmic Approach</span>
                  </div>
                  <p className="text-xs leading-relaxed text-text-muted">
                    This problem belongs to the <strong className="text-text">{questionDetail.subcategory}</strong> category.
                    Aim for an optimal solution matching the expected complexity:
                  </p>
                  <div className="grid grid-cols-2 gap-2 pt-2 text-xs font-mono">
                    <div className="p-2 rounded bg-bg border border-border">
                      <span className="text-text-muted">Optimal Time:</span>
                      <div className="text-text font-semibold">{questionDetail.timeComplexity}</div>
                    </div>
                    <div className="p-2 rounded bg-bg border border-border">
                      <span className="text-text-muted">Auxiliary Space:</span>
                      <div className="text-text font-semibold">{questionDetail.spaceComplexity}</div>
                    </div>
                  </div>
                </div>

                <div className="space-y-2 text-xs text-text-muted leading-relaxed">
                  <h4 className="font-semibold text-text text-sm">Key Strategy</h4>
                  <p>
                    1. Identify invariant constraints and boundary conditions from the constraints list.
                  </p>
                  <p>
                    2. Use optimal data structures (hash maps for O(1) lookups, two pointers/sliding window for linear scans, or priority queues for streaming medians/heaps).
                  </p>
                  <p>
                    3. For SQL questions, verify Cartesian products, index usage on JOIN keys, and appropriate WHERE vs HAVING clause placement.
                  </p>
                </div>
              </div>
            )}

            {/* TAB: HINTS */}
            {solverTab === 'hints' && (
              <div className="space-y-3 animate-fadeIn">
                <div className="text-xs text-text-muted mb-2">
                  Stuck on this problem? Click on a hint below to progressively reveal guidance.
                </div>

                {!questionDetail.hints || questionDetail.hints.length === 0 ? (
                  <div className="p-6 text-center text-text-muted text-xs bg-surface rounded-lg border border-border">
                    No official hints provided for this question. Try testing edge cases or checking the approach tab!
                  </div>
                ) : (
                  questionDetail.hints.map((hintText, idx) => {
                    const isRevealed = !!revealedHints[idx];
                    return (
                      <div key={idx} className="rounded-lg bg-surface border border-border overflow-hidden">
                        <button
                          type="button"
                          onClick={() => setRevealedHints(prev => ({ ...prev, [idx]: !prev[idx] }))}
                          className="w-full flex items-center justify-between p-3 text-xs font-medium text-left hover:bg-surface-hover transition-colors cursor-pointer"
                        >
                          <span className="flex items-center gap-2">
                            <Lightbulb className={`w-3.5 h-3.5 ${isRevealed ? 'text-amber-400 fill-amber-400' : 'text-text-muted'}`} />
                            <span>Hint {idx + 1}</span>
                          </span>
                          <span className="text-text-muted text-[11px] font-mono">
                            {isRevealed ? "Hide" : "Reveal"}
                          </span>
                        </button>
                        {isRevealed && (
                          <div className="p-3 pt-0 border-t border-border/40 text-xs text-text leading-relaxed bg-bg/50">
                            {hintText}
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            )}

            {/* TAB: SUBMISSIONS */}
            {solverTab === 'submissions' && (
              <div className="space-y-3 animate-fadeIn">
                <div className="text-xs text-text-muted mb-2">
                  Your past submissions for this problem:
                </div>

                {!questionDetail.prevSubmissions || questionDetail.prevSubmissions.length === 0 ? (
                  <div className="p-6 text-center text-text-muted text-xs bg-surface rounded-lg border border-border">
                    No submissions recorded yet. Write your code and click Submit to test!
                  </div>
                ) : (
                  questionDetail.prevSubmissions.map((sub, idx) => (
                    <div 
                      key={sub.id || idx}
                      onClick={() => setViewingSubmissionCode(sub)}
                      className="p-3 rounded-lg bg-surface border border-border hover:border-accent/50 transition-all cursor-pointer flex items-center justify-between gap-3 text-xs"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-0.5 rounded font-mono font-medium text-[11px] ${
                            sub.status === 'Accepted'
                              ? 'bg-emerald-500/10 text-emerald-500'
                              : 'bg-rose-500/10 text-rose-500'
                          }`}>
                            {sub.status}
                          </span>
                          <span className="font-mono text-text-muted">{sub.language}</span>
                        </div>
                        <div className="text-[11px] text-text-muted font-mono">
                          {sub.runtime_ms != null && sub.runtime_ms > 0 && <span>Runtime: {sub.runtime_ms} ms</span>}
                          {sub.runtime_ms != null && sub.runtime_ms > 0 && sub.memory_mb != null && sub.memory_mb > 0 && <span> · </span>}
                          {sub.memory_mb != null && sub.memory_mb > 0 && <span>Memory: {sub.memory_mb} MB</span>}
                        </div>
                      </div>

                      <div className="text-right">
                        <div className="text-[11px] text-text-muted font-mono">
                          {sub.submitted_at ? new Date(sub.submitted_at).toLocaleDateString() : 'Recent'}
                        </div>
                        <span className="text-[11px] text-accent font-medium hover:underline">
                          View Code →
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>

        {/* ================================================================= */}
        {/* RIGHT PANE: Code Editor (Top) & Testcase/Result Console (Bottom) */}
        {/* ================================================================= */}
        <div className="lg:col-span-7 flex flex-col bg-surface overflow-hidden h-[calc(100vh-50px)]">
          {/* Top Code Editor Header */}
          <div className="px-4 py-2 border-b border-border bg-surface flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5 text-xs font-mono font-semibold text-text">
                <Code2 className="w-3.5 h-3.5 text-accent" />
                <span>Code</span>
              </div>

              {/* Language Selector Dropdown */}
              <select
                value={selectedLang}
                onChange={(e) => handleLanguageChange(e.target.value)}
                className="px-2.5 py-1 rounded bg-bg border border-border text-xs font-mono text-text focus:outline-none focus:border-border-focus cursor-pointer"
              >
                {availableLangs.map(l => (
                  <option key={l.id} value={l.id}>{l.label}</option>
                ))}
              </select>
            </div>

            {/* Editor Actions: Reset Code, Copy Code */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleCopyCode}
                className="p-1.5 rounded hover:bg-surface-hover text-text-muted hover:text-text transition-colors"
                title="Copy Code to Clipboard"
              >
                {copiedCode ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
              </button>

              <button
                type="button"
                onClick={handleResetCode}
                className="p-1.5 rounded hover:bg-surface-hover text-text-muted hover:text-text transition-colors"
                title="Reset to default starter code"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Monaco Code Editor Area */}
          <div className="flex-1 min-h-[300px] border-b border-border relative">
            <Editor
              height="100%"
              language={availableLangs.find(l => l.id === selectedLang)?.monacoLang || 'python'}
              theme={editorTheme}
              value={code}
              onChange={(val) => setCode(val || '')}
              onMount={handleEditorMount}
              options={{
                fontSize: 13,
                fontFamily: '"JetBrains Mono", Consolas, "Courier New", monospace',
                tabSize: 4,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                wordWrap: 'on',
                lineNumbers: 'on',
                automaticLayout: true,
                padding: { top: 10, bottom: 10 }
              }}
            />
          </div>

          {/* Bottom Console: Testcase & Results (Split Tabs) */}
          <div className="h-64 flex flex-col bg-bg">
            {/* Console Header Tabs */}
            <div className="px-3 border-b border-border bg-surface flex items-center justify-between">
              <div className="flex items-center">
                <button
                  type="button"
                  onClick={() => setBottomConsoleTab('testcase')}
                  className={`px-3 py-1.5 text-xs font-mono font-medium border-b-2 transition-colors cursor-pointer ${
                    bottomConsoleTab === 'testcase'
                      ? 'border-accent text-accent'
                      : 'border-transparent text-text-muted hover:text-text'
                  }`}
                >
                  ✓ Testcase
                </button>
                <button
                  type="button"
                  onClick={() => setBottomConsoleTab('result')}
                  className={`px-3 py-1.5 text-xs font-mono font-medium border-b-2 transition-colors cursor-pointer ${
                    bottomConsoleTab === 'result'
                      ? 'border-accent text-accent'
                      : 'border-transparent text-text-muted hover:text-text'
                  }`}
                >
                  &gt;_ Test Result
                </button>
              </div>

              {/* Status Indicator */}
              <div className="text-[11px] font-mono text-text-muted">
                {isRunning && <span className="text-accent animate-pulse">Running test cases...</span>}
                {isSubmitting && <span className="text-emerald-500 animate-pulse">Evaluating submission...</span>}
              </div>
            </div>

            {/* Console Body */}
            <div className="flex-1 overflow-y-auto p-4 font-mono text-xs">
              {/* TAB 1: TESTCASE */}
              {bottomConsoleTab === 'testcase' && (
                <div className="space-y-3">
                  {/* Case 1, Case 2 tabs */}
                  <div className="flex items-center gap-2">
                    {(questionDetail.sampleCases || []).map((sc, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => setActiveCaseTab(idx)}
                        className={`px-2.5 py-1 rounded text-xs transition-colors cursor-pointer ${
                          activeCaseTab === idx
                            ? 'bg-surface text-text font-bold border border-border'
                            : 'bg-bg text-text-muted hover:text-text'
                        }`}
                      >
                        Case {idx + 1}
                      </button>
                    ))}
                  </div>

                  {/* Active Case Details */}
                  {questionDetail.sampleCases && questionDetail.sampleCases[activeCaseTab] ? (
                    <div className="space-y-2">
                      <div>
                        <span className="text-text-muted block text-[11px] uppercase mb-1">Input</span>
                        <div className="p-2 rounded bg-surface border border-border text-text whitespace-pre-wrap">
                          {questionDetail.sampleCases[activeCaseTab].input}
                        </div>
                      </div>
                      <div>
                        <span className="text-text-muted block text-[11px] uppercase mb-1">Expected Output</span>
                        <div className="p-2 rounded bg-surface border border-border text-text whitespace-pre-wrap">
                          {questionDetail.sampleCases[activeCaseTab].expected}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-text-muted">
                      No sample cases available. Click Run to test against standard tests.
                    </div>
                  )}
                </div>
              )}

              {/* TAB 2: TEST RESULT */}
              {bottomConsoleTab === 'result' && (
                <div>
                  {isRunning || isSubmitting ? (
                    <div className="py-8 text-center text-text-muted">
                      <div className="inline-flex items-center gap-2">
                        <span className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin"></span>
                        <span>Compiling and executing code...</span>
                      </div>
                    </div>
                  ) : submitResult ? (
                    /* SUBMIT RESULT VIEW */
                    <div className="space-y-3 animate-fadeIn">
                      <div className="flex items-center justify-between pb-2 border-b border-border">
                        <div className="flex items-center gap-2">
                          <span className={`text-base font-bold ${
                            submitResult.is_correct ? 'text-emerald-500' : 'text-rose-500'
                          }`}>
                            {submitResult.status}
                          </span>
                          {submitResult.is_correct && <CheckCircle2 className="w-5 h-5 text-emerald-500" />}
                        </div>
                        <div className="text-text-muted text-[11px]">
                          {submitResult.passed_test_cases} / {submitResult.total_test_cases} test cases passed
                        </div>
                      </div>

                      {/* Actual Performance metrics - only displayed if real measured data exists */}
                      {((submitResult.runtime_ms != null && submitResult.runtime_ms > 0) || 
                        (submitResult.memory_mb != null && submitResult.memory_mb > 0)) && (
                        <div className="grid grid-cols-2 gap-3">
                          {submitResult.runtime_ms != null && submitResult.runtime_ms > 0 && (
                            <div className="p-3 rounded bg-surface border border-border">
                              <span className="text-text-muted block text-[11px] uppercase font-semibold">Runtime</span>
                              <div className="text-base font-bold text-text">{submitResult.runtime_ms} ms</div>
                            </div>
                          )}

                          {submitResult.memory_mb != null && submitResult.memory_mb > 0 && (
                            <div className="p-3 rounded bg-surface border border-border">
                              <span className="text-text-muted block text-[11px] uppercase font-semibold">Memory</span>
                              <div className="text-base font-bold text-text">{submitResult.memory_mb} MB</div>
                            </div>
                          )}
                        </div>
                      )}

                      {!submitResult.is_correct && (submitResult.error || submitResult.error_message) && (
                        <div className="p-3 rounded bg-rose-500/10 border border-rose-500/30 text-rose-500 font-mono text-xs whitespace-pre-wrap">
                          {submitResult.error || submitResult.error_message}
                        </div>
                      )}
                    </div>
                  ) : runResult ? (
                    /* RUN RESULT VIEW */
                    <div className="space-y-3 animate-fadeIn">
                      <div className="flex items-center justify-between pb-2 border-b border-border">
                        <span className={`text-sm font-bold ${
                          runResult.is_correct ? 'text-emerald-500' : 'text-rose-500'
                        }`}>
                          {runResult.status}
                        </span>
                        <span className="text-text-muted text-[11px]">
                          {runResult.runtime_ms != null && runResult.runtime_ms > 0 ? `${runResult.runtime_ms} ms` : ''}
                        </span>
                      </div>

                      {(runResult.error || (!runResult.is_correct && runResult.compiler_output)) && (
                        <div className="p-3 rounded bg-rose-500/10 border border-rose-500/30 text-rose-500 font-mono text-xs whitespace-pre-wrap">
                          {runResult.error || runResult.compiler_output}
                        </div>
                      )}

                      {/* Per-testcase results */}
                      {runResult.test_case_results && runResult.test_case_results.length > 0 && (
                        <div className="space-y-3">
                          <div className="flex items-center gap-2">
                            {runResult.test_case_results.map((tc, idx) => (
                              <button
                                key={idx}
                                type="button"
                                onClick={() => setActiveCaseTab(idx)}
                                className={`px-2.5 py-1 rounded text-xs transition-colors cursor-pointer flex items-center gap-1 ${
                                  activeCaseTab === idx
                                    ? 'bg-surface text-text font-bold border border-border'
                                    : 'bg-bg text-text-muted'
                                }`}
                              >
                                <span className={`w-1.5 h-1.5 rounded-full ${tc.passed ? 'bg-emerald-500' : 'bg-rose-500'}`} />
                                Case {idx + 1}
                              </button>
                            ))}
                          </div>

                          {runResult.test_case_results[activeCaseTab] && (
                            <div className="space-y-2 bg-surface p-3 rounded-lg border border-border">
                              <div>
                                <span className="text-text-muted block text-[11px] uppercase">Input</span>
                                <div className="text-text">{runResult.test_case_results[activeCaseTab].input_data}</div>
                              </div>
                              <div>
                                <span className="text-text-muted block text-[11px] uppercase">Output</span>
                                <div className={runResult.test_case_results[activeCaseTab].passed ? "text-emerald-500" : "text-rose-500"}>
                                  {runResult.test_case_results[activeCaseTab].actual_output || '(None)'}
                                </div>
                              </div>
                              <div>
                                <span className="text-text-muted block text-[11px] uppercase">Expected</span>
                                <div className="text-text">{runResult.test_case_results[activeCaseTab].expected_output}</div>
                              </div>
                              {runResult.test_case_results[activeCaseTab].stdout && (
                                <div>
                                  <span className="text-text-muted block text-[11px] uppercase">Stdout</span>
                                  <div className="text-text-muted">{runResult.test_case_results[activeCaseTab].stdout}</div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="py-8 text-center text-text-muted">
                      Click <strong className="text-text font-bold">Run</strong> to evaluate against sample test cases or <strong className="text-text font-bold">Submit</strong> for full verification.
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* SQL Schema Modal for DBMS Questions */}
      {showSqlSchemaModal && questionDetail.sqlSchema && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-surface border border-border rounded-xl max-w-2xl w-full p-5 space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-text">
                <Database className="w-4 h-4 text-amber-500" />
                <span>SQL Schema & Table Definitions</span>
              </div>
              <button
                type="button"
                onClick={() => setShowSqlSchemaModal(false)}
                className="text-text-muted hover:text-text p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-3 bg-bg rounded-lg border border-border font-mono text-xs text-text overflow-x-auto max-h-96 whitespace-pre-wrap">
              {questionDetail.sqlSchema}
            </div>

            {questionDetail.sqlSetup && questionDetail.sqlSetup.length > 0 && (
              <div className="space-y-1">
                <span className="text-xs font-mono text-text-muted">Setup / Sample Inserts:</span>
                <div className="p-2 bg-bg rounded border border-border font-mono text-[11px] text-text-muted max-h-32 overflow-y-auto">
                  {questionDetail.sqlSetup.join('\n')}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Submission Code Modal */}
      {viewingSubmissionCode && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-surface border border-border rounded-xl max-w-2xl w-full p-5 space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded font-mono font-medium text-xs ${
                    viewingSubmissionCode.status === 'Accepted'
                      ? 'bg-emerald-500/10 text-emerald-500'
                      : 'bg-rose-500/10 text-rose-500'
                  }`}>
                    {viewingSubmissionCode.status}
                  </span>
                  <span className="text-xs font-mono text-text-muted">{viewingSubmissionCode.language}</span>
                </div>
                <div className="text-[11px] text-text-muted font-mono">
                  Runtime: {viewingSubmissionCode.runtime_ms} ms · Memory: {viewingSubmissionCode.memory_mb} MB
                </div>
              </div>
              <button
                type="button"
                onClick={() => setViewingSubmissionCode(null)}
                className="text-text-muted hover:text-text p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-3 bg-bg rounded-lg border border-border font-mono text-xs text-text overflow-x-auto max-h-96 whitespace-pre-wrap">
              {viewingSubmissionCode.code}
            </div>

            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  setCode(viewingSubmissionCode.code);
                  setViewingSubmissionCode(null);
                }}
                className="px-3 py-1.5 rounded-lg bg-accent text-accent-contrast text-xs font-medium hover:bg-accent-hover transition-colors"
              >
                Load Code into Editor
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
