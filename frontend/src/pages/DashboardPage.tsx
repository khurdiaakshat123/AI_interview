import React, { useState, useEffect } from 'react';
import { 
  Building2, Briefcase, Clock, Trophy, ArrowRight,
  Code2, Cpu, CheckCircle2, ChevronRight, Layers, UserPlus
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
    <div className="max-w-[1100px] mx-auto px-4 sm:px-6 py-8 sm:py-10 space-y-8">
      {/* Top Welcome Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 sm:p-8 rounded-[12px] bg-surface border border-border">
        <div>
          <span className="text-[12px] font-mono uppercase tracking-[0.06em] text-accent block mb-1">
            Target Preparation
          </span>
          <h1 className="font-serif text-3xl sm:text-4xl text-text font-normal tracking-tight">
            Candidate Command Center
          </h1>
          <p className="text-[14px] text-text-muted mt-1 max-w-xl">
            Track rolling assessment windows, practice high-priority topics, and sit realistic 1-on-1 interview simulations.
          </p>
        </div>

        {/* Company & Role Selector + Custom Candidate Button */}
        <div className="flex flex-wrap items-center gap-3">
          {onOpenCandidateSetup && (
            <button
              onClick={onOpenCandidateSetup}
              className="flex items-center gap-2 h-9 px-3.5 rounded-md border border-border bg-bg hover:bg-surface-hover text-text text-xs font-medium transition-colors"
            >
              <UserPlus className="w-3.5 h-3.5 text-text-muted" />
              <span>New Candidate / JD</span>
            </button>
          )}

          <div className="flex items-center gap-2 bg-bg border border-border px-3 py-1.5 rounded-md text-xs">
            <Building2 className="w-3.5 h-3.5 text-text-muted" />
            <select
              value={selectedCompany}
              onChange={(e) => {
                const comp = e.target.value;
                setSelectedCompany(comp);
                const match = profiles.find(p => p.company === comp);
                if (match) setSelectedRole(match.role);
              }}
              className="bg-transparent text-text font-mono text-xs focus:outline-none cursor-pointer"
            >
              {Array.from(new Set(profiles.map(p => p.company))).map(comp => (
                <option key={comp} value={comp} className="bg-surface text-text">
                  {comp}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2 bg-bg border border-border px-3 py-1.5 rounded-md text-xs">
            <Briefcase className="w-3.5 h-3.5 text-text-muted" />
            <select
              value={selectedRole}
              onChange={(e) => setSelectedRole(e.target.value)}
              className="bg-transparent text-text font-mono text-xs focus:outline-none cursor-pointer"
            >
              {profiles.filter(p => p.company === selectedCompany).map(p => (
                <option key={p.id} value={p.role} className="bg-surface text-text">
                  {p.role}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-[12px] bg-surface border border-border">
          <div className="flex items-center justify-between text-text-muted text-[11px] font-mono uppercase tracking-[0.04em] mb-2">
            <span>Assessment Window</span>
            <Clock className="w-3.5 h-3.5 text-text-muted" />
          </div>
          <div className="text-2xl font-mono text-text">7 Days</div>
          <div className="text-[11px] text-success font-mono mt-1 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-success" />
            Active 7-Day Cycle
          </div>
        </div>

        <div className="p-5 rounded-[12px] bg-surface border border-border">
          <div className="flex items-center justify-between text-text-muted text-[11px] font-mono uppercase tracking-[0.04em] mb-2">
            <span>Project Defense</span>
            <Trophy className="w-3.5 h-3.5 text-accent" />
          </div>
          <div className="text-2xl font-mono text-text">82.5 <span className="text-xs text-text-muted font-normal">/ 100</span></div>
          <div className="text-[11px] text-text-muted font-mono mt-1">
            4.1 / 5.0 Rating
          </div>
        </div>

        <div className="p-5 rounded-[12px] bg-surface border border-border">
          <div className="flex items-center justify-between text-text-muted text-[11px] font-mono uppercase tracking-[0.04em] mb-2">
            <span>Subject Knowledge</span>
            <Cpu className="w-3.5 h-3.5 text-accent" />
          </div>
          <div className="text-2xl font-mono text-text">86.0 <span className="text-xs text-text-muted font-normal">/ 100</span></div>
          <div className="text-[11px] text-text-muted font-mono mt-1">
            Strong: Systems, Caching
          </div>
        </div>

        <div className="p-5 rounded-[12px] bg-surface border border-border">
          <div className="flex items-center justify-between text-text-muted text-[11px] font-mono uppercase tracking-[0.04em] mb-2">
            <span>Quality Verification</span>
            <CheckCircle2 className="w-3.5 h-3.5 text-success" />
          </div>
          <div className="text-2xl font-mono text-text">100%</div>
          <div className="text-[11px] text-text-muted font-mono mt-1">
            18/18 Standards Verified
          </div>
        </div>
      </div>

      {/* Main Action Hub & Topic Priority Overview */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Role Topic Profile Preview */}
        <div className="lg:col-span-2 space-y-6">
          <div className="p-6 sm:p-7 rounded-[12px] bg-surface border border-border">
            <div className="flex items-center justify-between mb-5 pb-3 border-b border-border">
              <div>
                <h2 className="text-[18px] font-semibold text-text tracking-tight font-sans">
                  Target Role Topics & Priority Weightings
                </h2>
                <p className="text-xs text-text-muted mt-0.5">
                  Curated for {selectedCompany} engineering expectations.
                </p>
              </div>

              <button
                onClick={() => onNavigate('jd-intake', { company: selectedCompany, role: selectedRole })}
                className="text-xs font-mono text-accent hover:underline flex items-center gap-1"
              >
                Inspect Details
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Subjects and Topics */}
            <div className="space-y-4">
              {currentProfile?.subjects.map((sub, idx) => (
                <div key={idx} className="p-4 rounded-md bg-bg border border-border">
                  <div className="text-[11px] font-mono uppercase tracking-wider text-text-muted mb-3 flex items-center gap-2">
                    <Layers className="w-3.5 h-3.5 text-accent" />
                    {sub.subject}
                  </div>

                  <div className="space-y-2.5">
                    {sub.topics.slice(0, 3).map((top, tIdx) => (
                      <div key={tIdx} className="space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-text font-medium">{top.topic}</span>
                          <span className="font-mono text-accent text-[11px]">
                            {Math.round(top.importance_score * 100)}% Weight
                          </span>
                        </div>
                        <div className="w-full h-1 rounded-full bg-surface overflow-hidden">
                          <div 
                            className="h-full rounded-full bg-accent"
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
          <div className="p-6 rounded-[12px] bg-surface border border-border flex flex-col justify-between">
            <div>
              <span className="text-[11px] font-mono uppercase tracking-wider text-text-muted block mb-1">
                Step 1 — Practice
              </span>
              <h3 className="text-[16px] font-semibold text-text mb-1">
                Targeted Skill Practice
              </h3>
              <p className="text-[13px] text-text-muted mb-5 leading-[1.6]">
                Hone high-frequency topics with adjustable difficulty, instant hints, step-by-step approaches, and full solutions.
              </p>
            </div>
            <button
              onClick={() => onNavigate('practice', { company: selectedCompany, role: selectedRole })}
              className="w-full h-9 rounded-md text-xs font-medium border border-border bg-transparent text-text hover:bg-surface-hover hover:border-border-focus flex items-center justify-center gap-2 transition-colors"
            >
              <span>Configure Practice Session</span>
              <ArrowRight className="w-3.5 h-3.5 text-text-muted" />
            </button>
          </div>

          {/* Card 2: Timed Mock OA */}
          <div className="p-6 rounded-[12px] bg-surface border border-border flex flex-col justify-between">
            <div>
              <span className="text-[11px] font-mono uppercase tracking-wider text-text-muted block mb-1">
                Step 2 — Timed Assessment
              </span>
              <h3 className="text-[16px] font-semibold text-text mb-1">
                Timed Coding Assessment
              </h3>
              <p className="text-[13px] text-text-muted mb-5 leading-[1.6]">
                Take a 60-minute simulated assessment synchronized with current company hiring cycles and anti-cheat verification.
              </p>
            </div>
            <button
              onClick={() => onNavigate('mock-oa', { company: selectedCompany, role: selectedRole })}
              className="w-full h-9 rounded-md text-xs font-medium border border-border bg-transparent text-text hover:bg-surface-hover hover:border-border-focus flex items-center justify-center gap-2 transition-colors"
            >
              <span>Start Timed Assessment</span>
              <ArrowRight className="w-3.5 h-3.5 text-text-muted" />
            </button>
          </div>

          {/* Card 3: AI Interview */}
          <div className="p-6 rounded-[12px] bg-surface border border-border flex flex-col justify-between">
            <div>
              <span className="text-[11px] font-mono uppercase tracking-wider text-accent block mb-1">
                Step 3 — Technical Interview
              </span>
              <h3 className="text-[16px] font-semibold text-text mb-1">
                1-on-1 AI Technical Interview
              </h3>
              <p className="text-[13px] text-text-muted mb-5 leading-[1.6]">
                Voice-enabled technical interview probing real past projects, system architecture decisions, and CS fundamentals.
              </p>
            </div>
            <button
              onClick={() => onNavigate('interview', { company: selectedCompany, role: selectedRole })}
              className="w-full h-10 rounded-md text-xs font-medium bg-accent hover:bg-accent-hover text-accent-contrast flex items-center justify-center gap-2 transition-colors"
            >
              <span>Enter Interview Room</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
