import React, { useState, useEffect } from 'react';
import { 
  FileText, Cpu, CheckCircle2, ArrowRight, Upload, Sparkles,
  Building2, Briefcase, Star, Layers, ShieldCheck
} from 'lucide-react';
import { StructuredResume } from '../types';
import { api } from '../services/api';
import { DocumentUploadInput } from '../components/DocumentUploadInput';

interface InterviewIntakePageProps {
  initialCompany?: string;
  initialRole?: string;
  onNavigate: (tab: string, state?: any) => void;
}

export const InterviewIntakePage: React.FC<InterviewIntakePageProps> = ({
  initialCompany = 'Google',
  initialRole = 'Software Engineer II (L4)',
  onNavigate
}) => {
  const [company, setCompany] = useState(initialCompany);
  const [role, setRole] = useState(initialRole);
  const [candidateName, setCandidateName] = useState('Alex Mercer');
  const [candidateEmail, setCandidateEmail] = useState('alex.mercer@intervyn.ai');
  const [resumeText, setResumeText] = useState('');
  const [structuredResume, setStructuredResume] = useState<StructuredResume | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function loadSample() {
      try {
        const sample = await api.getSampleResume();
        setStructuredResume(sample);
      } catch (err) {
        console.error(err);
      }
    }
    loadSample();
  }, []);

  const handleParseResume = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resumeText.trim()) return;
    setLoading(true);
    try {
      const res = await api.parseResume({
        candidate_name: candidateName,
        candidate_email: candidateEmail,
        resume_text: resumeText,
        company,
        role
      });
      setStructuredResume(res);
    } catch (err) {
      console.error(err);
      alert('Failed to parse resume.');
    } finally {
      setLoading(false);
    }
  };

  const handleStartInterview = async () => {
    setLoading(true);
    try {
      const turn = await api.startInterview({
        company,
        role,
        resume_id: structuredResume?.id,
        candidate_name: candidateName,
        resume_text: resumeText
      });
      onNavigate('live-interview', { turn, company, role, candidateName });
    } catch (err) {
      console.error(err);
      alert('Failed to launch live interview session.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-2 text-xs font-semibold text-sky-400 uppercase tracking-wider mb-2">
          <Cpu className="w-4 h-4" />
          Technical Interview • Candidate Alignment
        </div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight">
          Interactive Technical Interview Setup
        </h1>
        <p className="text-sm text-slate-300 mt-1 max-w-2xl">
          Upload or paste your resume. Intervyn structures your production projects, computes alignment with the target role, and prepares deep situational questions.
        </p>
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        {/* Left Form */}
        <div className="lg:col-span-1 space-y-6">
          <div className="p-6 rounded-2xl bg-slate-900/80 border border-white/10 shadow-lg space-y-4">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Building2 className="w-4 h-4 text-sky-400" />
              Target Position
            </h2>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Company</label>
              <input
                type="text"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-white/10 text-xs text-white focus:border-sky-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Target Role</label>
              <input
                type="text"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-white/10 text-xs text-white focus:border-sky-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Candidate Name</label>
              <input
                type="text"
                value={candidateName}
                onChange={(e) => setCandidateName(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-white/10 text-xs text-white focus:border-sky-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Email</label>
              <input
                type="email"
                value={candidateEmail}
                onChange={(e) => setCandidateEmail(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-white/10 text-xs text-white focus:border-sky-500 focus:outline-none"
              />
            </div>

            {/* Resume Text Input or File Upload */}
            <div className="pt-2 border-t border-slate-800">
              <DocumentUploadInput
                label="Resume Document (.pdf, .png, .jpg, .txt)"
                placeholder="Upload your resume PDF/image or paste plain text..."
                value={resumeText}
                onChange={setResumeText}
                onMetaExtracted={({ name: extractedName, email: extractedEmail }) => {
                  if (extractedName) setCandidateName(extractedName);
                  if (extractedEmail) setCandidateEmail(extractedEmail);
                }}
              />
            </div>

            <button
              onClick={handleParseResume}
              disabled={loading || !resumeText.trim()}
              className="w-full py-2.5 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-sky-300 border border-sky-500/30 flex items-center justify-center gap-2 transition-all disabled:opacity-50"
            >
              <Upload className="w-3.5 h-3.5" />
              {loading ? 'Parsing Resume Structure...' : 'Parse & Structure Resume'}
            </button>
          </div>

          {/* Start Interview Action Card */}
          {structuredResume && (
            <div className="p-6 rounded-2xl bg-gradient-to-b from-slate-900 to-indigo-950/30 border border-white/10 shadow-lg space-y-4">
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-emerald-400">
                <CheckCircle2 className="w-4 h-4" />
                Ready to Launch
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                Resume parsed successfully. The interview begins with your highest-relevance project: <span className="text-white font-semibold">{structuredResume.projects[0]?.title}</span>.
              </p>
              <button
                onClick={handleStartInterview}
                disabled={loading}
                className="w-full py-3.5 rounded-xl text-xs font-bold bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-600 hover:from-blue-500 hover:to-indigo-500 text-white flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/25 transition-all active:scale-[0.98]"
              >
                {loading ? 'Initializing Interview Room...' : 'Enter AI Technical Interview Room'}
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>

        {/* Right Details: Extracted Projects & Relevance Ranking */}
        <div className="lg:col-span-2 space-y-6">
          {structuredResume ? (
            <div className="space-y-6">
              {/* Profile Card */}
              <div className="p-6 rounded-2xl bg-slate-900/80 border border-white/10 shadow-lg flex flex-wrap items-center justify-between gap-4">
                <div>
                  <h3 className="text-lg font-bold text-white">{structuredResume.candidate_name}</h3>
                  <p className="text-xs text-slate-400">{structuredResume.candidate_email || 'Verified Candidate Profile'}</p>
                  <div className="flex flex-wrap items-center gap-1.5 mt-3">
                    {structuredResume.skills.slice(0, 8).map((sk, i) => (
                      <span key={i} className="px-2 py-0.5 rounded bg-slate-800 border border-white/5 text-[10px] text-slate-300 font-mono">
                        {sk}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="text-xs text-right text-slate-400 font-mono space-y-0.5">
                  <div>Work Exp Weight: 30%</div>
                  <div>Projects Weight: 30%</div>
                  <div>Skills Weight: 15%</div>
                </div>
              </div>

              {/* Projects Ranked by Priority */}
              <div className="p-6 rounded-2xl bg-slate-900/80 border border-white/10 shadow-lg space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-base font-bold text-white">
                      Extracted Projects & Questioning Priority
                    </h4>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Ranked by relevance to {role}. High relevance topics receive deep situational follow-ups.
                    </p>
                  </div>
                </div>

                <div className="space-y-3">
                  {structuredResume.projects.map((proj, idx) => (
                    <div
                      key={idx}
                      className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-2.5"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="w-5 h-5 rounded-full bg-brand-600/30 text-brand-300 text-xs font-mono font-bold flex items-center justify-center">
                            #{proj.questioning_priority}
                          </span>
                          <span className="text-xs sm:text-sm font-bold text-white">{proj.title}</span>
                        </div>

                        <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">
                          {Math.round(proj.overall_relevance * 100)}% Relevance
                        </span>
                      </div>

                      <p className="text-xs text-slate-400 leading-relaxed">{proj.description}</p>

                      <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-800/60 text-[11px]">
                        <div className="flex items-center gap-1 text-slate-400">
                          <span className="font-semibold text-slate-300">Target Topics:</span>
                          <span>{proj.relevant_topics.join(', ')}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-12 text-center rounded-2xl border border-dashed border-slate-800 text-slate-500">
              No structured resume loaded.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
