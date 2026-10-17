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
        <div className="inline-flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-text-muted mb-2">
          <Sparkles className="w-3.5 h-3.5 text-accent" />
          Role Intelligence • Competency Mapping
        </div>
        <h1 className="text-3xl sm:text-4xl font-serif text-text tracking-tight font-normal">
          Target Role Profiler & Skill Mapping
        </h1>
        <p className="text-sm text-text-muted mt-1.5 max-w-2xl leading-relaxed">
          Analyze job requirements to extract core data structures, algorithms, and system design topics prioritized by company interview frequency.
        </p>
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        {/* Left Form */}
        <div className="lg:col-span-1 space-y-6">
          <form onSubmit={handleGenerate} className="p-6 rounded-xl bg-surface border border-border space-y-4">
            <h2 className="text-base font-semibold text-text flex items-center gap-2">
              <FileText className="w-4 h-4 text-accent" />
              Role & JD Parameters
            </h2>

            <div>
              <label className="block text-xs font-mono uppercase tracking-wider text-text-muted mb-1">Company</label>
              <input
                type="text"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="e.g. Google, Amazon, Microsoft"
                className="w-full px-3.5 py-2.5 rounded-lg bg-bg border border-border text-xs text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-mono uppercase tracking-wider text-text-muted mb-1">Role Title</label>
              <input
                type="text"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                placeholder="e.g. Backend SDE 2, Full Stack"
                className="w-full px-3.5 py-2.5 rounded-lg bg-bg border border-border text-xs text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-mono uppercase tracking-wider text-text-muted mb-1">Job Type</label>
                <select
                  value={jobType}
                  onChange={(e) => setJobType(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-bg border border-border text-xs text-text focus:border-accent focus:outline-none cursor-pointer"
                >
                  <option value="Full-Time">Full-Time</option>
                  <option value="Contract">Contract</option>
                  <option value="Internship">Internship</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-mono uppercase tracking-wider text-text-muted mb-1">Experience</label>
                <select
                  value={experience}
                  onChange={(e) => setExperience(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-bg border border-border text-xs text-text focus:border-accent focus:outline-none cursor-pointer"
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
              className="w-full py-3 rounded-xl text-sm font-medium bg-accent text-accent-contrast hover:opacity-90 disabled:opacity-40 flex items-center justify-center gap-2 transition-opacity"
            >
              {loading ? 'Analyzing Job Requirements...' : 'Generate Target Role Profile'}
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </form>

          {/* Action Callout */}
          {profile && (
            <div className="p-5 rounded-xl bg-surface border border-border space-y-3">
              <div className="text-xs font-mono uppercase tracking-wider text-text-muted">
                Next Preparation Step
              </div>
              <p className="text-xs text-text-muted leading-relaxed">
                Role competencies are mapped and synced across your Practice Engine, Timed Assessments, and 1-on-1 Interview loop.
              </p>
              <button
                onClick={() => onNavigate('practice', { company: profile.company, role: profile.role })}
                className="w-full py-2.5 rounded-lg text-xs font-medium bg-bg hover:bg-surface text-text border border-border flex items-center justify-center gap-1.5 transition-colors"
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
              <div className="p-6 rounded-xl bg-surface border border-border flex flex-wrap items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xl font-serif text-text">{profile.company}</span>
                    <span className="text-text-muted">•</span>
                    <span className="text-sm text-text font-medium">{profile.role}</span>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 mt-2">
                    {profile.required_skills.slice(0, 6).map((skill, i) => (
                      <span key={i} className="px-2 py-0.5 rounded bg-bg text-[11px] text-text-muted border border-border font-mono">
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="text-right text-xs text-text-muted font-mono">
                  <div>Status: <span className="text-success font-medium">ACTIVE</span></div>
                  <div>Window ID: {profile.time_window_id ? profile.time_window_id.slice(0, 8) : 'canonical-7d'}</div>
                </div>
              </div>

              {/* Subject Breakdown */}
              <div className="space-y-4">
                {profile.subjects.map((sub, sIdx) => (
                  <div key={sIdx} className="p-5 rounded-xl bg-surface border border-border">
                    <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-text-muted mb-4 pb-2 border-b border-border">
                      <Layers className="w-3.5 h-3.5 text-accent" />
                      {sub.subject}
                    </div>

                    <div className="grid gap-3">
                      {sub.topics.map((top, tIdx) => (
                        <div key={tIdx} className="p-3.5 rounded-lg bg-bg border border-border space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-medium text-text">{top.topic}</span>
                            <span className="text-xs font-mono font-medium text-accent">
                              {Math.round(top.importance_score * 100)}% Importance
                            </span>
                          </div>

                          <div className="w-full h-1.5 rounded-full bg-border overflow-hidden">
                            <div 
                              className="h-full rounded-full bg-accent"
                              style={{ width: `${top.importance_score * 100}%` }}
                            />
                          </div>

                          <div className="flex flex-wrap items-center justify-between gap-2 pt-1 text-[11px] text-text-muted">
                            <div className="flex items-center gap-1.5">
                              <span>Expected:</span>
                              {top.expected_question_types.map((qt, qIdx) => (
                                <span key={qIdx} className="px-1.5 py-0.5 rounded bg-surface border border-border text-text font-mono">
                                  {qt}
                                </span>
                              ))}
                            </div>

                            <div>
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
              <div className="p-5 rounded-xl bg-surface border border-border">
                <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-text-muted mb-3">
                  <ShieldCheck className="w-4 h-4 text-accent" />
                  Evidence Provenance & Trust Traceability
                </div>
                <div className="space-y-2">
                  {profile.evidence.map((ev, eIdx) => (
                    <div key={eIdx} className="p-3 rounded-lg bg-bg border border-border text-xs flex items-start justify-between gap-4">
                      <div>
                        <p className="text-text leading-relaxed">{ev.fact}</p>
                        <span className="text-[10px] text-text-muted mt-1 block font-mono">Source: {ev.source}</span>
                      </div>
                      <span className="shrink-0 px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-success/10 text-success border border-success/30">
                        {ev.trust_level}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-12 text-center rounded-xl border border-dashed border-border text-text-muted font-mono text-xs">
              Select or generate a role topic profile to inspect importance distributions.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
