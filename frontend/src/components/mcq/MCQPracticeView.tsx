import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { 
  Search, Filter, Star, CheckCircle2, RotateCcw, 
  ChevronLeft, ChevronRight, Shuffle, Sparkles, 
  Layers, Code2, BookOpen, AlertCircle, Play, 
  HelpCircle, ChevronDown, Check, X, FileText 
} from 'lucide-react';
import { MCQBroadTopic, MCQQuestionSummary, MCQAnalytics } from '../../types';
import { api } from '../../services/api';
import { MCQTopicCard } from './MCQTopicCard';
import { MCQQuestionModal } from './MCQQuestionModal';
import { MCQQuizModal } from './MCQQuizModal';

export const MCQPracticeView: React.FC = () => {
  // Broad Topics & Analytics State
  const [broadTopics, setBroadTopics] = useState<MCQBroadTopic[]>([]);
  const [loadingTopics, setLoadingTopics] = useState(true);
  const [analytics, setAnalytics] = useState<MCQAnalytics | null>(null);

  // Filter State
  const [selectedTopics, setSelectedTopics] = useState<string[]>([]); // empty = all
  const [difficulty, setDifficulty] = useState<string>('all');
  const [status, setStatus] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [hasCodeOnly, setHasCodeOnly] = useState<boolean>(false);
  const [starredOnly, setStarredOnly] = useState<boolean>(false);
  const [page, setPage] = useState<number>(1);
  const limit = 25;

  // Questions State
  const [questions, setQuestions] = useState<MCQQuestionSummary[]>([]);
  const [totalQuestions, setTotalQuestions] = useState<number>(0);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [loadingQuestions, setLoadingQuestions] = useState<boolean>(true);

  // Active Interactive Solver Modal
  const [activeQuestionId, setActiveQuestionId] = useState<string | null>(null);

  // Quiz Modal State
  const [quizModalOpen, setQuizModalOpen] = useState(false);
  const [quizInitialTopic, setQuizInitialTopic] = useState<string | undefined>(undefined);

  // Dropdown open state for multiple topic filter
  const [topicDropdownOpen, setTopicDropdownOpen] = useState(false);

  // Load Broad Topics & Analytics
  const loadMetadata = useCallback(async () => {
    try {
      const [topicsRes, analyticsRes] = await Promise.all([
        api.getMCQTopics(),
        api.getMCQAnalytics().catch(() => null)
      ]);
      setBroadTopics(topicsRes);
      if (analyticsRes) setAnalytics(analyticsRes);
    } catch (err) {
      console.error('Failed to load MCQ metadata:', err);
    } finally {
      setLoadingTopics(false);
    }
  }, []);

  useEffect(() => {
    loadMetadata();
  }, [loadMetadata]);

  // Load Questions whenever filters change
  const loadQuestions = useCallback(async () => {
    setLoadingQuestions(true);
    try {
      const topicsParam = selectedTopics.length > 0 ? selectedTopics.join(',') : undefined;
      const res = await api.getMCQQuestions({
        topics: topicsParam,
        difficulty,
        status,
        search: searchQuery.trim() || undefined,
        has_code: hasCodeOnly ? true : undefined,
        starred_only: starredOnly,
        page,
        limit,
        sort_by: 'id',
        order: 'asc'
      });
      setQuestions(res.questions);
      setTotalQuestions(res.total);
      setTotalPages(res.total_pages);
    } catch (err) {
      console.error('Failed to load MCQ questions:', err);
    } finally {
      setLoadingQuestions(false);
    }
  }, [selectedTopics, difficulty, status, searchQuery, hasCodeOnly, starredOnly, page]);

  useEffect(() => {
    loadQuestions();
  }, [loadQuestions]);

  // Toggle single topic in cards or filter
  const handleTopicCardClick = (topicId: string) => {
    if (selectedTopics.length === 1 && selectedTopics[0] === topicId) {
      // Toggle off -> show all
      setSelectedTopics([]);
    } else {
      setSelectedTopics([topicId]);
    }
    setPage(1);
  };

  const toggleTopicMulti = (topicId: string) => {
    if (selectedTopics.includes(topicId)) {
      setSelectedTopics(selectedTopics.filter(t => t !== topicId));
    } else {
      setSelectedTopics([...selectedTopics, topicId]);
    }
    setPage(1);
  };

  const handleResetFilters = () => {
    setSelectedTopics([]);
    setDifficulty('all');
    setStatus('all');
    setSearchQuery('');
    setHasCodeOnly(false);
    setStarredOnly(false);
    setPage(1);
  };

  const handlePickRandom = async () => {
    if (questions.length > 0) {
      const randIdx = Math.floor(Math.random() * questions.length);
      setActiveQuestionId(questions[randIdx].id);
    } else {
      try {
        const res = await api.getMCQQuestions({ limit: 50, sort_by: 'random' });
        if (res.questions.length > 0) {
          setActiveQuestionId(res.questions[0].id);
        }
      } catch (err) {
        console.error(err);
      }
    }
  };

  const handleStartTopicQuiz = (topicId: string) => {
    setQuizInitialTopic(topicId);
    setQuizModalOpen(true);
  };

  // Navigate next/prev inside solver modal
  const handleNavigateModal = (direction: 'prev' | 'next') => {
    if (!activeQuestionId || questions.length === 0) return;
    const curIdx = questions.findIndex(q => q.id === activeQuestionId);
    if (curIdx === -1) return;
    if (direction === 'next' && curIdx < questions.length - 1) {
      setActiveQuestionId(questions[curIdx + 1].id);
    } else if (direction === 'prev' && curIdx > 0) {
      setActiveQuestionId(questions[curIdx - 1].id);
    }
  };

  const handleModalStatusUpdated = (questionId: string, newStatus: 'todo' | 'attempted' | 'solved', newIsStarred: boolean) => {
    // Update question in local state
    setQuestions(prev => prev.map(q => {
      if (q.id === questionId) {
        return { ...q, status: newStatus, is_starred: newIsStarred };
      }
      return q;
    }));
    loadMetadata();
  };

  const getDifficultyBadge = (diff: string) => {
    switch (diff?.toLowerCase()) {
      case 'easy':
        return 'text-emerald-500 bg-emerald-500/10 border-emerald-500/20';
      case 'medium':
        return 'text-amber-500 bg-amber-500/10 border-amber-500/20';
      case 'hard':
        return 'text-rose-500 bg-rose-500/10 border-rose-500/20';
      default:
        return 'text-text-muted bg-surface border-border';
    }
  };

  return (
    <div className="space-y-6">
      {/* 1. Header Overview & Progress Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-surface border border-border flex items-center justify-between">
          <div>
            <span className="text-[11px] font-mono uppercase tracking-wider text-text-muted">Total Bank</span>
            <div className="text-2xl font-bold font-serif text-text mt-0.5">1,500</div>
            <span className="text-xs text-text-muted">Questions across 9 broad topics</span>
          </div>
          <div className="w-10 h-10 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center text-accent">
            <BookOpen className="w-5 h-5" />
          </div>
        </div>

        <div className="p-4 rounded-xl bg-surface border border-border flex items-center justify-between">
          <div>
            <span className="text-[11px] font-mono uppercase tracking-wider text-emerald-500">Solved</span>
            <div className="text-2xl font-bold font-serif text-emerald-500 mt-0.5">
              {analytics?.solved_count || 0}
            </div>
            <span className="text-xs text-text-muted">
              {analytics?.total_questions ? Math.round(((analytics.solved_count || 0) / analytics.total_questions) * 100) : 0}% of question bank
            </span>
          </div>
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-500">
            <CheckCircle2 className="w-5 h-5" />
          </div>
        </div>

        <div className="p-4 rounded-xl bg-surface border border-border flex items-center justify-between">
          <div>
            <span className="text-[11px] font-mono uppercase tracking-wider text-text-muted">Overall Accuracy</span>
            <div className="text-2xl font-bold font-serif text-text mt-0.5">
              {analytics?.accuracy !== undefined ? `${analytics.accuracy}%` : '—'}
            </div>
            <span className="text-xs text-text-muted">Based on evaluated submissions</span>
          </div>
          <div className="w-10 h-10 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-500">
            <Sparkles className="w-5 h-5" />
          </div>
        </div>

        <div className="p-4 rounded-xl bg-surface border border-border flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono uppercase tracking-wider text-text-muted">Quick Practice</span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-accent/10 text-accent">Interactive</span>
          </div>
          <div className="flex items-center gap-2 mt-2">
            <button
              type="button"
              onClick={handlePickRandom}
              className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-surface hover:bg-surface-hover text-xs font-medium text-text cursor-pointer transition-colors shadow-xs"
            >
              <Shuffle className="w-3.5 h-3.5 text-accent" />
              <span>Random</span>
            </button>
            <button
              type="button"
              onClick={() => { setQuizInitialTopic(undefined); setQuizModalOpen(true); }}
              className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent text-accent-contrast text-xs font-medium cursor-pointer hover:bg-accent-hover transition-colors shadow-xs"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Quiz</span>
            </button>
          </div>
        </div>
      </div>

      {/* 2. Featured Broad Topics Grid (9 Broad Subject Cards) */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-accent" />
            <h2 className="text-sm font-semibold font-serif text-text tracking-tight uppercase">
              Featured Broad Subjects ({broadTopics.length})
            </h2>
          </div>
          {selectedTopics.length > 0 && (
            <button
              type="button"
              onClick={() => setSelectedTopics([])}
              className="text-xs font-mono text-accent hover:underline cursor-pointer"
            >
              Clear Topic Filter ({selectedTopics.length} active)
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
          {broadTopics.map(topic => (
            <MCQTopicCard
              key={topic.id}
              topic={topic}
              isSelected={selectedTopics.includes(topic.id)}
              onSelect={handleTopicCardClick}
              onStartQuiz={handleStartTopicQuiz}
            />
          ))}
        </div>
      </div>

      {/* 3. Search & Multi-Topic Filter Controls */}
      <div className="p-4 rounded-xl bg-surface border border-border space-y-3">
        <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
          {/* Search Input */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-text-muted absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }}
              placeholder="Search by question, code snippet, options, or subpart..."
              className="w-full pl-9 pr-8 py-2 rounded-lg border border-border bg-bg text-text text-xs focus:outline-hidden focus:border-accent font-sans"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-muted hover:text-text"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Multiple Topic Selector Dropdown */}
          <div className="relative shrink-0">
            <button
              type="button"
              onClick={() => setTopicDropdownOpen(!topicDropdownOpen)}
              className="w-full md:w-auto inline-flex items-center justify-between gap-2 px-3 py-2 rounded-lg border border-border bg-bg hover:bg-surface text-xs font-medium text-text cursor-pointer transition-colors"
            >
              <div className="flex items-center gap-1.5 truncate max-w-[200px]">
                <Layers className="w-3.5 h-3.5 text-accent" />
                <span>
                  {selectedTopics.length === 0
                    ? 'All Broad Topics'
                    : selectedTopics.length === 1
                    ? broadTopics.find(t => t.id === selectedTopics[0])?.name || '1 Topic'
                    : `${selectedTopics.length} Topics Selected`}
                </span>
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-text-muted" />
            </button>

            {topicDropdownOpen && (
              <div className="absolute right-0 mt-1.5 w-72 p-2 bg-surface border border-border rounded-xl shadow-xl z-30 space-y-1 animate-in fade-in zoom-in-95 duration-100">
                <div className="flex items-center justify-between px-2 py-1 text-[11px] font-mono text-text-muted border-b border-border/60">
                  <span>Filter Multiple Topics</span>
                  {selectedTopics.length > 0 && (
                    <button
                      type="button"
                      onClick={() => setSelectedTopics([])}
                      className="text-accent hover:underline cursor-pointer"
                    >
                      Clear
                    </button>
                  )}
                </div>
                <div className="max-h-60 overflow-y-auto space-y-0.5 pt-1">
                  {broadTopics.map(t => {
                    const checked = selectedTopics.includes(t.id);
                    return (
                      <button
                        key={t.id}
                        type="button"
                        onClick={() => toggleTopicMulti(t.id)}
                        className={`w-full px-2.5 py-1.5 rounded-lg text-left text-xs flex items-center justify-between cursor-pointer transition-colors ${
                          checked ? 'bg-accent/10 text-text font-medium' : 'text-text-muted hover:bg-surface-hover hover:text-text'
                        }`}
                      >
                        <span className="truncate">{t.name}</span>
                        {checked && <Check className="w-3.5 h-3.5 text-accent shrink-0 ml-1" />}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Filter Pills Row */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-border/60">
          <div className="flex flex-wrap items-center gap-2 text-xs">
            {/* Difficulty Pills */}
            <div className="flex items-center gap-1 bg-bg p-0.5 rounded-lg border border-border">
              {['all', 'Easy', 'Medium', 'Hard'].map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => { setDifficulty(d); setPage(1); }}
                  className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors cursor-pointer capitalize ${
                    difficulty === d
                      ? 'bg-text text-bg shadow-2xs'
                      : 'text-text-muted hover:text-text'
                  }`}
                >
                  {d}
                </button>
              ))}
            </div>

            {/* Status Pills */}
            <div className="flex items-center gap-1 bg-bg p-0.5 rounded-lg border border-border">
              {[
                { id: 'all', label: 'All Status' },
                { id: 'solved', label: 'Solved' },
                { id: 'attempted', label: 'Attempted' },
                { id: 'todo', label: 'Todo' }
              ].map((st) => (
                <button
                  key={st.id}
                  type="button"
                  onClick={() => { setStatus(st.id); setPage(1); }}
                  className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors cursor-pointer ${
                    status === st.id
                      ? 'bg-text text-bg shadow-2xs'
                      : 'text-text-muted hover:text-text'
                  }`}
                >
                  {st.label}
                </button>
              ))}
            </div>

            {/* Has Code Toggle */}
            <button
              type="button"
              onClick={() => { setHasCodeOnly(prev => !prev); setPage(1); }}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-[11px] font-medium transition-colors cursor-pointer ${
                hasCodeOnly
                  ? 'border-accent bg-accent/10 text-accent font-semibold'
                  : 'border-border bg-bg text-text-muted hover:text-text'
              }`}
            >
              <Code2 className="w-3.5 h-3.5" />
              <span>With Code (700)</span>
            </button>

            {/* Starred Only Toggle */}
            <button
              type="button"
              onClick={() => { setStarredOnly(prev => !prev); setPage(1); }}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-[11px] font-medium transition-colors cursor-pointer ${
                starredOnly
                  ? 'border-amber-500/50 bg-amber-500/10 text-amber-500 font-semibold'
                  : 'border-border bg-bg text-text-muted hover:text-text'
              }`}
            >
              <Star className={`w-3.5 h-3.5 ${starredOnly ? 'fill-amber-500' : ''}`} />
              <span>Bookmarked</span>
            </button>
          </div>

          {/* Reset Filters */}
          {(selectedTopics.length > 0 || difficulty !== 'all' || status !== 'all' || searchQuery || hasCodeOnly || starredOnly) && (
            <button
              type="button"
              onClick={handleResetFilters}
              className="inline-flex items-center gap-1 text-[11px] font-mono text-text-muted hover:text-text cursor-pointer transition-colors"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Reset Filters</span>
            </button>
          )}
        </div>
      </div>

      {/* 4. Questions Table / Explorer List */}
      <div className="rounded-xl border border-border bg-surface overflow-hidden shadow-xs">
        <div className="px-5 py-3.5 border-b border-border flex items-center justify-between text-xs font-mono text-text-muted bg-surface/80">
          <div className="flex items-center gap-2">
            <span>Showing {questions.length} of {totalQuestions} questions</span>
            {selectedTopics.length > 0 && (
              <span className="text-accent">• {selectedTopics.length} broad topic{selectedTopics.length > 1 ? 's' : ''} filtered</span>
            )}
          </div>
          <span className="text-[11px]">Click any question to view, answer & see code</span>
        </div>

        {loadingQuestions ? (
          <div className="py-20 flex flex-col items-center justify-center text-text-muted space-y-2">
            <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
            <p className="text-xs">Loading questions...</p>
          </div>
        ) : questions.length === 0 ? (
          <div className="py-16 text-center space-y-2">
            <AlertCircle className="w-8 h-8 text-text-muted mx-auto" />
            <p className="text-sm font-medium text-text">No questions match your current filters.</p>
            <button
              type="button"
              onClick={handleResetFilters}
              className="text-xs font-mono text-accent hover:underline cursor-pointer"
            >
              Reset all filters
            </button>
          </div>
        ) : (
          <div className="divide-y divide-border/60">
            {questions.map((q) => {
              const isSolved = q.status === 'solved' || q.is_correct;
              const isAttempted = q.status === 'attempted';

              return (
                <div
                  key={q.id}
                  onClick={() => setActiveQuestionId(q.id)}
                  className="p-4 hover:bg-surface-hover/80 transition-colors flex items-start gap-3.5 cursor-pointer group"
                >
                  {/* Status Indicator */}
                  <div className="pt-0.5 shrink-0">
                    {isSolved ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    ) : isAttempted ? (
                      <div className="w-4 h-4 rounded-full border-2 border-amber-500/80 flex items-center justify-center">
                        <div className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                      </div>
                    ) : (
                      <div className="w-4 h-4 rounded-full border border-text-muted/40" />
                    )}
                  </div>

                  {/* Question Main Content */}
                  <div className="flex-1 min-w-0 space-y-1.5">
                    {/* Top Row: Broad Topic Badge, Subpart, Difficulty, ID */}
                    <div className="flex flex-wrap items-center gap-2 text-[11px]">
                      <span className="font-mono text-text-muted text-[11px] font-medium">
                        {q.id}
                      </span>
                      <span className="px-2 py-0.2 rounded font-medium bg-surface-hover border border-border text-text">
                        {q.broad_topic_name}
                      </span>
                      <span className="text-text-muted/60">•</span>
                      <span className="text-text-muted truncate max-w-[220px]">
                        {q.subpart_name}
                      </span>

                      {q.has_code && (
                        <span className="inline-flex items-center gap-1 px-1.5 py-0.2 rounded bg-accent/10 text-accent font-mono text-[10px]">
                          <Code2 className="w-3 h-3" />
                          <span>Code</span>
                        </span>
                      )}

                      <span className={`px-2 py-0.2 rounded text-[10px] font-medium border ml-auto ${getDifficultyBadge(q.difficulty)}`}>
                        {q.difficulty}
                      </span>
                    </div>

                    {/* Question text preview */}
                    <div className="text-sm font-sans text-text group-hover:text-accent transition-colors line-clamp-2 leading-relaxed">
                      {q.question}
                    </div>
                  </div>

                  {/* Bookmark Star button */}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      api.toggleMCQStar(q.id).then(res => {
                        setQuestions(prev => prev.map(item => item.id === q.id ? { ...item, is_starred: res.is_starred } : item));
                      });
                    }}
                    className={`p-1.5 rounded-lg transition-colors cursor-pointer shrink-0 ${
                      q.is_starred ? 'text-amber-500' : 'text-text-muted/40 hover:text-text hover:bg-surface'
                    }`}
                    title={q.is_starred ? 'Starred' : 'Bookmark'}
                  >
                    <Star className={`w-4 h-4 ${q.is_starred ? 'fill-amber-500' : ''}`} />
                  </button>
                </div>
              );
            })}
          </div>
        )}

        {/* 5. Pagination Bar */}
        {totalPages > 1 && (
          <div className="px-5 py-3 border-t border-border flex items-center justify-between text-xs bg-surface shrink-0">
            <span className="text-text-muted font-mono">
              Page {page} of {totalPages}
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage(prev => Math.max(1, prev - 1))}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-border bg-surface hover:bg-surface-hover text-xs font-medium text-text cursor-pointer disabled:opacity-40"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>Prev</span>
              </button>
              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => setPage(prev => Math.min(totalPages, prev + 1))}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-border bg-surface hover:bg-surface-hover text-xs font-medium text-text cursor-pointer disabled:opacity-40"
              >
                <span>Next</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Interactive Question Solver Modal */}
      {activeQuestionId && (
        <MCQQuestionModal
          questionId={activeQuestionId}
          onClose={() => setActiveQuestionId(null)}
          onNavigateQuestion={handleNavigateModal}
          onPickRandom={handlePickRandom}
          onStatusUpdated={handleModalStatusUpdated}
        />
      )}

      {/* Quiz Modal */}
      {quizModalOpen && (
        <MCQQuizModal
          broadTopics={broadTopics}
          initialTopicId={quizInitialTopic}
          onClose={() => setQuizModalOpen(false)}
          onQuizCompleted={loadMetadata}
        />
      )}
    </div>
  );
};
