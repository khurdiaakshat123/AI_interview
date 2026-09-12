import React, { useState, useEffect } from 'react';
import { 
  Sparkles, FileText, Building2, Briefcase, CheckCircle2,
  ShieldCheck, ArrowRight, Layers, HelpCircle, Flame, BarChart3
} from 'lucide-react';
import { RoleTopicProfile } from '../types';
import { api } from '../services/api';
import { DocumentUploadInput } from '../components/DocumentUploadInput';

interface JDIntakePageProps {
  initialCompany?: string;
  initialRole?: string;
  onNavigate: (tab: string, state?: any) => void;
}

export const JDIntakePage: React.FC<JDIntakePageProps> = ({
  initialCompany = 'Google',
  initialRole = 'Software Engineer II (L4)',
  onNavigate
}) => {
  const [company, setCompany] = useState(initialCompany);
  const [role, setRole] = useState(initialRole);
  const [jobType, setJobType] = useState('Full-Time');
  const [experience, setExperience] = useState('1-3 years');
  const [jdText, setJdText] = useState('');
  const [profile, setProfile] = useState<RoleTopicProfile | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function loadDefault() {
      try {
        const list = await api.getRoleProfiles();
        const found = list.find(p => p.company === initialCompany && p.role === initialRole) || list[0];
        if (found) setProfile(found);
      } catch (err) {
        console.error(err);
      }
    }
    loadDefault();
  }, [initialCompany, initialRole]);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await api.createRoleProfile({
        company,
        role,
        job_type: jobType,
        experience_requirement: experience,
        jd_text: jdText
      });
      setProfile(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-2 text-xs font-semibold text-sky-400 uppercase tracking-wider mb-2">
          <Sparkles className="w-4 h-4" />
          Role Intelligence • Competency Mapping
        </div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight">
          Target Role Profiler & Skill Mapping
        </h1>
        <p className="text-sm text-slate-300 mt-1 max-w-2xl">
          Analyze job requirements to extract core data structures, algorithms, and system design topics prioritized by company interview frequency.
        </p>
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        {/* Left Form */}
        <div className="lg:col-span-1 space-y-6">
          <form onSubmit={handleGenerate} className="p-6 sm:p-7 rounded-2xl bg-slate-900/80 border border-white/10 shadow-xl space-y-4">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <FileText className="w-4 h-4 text-sky-400" />
              Role & JD Parameters
            </h2>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Company</label>
              <input
                type="text"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="e.g. Google, Amazon, Microsoft"
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-white/10 text-xs text-slate-100 focus:border-sky-500 focus:outline-none"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Role Title</label>
              <input
                type="text"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                placeholder="e.g. Backend SDE 2, Full Stack"
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-white/10 text-xs text-slate-100 focus:border-sky-500 focus:outline-none"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Job Type</label>
                <select
                  value={jobType}
                  onChange={(e) => setJobType(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-white/10 text-xs text-slate-100 focus:border-sky-500 focus:outline-none cursor-pointer"
                >
                  <option value="Full-Time">Full-Time</option>
                  <option value="Contract">Contract</option>
                  <option value="Internship">Internship</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Experience</label>
                <select
                  value={experience}
                  onChange={(e) => setExperience(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-white/10 text-xs text-slate-100 focus:border-sky-500 focus:outline-none cursor-pointer"
                >
                  <option value="0-1 years">0-1 years</option>
                  <option value="1-3 years">1-3 years</option>
                  <option value="3-5 years">3-5 years</option>
                  <option value="5+ years">5+ years</option>
                </select>
              </div>
            </div>

            <DocumentUploadInput
              label="Target Job Description (JD)"
              sublabel="Upload PDF job specs, JD screenshots (PNG/JPG), or paste raw text"
              value={jdText}
              onChange={setJdText}
              placeholder="Paste requirements, tech stack, and responsibilities, or upload a PDF/screenshot..."
              rows={5}
              badgeColor="brand"
            />

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-xl text-xs font-bold bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50 text-white flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/25 transition-all active:scale-[0.98]"
            >
              {loading ? 'Analyzing Job Requirements...' : 'Generate Target Role Profile'}
              <Sparkles className="w-3.5 h-3.5" />
            </button>
          </form>

          {/* Action Callout */}
          {profile && (
            <div className="p-5 rounded-2xl bg-gradient-to-b from-indigo-950/40 to-slate-900 border border-indigo-500/20 shadow-md space-y-3">
              <div className="text-xs font-bold text-sky-300 uppercase tracking-wider">
                Next Preparation Step
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                Role competencies are mapped and synced across your Practice Engine, Timed Assessments, and 1-on-1 Interview loop.
              </p>
              <button
                onClick={() => onNavigate('practice', { company: profile.company, role: profile.role })}
                className="w-full py-2.5 rounded-xl text-xs font-bold bg-slate-800 hover:bg-slate-700 text-sky-300 border border-sky-500/30 flex items-center justify-center gap-1.5 transition-all shadow-sm"
              >
                Start Targeted Practice
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>

        {/* Right Details: Subjects, Topics, Evidence Provenance */}
        <div className="lg:col-span-2 space-y-6">
          {profile ? (
            <div className="space-y-6">
              {/* Header card */}
              <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-wrap items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-lg font-bold text-white">{profile.company}</span>
                    <span className="text-slate-500">•</span>
                    <span className="text-sm text-brand-300 font-medium">{profile.role}</span>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 mt-2">
                    {profile.required_skills.slice(0, 6).map((skill, i) => (
                      <span key={i} className="px-2 py-0.5 rounded-md bg-slate-800 text-[11px] text-slate-300 border border-slate-700">
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="text-right text-xs text-slate-400 font-mono">
                  <div>Status: <span className="text-emerald-400 font-semibold">ACTIVE</span></div>
                  <div>Window ID: {profile.time_window_id ? profile.time_window_id.slice(0, 8) : 'canonical-7d'}</div>
                </div>
              </div>

              {/* Subject Breakdown */}
              <div className="space-y-4">
                {profile.subjects.map((sub, sIdx) => (
                  <div key={sIdx} className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
                    <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-200 mb-4 pb-2 border-b border-slate-800">
                      <Layers className="w-4 h-4 text-brand-400" />
                      {sub.subject}
                    </div>

                    <div className="grid gap-3">
                      {sub.topics.map((top, tIdx) => (
                        <div key={tIdx} className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold text-slate-200">{top.topic}</span>
                            <span className="text-xs font-mono font-bold text-brand-400">
                              {Math.round(top.importance_score * 100)}% Importance
                            </span>
                          </div>

                          <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                            <div 
                              className="h-full rounded-full bg-gradient-to-r from-brand-500 to-indigo-500"
                              style={{ width: `${top.importance_score * 100}%` }}
                            />
                          </div>

                          <div className="flex flex-wrap items-center justify-between gap-2 pt-1 text-[11px] text-slate-400">
                            <div className="flex items-center gap-1.5">
                              <span>Expected:</span>
                              {top.expected_question_types.map((qt, qIdx) => (
                                <span key={qIdx} className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                                  {qt}
                                </span>
                              ))}
                            </div>

                            <div className="text-slate-500">
                              Subtopics: {top.subtopics.slice(0, 3).join(', ')}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>

              {/* Evidence Provenance Box */}
              <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800">
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-300 mb-3">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  Evidence Provenance & Trust Traceability
                </div>
                <div className="space-y-2">
                  {profile.evidence.map((ev, eIdx) => (
                    <div key={eIdx} className="p-3 rounded-lg bg-slate-950/40 border border-slate-800/60 text-xs flex items-start justify-between gap-4">
                      <div>
                        <p className="text-slate-300">{ev.fact}</p>
                        <span className="text-[10px] text-slate-500 mt-1 block">Source: {ev.source}</span>
                      </div>
                      <span className="shrink-0 px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800">
                        {ev.trust_level}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-12 text-center rounded-2xl border border-dashed border-slate-800 text-slate-500">
              Select or generate a role topic profile to inspect importance distributions.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
