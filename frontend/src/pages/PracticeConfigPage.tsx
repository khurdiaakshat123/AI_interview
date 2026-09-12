import React, { useState, useEffect } from 'react';
import { 
  Code2, Sliders, CheckSquare, Sparkles, Hash, ArrowRight, Layers
} from 'lucide-react';
import { RoleTopicProfile } from '../types';
import { api } from '../services/api';

interface PracticeConfigPageProps {
  initialCompany?: string;
  initialRole?: string;
  onNavigate: (tab: string, state?: any) => void;
}

export const PracticeConfigPage: React.FC<PracticeConfigPageProps> = ({
  initialCompany = 'Google',
  initialRole = 'Software Engineer II (L4)',
  onNavigate
}) => {
  const [company, setCompany] = useState(initialCompany);
  const [role, setRole] = useState(initialRole);
  const [profiles, setProfiles] = useState<RoleTopicProfile[]>([]);
  const [selectedTopics, setSelectedTopics] = useState<string[]>([
    'Sliding Window & Two Pointers',
    'Graphs & Shortest Path',
    'SQL & Query Optimization',
    'Distributed Storage & Caching'
  ]);
  const [proficiencyVector, setProficiencyVector] = useState<Record<string, string>>({
    'Sliding Window & Two Pointers': 'intermediate',
    'Graphs & Shortest Path': 'advanced',
    'SQL & Query Optimization': 'intermediate',
    'Distributed Storage & Caching': 'intermediate'
  });
  const [totalQuestions, setTotalQuestions] = useState(5);
  const [allocationMode, setAllocationMode] = useState<'auto' | 'manual'>('auto');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function loadData() {
      try {
        const list = await api.getRoleProfiles();
        setProfiles(list);
      } catch (err) {
        console.error(err);
      }
    }
    loadData();
  }, []);

  const handleTopicToggle = (topic: string) => {
    if (selectedTopics.includes(topic)) {
      setSelectedTopics(selectedTopics.filter(t => t !== topic));
    } else {
      setSelectedTopics([...selectedTopics, topic]);
      if (!proficiencyVector[topic]) {
        setProficiencyVector({ ...proficiencyVector, [topic]: 'intermediate' });
      }
    }
  };

  const handleProficiencyChange = (topic: string, level: string) => {
    setProficiencyVector({ ...proficiencyVector, [topic]: level });
  };

  const handleStartPractice = async () => {
    setLoading(true);
    try {
      const session = await api.createPracticeSession({
        company,
        role,
        selected_topics: selectedTopics,
        proficiency_vector: proficiencyVector,
        total_questions: totalQuestions,
        allocation_mode: allocationMode
      });
      onNavigate('practice-runner', { session });
    } catch (err) {
      console.error(err);
      alert('Failed to initialize practice session.');
    } finally {
      setLoading(false);
    }
  };

  const availableTopics = [
    'Sliding Window & Two Pointers',
    'Graphs & Shortest Path',
    'Trees & Binary Search Trees',
    'Dynamic Programming & Memoization',
    'SQL & Query Optimization',
    'Distributed Storage & Caching',
    'High-Throughput Messaging & Queues',
    'Operating Systems & Concurrency'
  ];

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-2 text-xs font-semibold text-sky-400 uppercase tracking-wider mb-2">
          <Code2 className="w-4 h-4" />
          Coding & System Design Practice
        </div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight">
          Targeted Skill Practice
        </h1>
        <p className="text-sm text-slate-300 mt-1">
          Select target topics, set your current proficiency level, and generate tailored questions with hints, code templates, and automated tests.
        </p>
      </div>

      <div className="p-6 sm:p-8 rounded-2xl bg-slate-900/80 border border-white/10 shadow-xl space-y-6">
        {/* Company & Role Target */}
        <div className="grid sm:grid-cols-2 gap-4 pb-6 border-b border-slate-800">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Company Target</label>
            <input
              type="text"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:border-brand-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Role Title</label>
            <input
              type="text"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:border-brand-500 focus:outline-none"
            />
          </div>
        </div>

        {/* Allocation Mode & Total Questions */}
        <div className="grid sm:grid-cols-2 gap-6 pb-6 border-b border-slate-800">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-2">Question Count</label>
            <div className="flex items-center gap-2">
              {[3, 5, 8, 10].map((num) => (
                <button
                  key={num}
                  type="button"
                  onClick={() => setTotalQuestions(num)}
                  className={`flex-1 py-2 rounded-xl text-xs font-semibold font-mono transition-all ${
                    totalQuestions === num
                      ? 'bg-brand-600 text-white shadow-sm'
                      : 'bg-slate-950 border border-slate-800 text-slate-400 hover:text-white'
                  }`}
                >
                  {num} Qs
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-2">Allocation Mode</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setAllocationMode('auto')}
                className={`py-2 px-3 rounded-xl text-xs font-semibold text-center transition-all ${
                  allocationMode === 'auto'
                    ? 'bg-brand-600 text-white shadow-sm'
                    : 'bg-slate-950 border border-slate-800 text-slate-400 hover:text-white'
                }`}
              >
                Auto (Weighted)
              </button>
              <button
                type="button"
                onClick={() => setAllocationMode('manual')}
                className={`py-2 px-3 rounded-xl text-xs font-semibold text-center transition-all ${
                  allocationMode === 'manual'
                    ? 'bg-brand-600 text-white shadow-sm'
                    : 'bg-slate-950 border border-slate-800 text-slate-400 hover:text-white'
                }`}
              >
                Manual Equal
              </button>
            </div>
          </div>
        </div>

        {/* Topics & Per-Topic Proficiency Sliders */}
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-3">
            Select Topics & Target Proficiency
          </label>

          <div className="space-y-3">
            {availableTopics.map((top) => {
              const isSelected = selectedTopics.includes(top);
              const currentLevel = proficiencyVector[top] || 'intermediate';

              return (
                <div
                  key={top}
                  className={`p-3.5 rounded-xl border transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                    isSelected
                      ? 'bg-slate-950/80 border-brand-500/40'
                      : 'bg-slate-950/40 border-slate-800/80 opacity-70'
                  }`}
                >
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => handleTopicToggle(top)}
                      className="w-4 h-4 rounded border-slate-700 bg-slate-900 text-brand-600 focus:ring-0 focus:ring-offset-0 cursor-pointer"
                    />
                    <span className="text-xs font-semibold text-slate-200">{top}</span>
                  </label>

                  {isSelected && (
                    <div className="flex items-center gap-1.5 self-end sm:self-auto">
                      {['beginner', 'intermediate', 'advanced'].map((lvl) => (
                        <button
                          key={lvl}
                          type="button"
                          onClick={() => handleProficiencyChange(top, lvl)}
                          className={`px-2.5 py-1 rounded-lg text-[11px] font-medium capitalize transition-all ${
                            currentLevel === lvl
                              ? 'bg-brand-600/30 text-brand-300 border border-brand-500/40'
                              : 'text-slate-500 hover:text-slate-300'
                          }`}
                        >
                          {lvl}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Action Button */}
        <div className="pt-4">
          <button
            onClick={handleStartPractice}
            disabled={loading || selectedTopics.length === 0}
            className="w-full py-3.5 rounded-xl text-xs font-bold bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50 text-white flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/25 transition-all active:scale-[0.98]"
          >
            {loading ? 'Preparing Practice Set...' : 'Launch Practice Session'}
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
