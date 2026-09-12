import React, { useState, useEffect } from 'react';
import { 
  Building2, Briefcase, Calendar, Clock, Trophy, Target, ArrowRight,
  TrendingUp, Code2, Cpu, CheckCircle2, ChevronRight, Layers, Sparkles, UserPlus
} from 'lucide-react';
import { RoleTopicProfile } from '../types';
import { api } from '../services/api';

interface DashboardPageProps {
  onNavigate: (tab: string, state?: any) => void;
  candidate?: { name: string; email: string; company: string; role: string };
  onOpenCandidateSetup?: () => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ 
  onNavigate,
  candidate = { name: "Alex Mercer", email: "alex.mercer@intervyn.ai", company: "Google", role: "Software Engineer II (L4)" },
  onOpenCandidateSetup
}) => {
  const [profiles, setProfiles] = useState<RoleTopicProfile[]>([]);
  const [selectedCompany, setSelectedCompany] = useState('Google');
  const [selectedRole, setSelectedRole] = useState('Software Engineer II (L4)');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const data = await api.getRoleProfiles();
        setProfiles(data);
        if (data.length > 0) {
          setSelectedCompany(data[0].company);
          setSelectedRole(data[0].role);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const currentProfile = profiles.find(
    p => p.company === selectedCompany && p.role === selectedRole
  ) || profiles[0];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Welcome Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 sm:p-8 rounded-2xl bg-gradient-to-r from-slate-900/90 via-slate-900 to-indigo-950/40 border border-white/10 shadow-xl shadow-black/30">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-sky-400 uppercase tracking-wider mb-1">
            <Sparkles className="w-3.5 h-3.5" />
            Active Target Preparation
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Candidate Command Center
          </h1>
          <p className="text-sm text-slate-300 mt-1">
            Track rolling assessment windows, practice high-priority topics, and conduct realistic 1-on-1 interview simulations.
          </p>
        </div>

        {/* Company & Role Selector + Custom Candidate Button */}
        <div className="flex flex-wrap items-center gap-3">
          {onOpenCandidateSetup && (
            <button
              onClick={onOpenCandidateSetup}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-bold shadow-lg shadow-indigo-600/25 transition-all active:scale-[0.98]"
            >
              <UserPlus className="w-4 h-4" />
              <span>New Candidate / Custom JD</span>
            </button>
          )}

          <div className="flex items-center gap-2 bg-slate-900/90 border border-white/10 px-3.5 py-2 rounded-xl text-xs">
            <Building2 className="w-4 h-4 text-sky-400" />
            <select
              value={selectedCompany}
              onChange={(e) => {
                const comp = e.target.value;
                setSelectedCompany(comp);
                const match = profiles.find(p => p.company === comp);
                if (match) setSelectedRole(match.role);
              }}
              className="bg-transparent text-slate-100 font-semibold focus:outline-none cursor-pointer"
            >
              {Array.from(new Set(profiles.map(p => p.company))).map(comp => (
                <option key={comp} value={comp} className="bg-slate-900 text-slate-100">
                  {comp}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2 bg-slate-900/90 border border-white/10 px-3.5 py-2 rounded-xl text-xs">
            <Briefcase className="w-4 h-4 text-indigo-400" />
            <select
              value={selectedRole}
              onChange={(e) => setSelectedRole(e.target.value)}
              className="bg-transparent text-slate-100 font-semibold focus:outline-none cursor-pointer"
            >
              {profiles.filter(p => p.company === selectedCompany).map(p => (
                <option key={p.id} value={p.role} className="bg-slate-900 text-slate-100">
                  {p.role}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-xl bg-slate-900/80 border border-white/10 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2 font-medium">
            <span>Active Assessment Window</span>
            <Clock className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">7 Days</div>
          <div className="text-xs text-emerald-400 mt-1 flex items-center gap-1.5 font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Active Cycle (Synchronized Variant #1)
          </div>
        </div>

        <div className="p-5 rounded-xl bg-slate-900/80 border border-white/10 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2 font-medium">
            <span>Project Defense Score</span>
            <Trophy className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">82.5 <span className="text-sm font-normal text-slate-400">/ 100</span></div>
          <div className="text-xs text-slate-400 mt-1">
            ★ 4.13 / 5.0 Star Rating
          </div>
        </div>

        <div className="p-5 rounded-xl bg-slate-900/80 border border-white/10 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2 font-medium">
            <span>Subject Knowledge</span>
            <Cpu className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">86.0 <span className="text-sm font-normal text-slate-400">/ 100</span></div>
          <div className="text-xs text-indigo-300 mt-1 font-medium">
            Strong: Concurrency, Caching
          </div>
        </div>

        <div className="p-5 rounded-xl bg-slate-900/80 border border-white/10 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2 font-medium">
            <span>Quality Verification</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">100%</div>
          <div className="text-xs text-slate-400 mt-1">
            18/18 Quality checkpoints passed
          </div>
        </div>
      </div>

      {/* Main Action Hub & Topic Priority Overview */}
      <div className="grid lg:grid-cols-3 gap-8">
        {/* Left 2 Cols: Role Topic Profile Preview */}
        <div className="lg:col-span-2 space-y-6">
          <div className="p-6 sm:p-7 rounded-2xl bg-slate-900/80 border border-white/10 shadow-lg">
            <div className="flex items-center justify-between mb-5">
              <div>
                <h2 className="text-lg font-bold text-white">
                  Target Role Topics & Priority Weightings
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Curated for {selectedCompany} engineering expectations and hiring bar.
                </p>
              </div>

              <button
                onClick={() => onNavigate('jd-intake', { company: selectedCompany, role: selectedRole })}
                className="text-xs font-semibold text-sky-400 hover:text-sky-300 flex items-center gap-1"
              >
                Inspect Details
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>

            {/* Subjects and Topics */}
            <div className="space-y-4">
              {currentProfile?.subjects.map((sub, idx) => (
                <div key={idx} className="p-4 rounded-xl bg-slate-950/60 border border-white/5">
                  <div className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-3 flex items-center gap-2">
                    <Layers className="w-3.5 h-3.5 text-sky-400" />
                    {sub.subject}
                  </div>

                  <div className="space-y-2.5">
                    {sub.topics.slice(0, 3).map((top, tIdx) => (
                      <div key={tIdx} className="space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-slate-300 font-medium">{top.topic}</span>
                          <span className="font-mono text-sky-400 font-semibold">
                            {Math.round(top.importance_score * 100)}% Priority
                          </span>
                        </div>
                        <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                          <div 
                            className="h-full rounded-full bg-gradient-to-r from-blue-500 to-cyan-400"
                            style={{ width: `${top.importance_score * 100}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Col: Quick Preparation Actions */}
        <div className="space-y-4">
          {/* Card 1: Practice Engine */}
          <div className="p-6 rounded-2xl bg-gradient-to-b from-slate-900 to-slate-950 border border-white/10 flex flex-col justify-between shadow-lg">
            <div>
              <div className="flex items-center gap-2 text-sky-400 text-xs font-bold uppercase tracking-wider mb-2">
                <Code2 className="w-4 h-4" />
                Step 1 — Practice
              </div>
              <h3 className="text-base font-bold text-white mb-1">
                Targeted Skill Practice
              </h3>
              <p className="text-xs text-slate-400 mb-4 leading-relaxed">
                Hone high-frequency topics with adjustable difficulty, instant hints, step-by-step approaches, and full solutions.
              </p>
            </div>
            <button
              onClick={() => onNavigate('practice', { company: selectedCompany, role: selectedRole })}
              className="w-full py-2.5 rounded-xl text-xs font-bold bg-slate-800 hover:bg-slate-700 text-sky-300 border border-sky-500/30 flex items-center justify-center gap-2 transition-all shadow-sm"
            >
              Configure Practice Session
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Card 2: Timed Mock OA */}
          <div className="p-6 rounded-2xl bg-gradient-to-b from-slate-900 to-slate-950 border border-white/10 flex flex-col justify-between shadow-lg">
            <div>
              <div className="flex items-center gap-2 text-amber-400 text-xs font-bold uppercase tracking-wider mb-2">
                <Clock className="w-4 h-4" />
                Step 2 — Timed Assessment
              </div>
              <h3 className="text-base font-bold text-white mb-1">
                Timed Coding Assessment
              </h3>
              <p className="text-xs text-slate-400 mb-4 leading-relaxed">
                Take a 60-minute simulated assessment synchronized with current company hiring cycles and anti-cheat verification.
              </p>
            </div>
            <button
              onClick={() => onNavigate('mock-oa', { company: selectedCompany, role: selectedRole })}
              className="w-full py-2.5 rounded-xl text-xs font-bold bg-amber-600 hover:bg-amber-500 text-white flex items-center justify-center gap-2 transition-all shadow-md shadow-amber-600/20"
            >
              Start Timed Assessment
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Card 3: AI Interview */}
          <div className="p-6 rounded-2xl bg-gradient-to-b from-slate-900 to-slate-950 border border-white/10 flex flex-col justify-between shadow-lg">
            <div>
              <div className="flex items-center gap-2 text-indigo-400 text-xs font-bold uppercase tracking-wider mb-2">
                <Cpu className="w-4 h-4" />
                Step 3 — Technical Interview
              </div>
              <h3 className="text-base font-bold text-white mb-1">
                1-on-1 AI Technical Interview
              </h3>
              <p className="text-xs text-slate-400 mb-4 leading-relaxed">
                Voice-enabled technical interview probing real past projects, system architecture decisions, and CS fundamentals.
              </p>
            </div>
            <button
              onClick={() => onNavigate('interview', { company: selectedCompany, role: selectedRole })}
              className="w-full py-2.5 rounded-xl text-xs font-bold bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-600 hover:from-blue-500 hover:to-indigo-500 text-white flex items-center justify-center gap-2 transition-all shadow-md shadow-indigo-600/25"
            >
              Enter Interview Room
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
