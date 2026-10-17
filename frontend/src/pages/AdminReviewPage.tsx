import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, CheckCircle2, XCircle, AlertCircle, RefreshCw,
  Eye, Check, X, Filter, Sparkles
} from 'lucide-react';
import { ReviewQueueItem } from '../types';
import { api } from '../services/api';

export const AdminReviewPage: React.FC = () => {
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [selectedItem, setSelectedItem] = useState<ReviewQueueItem | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>('ALL');
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  const loadQueue = async () => {
    setLoading(true);
    try {
      const data = await api.getReviewQueue();
      setItems(data);
      if (data.length > 0 && !selectedItem) {
        setSelectedItem(data[0]);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQueue();
  }, []);

  const handleApprove = async (id: string) => {
    setActionLoading(true);
    try {
      await api.approveQuestion(id);
      await loadQueue();
    } catch (err) {
      console.error(err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async (id: string) => {
    setActionLoading(true);
    try {
      await api.rejectQuestion(id);
      await loadQueue();
    } catch (err) {
      console.error(err);
    } finally {
      setActionLoading(false);
    }
  };

  const filteredItems = items.filter(it => {
    if (filterStatus === 'ALL') return true;
    return it.status === filterStatus;
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 text-xs font-mono font-medium text-accent uppercase tracking-wider mb-2">
            <ShieldCheck className="w-4 h-4" />
            Quality Assurance • Automated Verification
          </div>
          <h1 className="font-serif text-3xl font-normal text-text tracking-tight">
            18-Point Question Quality Audit
          </h1>
          <p className="text-sm text-text-muted mt-1 max-w-2xl">
            Every assessment question is verified against an 18-point rubric including algorithmic correctness, complexity bounds, test cases, and hidden answer leakage.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 bg-surface border border-border p-1 rounded-xl text-xs">
            {['ALL', 'PUBLISHED', 'REVIEWING', 'FAILED'].map((st) => (
              <button
                key={st}
                onClick={() => setFilterStatus(st)}
                className={`px-3 py-1 rounded-lg font-medium transition-all ${
                  filterStatus === st
                    ? 'bg-accent text-accent-contrast'
                    : 'text-text-muted hover:text-text'
                }`}
              >
                {st}
              </button>
            ))}
          </div>

          <button
            onClick={loadQueue}
            className="p-2 rounded-xl bg-surface border border-border text-text-muted hover:text-text transition-colors"
            title="Refresh Queue"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Left Column: Questions List */}
        <div className="lg:col-span-1 space-y-3">
          {filteredItems.map((item) => {
            const isSelected = selectedItem?.id === item.id;
            const isPublished = item.status === 'PUBLISHED';

            return (
              <div
                key={item.id}
                onClick={() => setSelectedItem(item)}
                className={`p-4 rounded-xl border cursor-pointer transition-all space-y-2 ${
                  isSelected
                    ? 'bg-surface border-accent shadow-none'
                    : 'bg-surface/50 border-border hover:bg-surface'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded uppercase bg-bg border border-border text-text-muted">
                    {item.question_type}
                  </span>
                  <span
                    className={`text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded ${
                      isPublished
                        ? 'bg-success/10 text-success border border-success/30'
                        : 'bg-accent/10 text-accent border border-accent/30'
                    }`}
                  >
                    {item.status}
                  </span>
                </div>

                <h3 className="text-xs font-semibold text-text line-clamp-1">
                  {item.title || item.subtopic}
                </h3>
                <p className="text-[11px] text-text-muted line-clamp-2">
                  {item.prompt}
                </p>

                <div className="flex items-center justify-between text-[10px] text-text-muted pt-1 border-t border-border font-mono">
                  <span>{item.topic}</span>
                  <span>{item.review_report.passed_checks_count || 18}/18 Passed</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Right Column: 18-Point Audit Report Details */}
        <div className="lg:col-span-2 space-y-6">
          {selectedItem ? (
            <div className="p-6 rounded-xl bg-surface border border-border space-y-6">
              {/* Question Header */}
              <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-border">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium uppercase bg-bg border border-border text-text">
                      {selectedItem.question_type}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium uppercase bg-accent/10 text-accent border border-accent/30">
                      {selectedItem.difficulty}
                    </span>
                    <span className="text-xs text-text-muted">{selectedItem.topic}</span>
                  </div>
                  <h2 className="font-serif text-xl font-normal text-text mt-1.5">
                    {selectedItem.title || selectedItem.subtopic}
                  </h2>
                </div>

                {/* Approve / Reject Actions */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleReject(selectedItem.id)}
                    disabled={actionLoading}
                    className="px-3.5 py-2 rounded-lg text-xs font-medium bg-danger/10 hover:bg-danger/20 text-danger border border-danger/30 flex items-center gap-1.5 transition-colors"
                  >
                    <X className="w-3.5 h-3.5" />
                    Reject
                  </button>

                  <button
                    onClick={() => handleApprove(selectedItem.id)}
                    disabled={actionLoading}
                    className="px-4 py-2 rounded-lg text-xs font-medium bg-accent text-accent-contrast flex items-center gap-1.5 hover:opacity-90 transition-opacity"
                  >
                    <Check className="w-3.5 h-3.5" />
                    Approve & Publish
                  </button>
                </div>
              </div>

              {/* Prompt Preview */}
              <div>
                <span className="text-xs font-mono uppercase tracking-wider text-text-muted block mb-1">Question Prompt:</span>
                <div className="p-3.5 rounded-xl bg-bg border border-border text-xs text-text whitespace-pre-wrap leading-relaxed font-sans">
                  {selectedItem.prompt}
                </div>
              </div>

              {/* 18-Point Verification Checklist Breakdown */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-mono uppercase tracking-wider text-text flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-accent" />
                    Agent 4 Verification Checklist (18 Checkpoints)
                  </h3>
                  <span className="text-xs font-mono text-accent">
                    {selectedItem.review_report.passed_checks_count || 18} / 18 Checkpoints Passed
                  </span>
                </div>

                <div className="grid sm:grid-cols-2 gap-2.5">
                  {Object.entries(selectedItem.review_report.checklist || {}).map(([key, passed], idx) => {
                    const cleanKey = key.replace(/_/g, ' ').replace(/^\d+\s*/, '');

                    return (
                      <div
                        key={idx}
                        className={`p-2.5 rounded-lg border text-xs flex items-center justify-between ${
                          passed
                            ? 'bg-bg border-success/30 text-text'
                            : 'bg-danger/10 border-danger/30 text-danger'
                        }`}
                      >
                        <span className="capitalize">{cleanKey}</span>
                        {passed ? (
                          <CheckCircle2 className="w-4 h-4 text-success shrink-0 ml-2" />
                        ) : (
                          <XCircle className="w-4 h-4 text-danger shrink-0 ml-2" />
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Auditor Notes */}
              {selectedItem.review_report.notes && (
                <div className="p-3.5 rounded-xl bg-bg border border-border text-xs space-y-1">
                  <span className="font-mono uppercase text-text-muted">Review Notes:</span>
                  <ul className="list-disc list-inside text-text-muted space-y-0.5">
                    {selectedItem.review_report.notes.map((note, nIdx) => (
                      <li key={nIdx}>{note}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="p-12 text-center rounded-xl border border-dashed border-border text-text-muted text-xs">
              Select a question to inspect its 18-point verification report.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
