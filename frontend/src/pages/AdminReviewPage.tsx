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
          <div className="inline-flex items-center gap-2 text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-2">
            <ShieldCheck className="w-4 h-4" />
            Subsystem A • Agent 4
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight">
            18-Point Question Validation Queue
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Every question must satisfy all 18 validation checkpoints before being published into the Question Bank.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-800 p-1 rounded-xl text-xs">
            {['ALL', 'PUBLISHED', 'REVIEWING', 'FAILED'].map((st) => (
              <button
                key={st}
                onClick={() => setFilterStatus(st)}
                className={`px-3 py-1 rounded-lg font-medium transition-all ${
                  filterStatus === st
                    ? 'bg-brand-600 text-white'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {st}
              </button>
            ))}
          </div>

          <button
            onClick={loadQueue}
            className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white"
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
                    ? 'bg-slate-900 border-brand-500 shadow-sm shadow-brand-500/10'
                    : 'bg-slate-950/60 border-slate-800/80 hover:bg-slate-900/60'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded uppercase bg-slate-800 text-slate-300 font-bold">
                    {item.question_type}
                  </span>
                  <span
                    className={`text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded ${
                      isPublished
                        ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                        : 'bg-amber-950 text-amber-300 border border-amber-800'
                    }`}
                  >
                    {item.status}
                  </span>
                </div>

                <h3 className="text-xs font-bold text-white line-clamp-1">
                  {item.title || item.subtopic}
                </h3>
                <p className="text-[11px] text-slate-400 line-clamp-2">
                  {item.prompt}
                </p>

                <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 border-t border-slate-800/60 font-mono">
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
            <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-6">
              {/* Question Header */}
              <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-brand-950 text-brand-300 border border-brand-800">
                      {selectedItem.question_type}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-amber-950 text-amber-300 border border-amber-800">
                      {selectedItem.difficulty}
                    </span>
                    <span className="text-xs text-slate-400">{selectedItem.topic}</span>
                  </div>
                  <h2 className="text-xl font-bold text-white mt-1.5">
                    {selectedItem.title || selectedItem.subtopic}
                  </h2>
                </div>

                {/* Approve / Reject Actions */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleReject(selectedItem.id)}
                    disabled={actionLoading}
                    className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-rose-950 hover:bg-rose-900 text-rose-300 border border-rose-800 flex items-center gap-1.5 transition-colors"
                  >
                    <X className="w-3.5 h-3.5" />
                    Reject
                  </button>

                  <button
                    onClick={() => handleApprove(selectedItem.id)}
                    disabled={actionLoading}
                    className="px-4 py-2 rounded-xl text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white flex items-center gap-1.5 transition-colors shadow-sm"
                  >
                    <Check className="w-3.5 h-3.5" />
                    Approve & Publish
                  </button>
                </div>
              </div>

              {/* Prompt Preview */}
              <div>
                <span className="text-xs font-bold text-slate-300 block mb-1">Question Prompt:</span>
                <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-200 whitespace-pre-wrap">
                  {selectedItem.prompt}
                </div>
              </div>

              {/* 18-Point Verification Checklist Breakdown */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                    Agent 4 Verification Checklist (18 Checkpoints)
                  </h3>
                  <span className="text-xs font-mono font-bold text-emerald-400">
                    {selectedItem.review_report.passed_checks_count || 18} / 18 Checkpoints Passed
                  </span>
                </div>

                <div className="grid sm:grid-cols-2 gap-2.5">
                  {Object.entries(selectedItem.review_report.checklist || {}).map(([key, passed], idx) => {
                    const cleanKey = key.replace(/_/g, ' ').replace(/^\d+\s*/, '');

                    return (
                      <div
                        key={idx}
                        className={`p-2.5 rounded-xl border text-xs flex items-center justify-between ${
                          passed
                            ? 'bg-slate-950/60 border-emerald-900/40 text-slate-300'
                            : 'bg-rose-950/40 border-rose-800 text-rose-300'
                        }`}
                      >
                        <span className="capitalize">{cleanKey}</span>
                        {passed ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 ml-2" />
                        ) : (
                          <XCircle className="w-4 h-4 text-rose-400 shrink-0 ml-2" />
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Auditor Notes */}
              {selectedItem.review_report.notes && (
                <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-xs space-y-1">
                  <span className="font-bold text-slate-400">Review Notes:</span>
                  <ul className="list-disc list-inside text-slate-400">
                    {selectedItem.review_report.notes.map((note, nIdx) => (
                      <li key={nIdx}>{note}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="p-12 text-center rounded-2xl border border-dashed border-slate-800 text-slate-500">
              Select a question to inspect its 18-point verification report.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
