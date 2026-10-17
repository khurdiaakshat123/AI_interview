import React, { useState, useEffect } from 'react';
import { 
  FileText, Cpu, CheckCircle2, ArrowRight, Upload, Sparkles,
  Building2, Briefcase, Star, Layers, ShieldCheck, AlertCircle,
  ChevronDown, ChevronUp, SlidersHorizontal, Edit3, Save, Loader2,
  Check
} from 'lucide-react';
import { StructuredResume, CandidateProfile } from '../types';
import { api, BASE_URL, getAuthToken } from '../services/api';
import { DocumentUploadInput } from '../components/DocumentUploadInput';

interface InterviewIntakePageProps {
  initialCompany?: string;
  initialRole?: string;
  candidateProfile?: CandidateProfile;
  onSaveProfile?: (profile: CandidateProfile) => void;
  onNavigate: (tab: string, state?: any) => void;
}

const SAMPLE_JDS = {
  openai: {
    company: 'OpenAI',
    role: 'Distributed Training Systems Engineer',
    jd: 'OpenAI is hiring a Distributed Training Infrastructure Engineer. You will scale training jobs across thousands of GPUs, optimize NCCL all-reduce routines, implement Megatron-LM tensor parallelism, and ensure fault-tolerant checkpointing with high-speed NVMe and InfiniBand fabrics. Strong background in Linux systems programming, Python/C++, and distributed systems required.'
  },
  google: {
    company: 'Google',
    role: 'Software Engineer II (L4) - Cloud Spanner',
    jd: 'Google Cloud Spanner team is seeking a Software Engineer II (L4). You will design distributed transaction protocols, optimize query execution plans, maintain Paxos replication consensus, and manage multi-region high availability. Experience with Go, C++, Paxos/Raft, and relational database internals is strongly preferred.'
  },
  meta: {
    company: 'Meta',
    role: 'Production Engineer (E4) - Infrastructure',
    jd: 'Meta is hiring a Production Engineer for core infrastructure. You will manage large-scale distributed caching services (Memcached/Tao), optimize network telemetry, automate multi-region failovers, and debug kernel/network bottlenecks. Proficiency in Python, Go, or C++, and solid OS/networking fundamentals required.'
  }
};

export const InterviewIntakePage: React.FC<InterviewIntakePageProps> = ({
  initialCompany = 'Google',
  initialRole = 'Software Engineer II (L4)',
  candidateProfile,
  onSaveProfile,
  onNavigate
}) => {
  const [company, setCompany] = useState(candidateProfile?.company || initialCompany);
  const [role, setRole] = useState(candidateProfile?.role || initialRole);
  const [candidateName, setCandidateName] = useState(candidateProfile?.name || 'Alex Mercer');
  const [candidateEmail, setCandidateEmail] = useState(candidateProfile?.email || 'alex.mercer@intervyn.ai');
  const [resumeText, setResumeText] = useState(candidateProfile?.resumeText || '');
  const [jdText, setJdText] = useState(candidateProfile?.jdText || '');
  
  // If user already has a stored resume in profile, collapse resume inputs by default to focus on JD
  const [showEditCandidateDetails, setShowEditCandidateDetails] = useState(!candidateProfile?.resumeText?.trim());
  const [profileSavedAlert, setProfileSavedAlert] = useState(false);

  const [structuredResume, setStructuredResume] = useState<StructuredResume | null>(null);
  const [isCustomResumeParsed, setIsCustomResumeParsed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [stepMessage, setStepMessage] = useState('');
  const [parseError, setParseError] = useState<string | null>(null);

  // Sync state if candidateProfile changes from external update
  useEffect(() => {
    if (candidateProfile) {
      if (candidateProfile.company) setCompany(candidateProfile.company);
      if (candidateProfile.role) setRole(candidateProfile.role);
      if (candidateProfile.name) setCandidateName(candidateProfile.name);
      if (candidateProfile.email) setCandidateEmail(candidateProfile.email);
      if (candidateProfile.resumeText !== undefined) setResumeText(candidateProfile.resumeText);
      if (candidateProfile.jdText !== undefined && !jdText) setJdText(candidateProfile.jdText);
    }
  }, [candidateProfile]);

  // Initial load: parse attached resume automatically or load sample
  useEffect(() => {
    let isMounted = true;
    async function loadInitial() {
      const activeResume = resumeText.trim() || candidateProfile?.resumeText?.trim();
      if (activeResume) {
        try {
          const res = await api.parseResume({
            candidate_name: candidateName,
            candidate_email: candidateEmail,
            resume_text: activeResume,
            company,
            role
          });
          if (isMounted) {
            setStructuredResume(res);
            setIsCustomResumeParsed(true);
          }
        } catch (err) {
          console.error('Error auto-parsing profile resume:', err);
        }
      } else {
        try {
          const sample = await api.getSampleResume();
          if (isMounted && !resumeText.trim()) {
            setStructuredResume(sample);
          }
        } catch (err) {
          console.error(err);
        }
      }
    }
    loadInitial();
    return () => {
      isMounted = false;
    };
  }, []);

  const handleResumeTextChange = (text: string) => {
    setResumeText(text);
    setIsCustomResumeParsed(false);
    setParseError(null);
  };

  const handleApplyJdPreset = (preset: 'openai' | 'google' | 'meta') => {
    const item = SAMPLE_JDS[preset];
    setCompany(item.company);
    setRole(item.role);
    setJdText(item.jd);
  };

  const handleSaveDetailsToProfile = () => {
    if (onSaveProfile) {
      const wordCount = resumeText.trim() ? resumeText.trim().split(/\s+/).filter(Boolean).length : 0;
      onSaveProfile({
        name: candidateName.trim(),
        email: candidateEmail.trim(),
        company: company.trim(),
        role: role.trim(),
        resumeText: resumeText.trim(),
        resumeWordCount: wordCount,
        jdText: jdText.trim()
      });
      setProfileSavedAlert(true);
      setTimeout(() => setProfileSavedAlert(false), 3000);
    }
  };

  const handleParseResume = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!resumeText.trim()) return;
    setLoading(true);
    setParseError(null);
    try {
      const res = await api.parseResume({
        candidate_name: candidateName,
        candidate_email: candidateEmail,
        resume_text: resumeText,
        company,
        role
      });
      setStructuredResume(res);
      setIsCustomResumeParsed(true);
      if (res.candidate_name && res.candidate_name !== 'Candidate' && res.candidate_name !== 'Alex Mercer') {
        setCandidateName(res.candidate_name);
      }
      if (res.candidate_email) {
        setCandidateEmail(res.candidate_email);
      }

      // Automatically sync parsed resume and names to profile
      if (onSaveProfile) {
        const wordCount = resumeText.trim().split(/\s+/).filter(Boolean).length;
        onSaveProfile({
          name: res.candidate_name || candidateName,
          email: res.candidate_email || candidateEmail,
          company,
          role,
          resumeText: resumeText.trim(),
          resumeWordCount: wordCount,
          jdText: jdText.trim()
        });
      }
    } catch (err: any) {
      console.error(err);
      setParseError(err.message || 'Failed to parse resume structure.');
    } finally {
      setLoading(false);
    }
  };

  const handleStartInterview = async () => {
    setLoading(true);
    setParseError(null);
    setStepMessage('Initializing AI interview session...');

    // Sync any edits back to the candidate's profile
    if (onSaveProfile) {
      const wordCount = resumeText.trim() ? resumeText.trim().split(/\s+/).filter(Boolean).length : 0;
      onSaveProfile({
        name: candidateName.trim(),
        email: candidateEmail.trim(),
        company: company.trim(),
        role: role.trim(),
        resumeText: resumeText.trim(),
        resumeWordCount: wordCount,
        jdText: jdText.trim()
      });
    }

    try {
      if (jdText.trim()) {
        // Run full setup using the provided Job Description & Resume
        setStepMessage('Extracting JD topics and tailoring interview questions with Live AI...');
        const token = getAuthToken();
        const headers: Record<string, string> = { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        };

        const payloadBody = JSON.stringify({
          name: candidateName.trim(),
          email: candidateEmail.trim(),
          experience_years: candidateProfile?.experience || '1-3 years',
          target_company: company.trim(),
          target_role: role.trim(),
          job_type: 'Full-Time',
          jd_text: jdText.trim(),
          resume_text: resumeText.trim()
        });

        let response: Response;
        try {
          response = await fetch(`${BASE_URL}/candidate/setup`, {
            method: 'POST',
            headers,
            body: payloadBody
          });
        } catch {
          response = await fetch('/api/candidate/setup', {
            method: 'POST',
            headers,
            body: payloadBody
          });
        }

        if (!response.ok) {
          const errText = await response.text();
          throw new Error(`Failed to initialize session with JD: ${errText}`);
        }

        const data = await response.json();
        onNavigate('live-interview', {
          turn: data.initial_turn,
          company: data.company,
          role: data.role,
          candidateName: data.candidate_name || candidateName.trim()
        });
      } else {
        // Direct launch with attached resume
        setStepMessage('Preparing live interview room...');
        const turn = await api.startInterview({
          company,
          role,
          resume_id: isCustomResumeParsed && structuredResume ? structuredResume.id : undefined,
          candidate_name: candidateName,
          resume_text: resumeText.trim() ? resumeText.trim() : undefined
        });
        onNavigate('live-interview', { turn, company, role, candidateName });
      }
    } catch (err: any) {
      console.error(err);
      setParseError(err.message || 'Failed to launch live interview session.');
    } finally {
      setLoading(false);
      setStepMessage('');
    }
  };

  const resumeWordCount = resumeText.trim() ? resumeText.trim().split(/\s+/).filter(Boolean).length : 0;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-text-muted mb-2">
          <Cpu className="w-3.5 h-3.5 text-accent" />
          Technical Interview • Adaptive Candidate Alignment
        </div>
        <h1 className="text-3xl sm:text-4xl font-serif text-text tracking-tight font-normal">
          AI Technical Interview Setup
        </h1>
        <p className="text-sm text-text-muted mt-1.5 max-w-3xl leading-relaxed">
          Your stored profile resume is automatically attached. Provide or paste the target Job Description (JD) to focus interview questions directly on the opening's requirements.
        </p>
      </div>

      {/* Profile & Resume Summary Card (Always Visible Status Banner) */}
      <div className="p-5 rounded-xl bg-surface border border-border flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-xl bg-bg border border-border flex items-center justify-center text-sm font-mono font-semibold text-text uppercase shrink-0">
            {candidateName[0] || 'C'}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-text">{candidateName}</h3>
              <span className="text-xs text-text-muted font-mono">({candidateEmail})</span>
            </div>
            <div className="text-xs text-text-muted flex items-center gap-1.5 mt-0.5">
              <span>Target:</span>
              <span className="font-medium text-text">{role}</span>
              <span className="text-text-muted">•</span>
              <span className="font-medium text-accent">{company}</span>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto justify-between md:justify-end">
          <div className="flex items-center gap-2">
            {resumeText.trim() ? (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-mono bg-success/10 text-success border border-success/30">
                <CheckCircle2 className="w-3.5 h-3.5 text-success" />
                Resume Attached ({resumeWordCount} words)
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-mono bg-danger/10 text-danger border border-danger/30">
                <AlertCircle className="w-3.5 h-3.5 text-danger" />
                No Resume Attached
              </span>
            )}
          </div>

          <button
            type="button"
            onClick={() => setShowEditCandidateDetails(prev => !prev)}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-medium bg-bg hover:bg-surface text-text border border-border transition-colors"
            title="Inspect or modify your attached resume, candidate name, or target position"
          >
            <SlidersHorizontal className="w-3.5 h-3.5 text-text-muted" />
            {showEditCandidateDetails ? 'Hide Resume & Position Settings' : 'Change Resume or Target Position'}
            {showEditCandidateDetails ? (
              <ChevronUp className="w-3.5 h-3.5 text-text-muted" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5 text-text-muted" />
            )}
          </button>
        </div>
      </div>

      {/* Collapsible Candidate Resume & Position Customization Card */}
      {showEditCandidateDetails && (
        <div className="p-6 rounded-xl bg-surface border border-border space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-border">
            <div className="flex items-center gap-2">
              <Building2 className="w-4 h-4 text-accent" />
              <h2 className="text-sm font-semibold text-text">
                Customize Candidate Details & Resume for this Session
              </h2>
            </div>
            <span className="text-[11px] text-text-muted">
              Edits can be saved to your profile or used for this interview
            </span>
          </div>

          {profileSavedAlert && (
            <div className="p-3 rounded-lg bg-success/10 border border-success/30 text-xs text-success flex items-center gap-2 font-mono">
              <Check className="w-4 h-4 text-success" />
              <span>Profile details and resume saved successfully!</span>
            </div>
          )}

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <div>
              <label className="block text-xs font-mono uppercase tracking-wider text-text-muted mb-1">Target Company</label>
              <input
                type="text"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="e.g. OpenAI, Google"
                className="w-full px-3 py-2 rounded-lg bg-bg border border-border text-xs text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-mono uppercase tracking-wider text-text-muted mb-1">Target Role</label>
              <input
                type="text"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                placeholder="e.g. Distributed Systems Engineer"
                className="w-full px-3 py-2 rounded-lg bg-bg border border-border text-xs text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-mono uppercase tracking-wider text-text-muted mb-1">Candidate Name</label>
              <input
                type="text"
                value={candidateName}
                onChange={(e) => setCandidateName(e.target.value)}
                placeholder="Full Name"
                className="w-full px-3 py-2 rounded-lg bg-bg border border-border text-xs text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-mono uppercase tracking-wider text-text-muted mb-1">Email</label>
              <input
                type="email"
                value={candidateEmail}
                onChange={(e) => setCandidateEmail(e.target.value)}
                placeholder="candidate@example.com"
                className="w-full px-3 py-2 rounded-lg bg-bg border border-border text-xs text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
              />
            </div>
          </div>

          <div className="pt-2">
            <DocumentUploadInput
              label="Attached Resume Document (.pdf, .docx, .png, .jpg, .txt)"
              sublabel="Upload a different resume or edit your plain text resume content"
              placeholder="Upload your resume PDF/Word/image or paste plain text..."
              value={resumeText}
              onChange={handleResumeTextChange}
              onMetaExtracted={({ name: extractedName, email: extractedEmail }) => {
                if (extractedName) setCandidateName(extractedName);
                if (extractedEmail) setCandidateEmail(extractedEmail);
              }}
              badgeColor="emerald"
              rows={4}
            />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-border">
            <button
              type="button"
              onClick={handleSaveDetailsToProfile}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-medium bg-bg hover:bg-surface text-text border border-border transition-colors"
            >
              <Save className="w-3.5 h-3.5" />
              Save to Profile
            </button>

            <button
              type="button"
              onClick={handleParseResume}
              disabled={loading || !resumeText.trim()}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-medium bg-surface hover:bg-bg text-text border border-border transition-colors disabled:opacity-40"
            >
              <Upload className="w-3.5 h-3.5 text-accent" />
              {loading ? 'Re-parsing Resume...' : 'Re-parse & Preview Projects'}
            </button>
          </div>
        </div>
      )}

      {/* Main Grid: JD Input on Left, Extracted Resume Structure on Right */}
      <div className="grid lg:grid-cols-3 gap-8">
        {/* Left Form: Dedicated Job Description (JD) Input & Launch */}
        <div className="lg:col-span-1 space-y-6">
          <div className="p-6 rounded-xl bg-surface border border-border space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-text flex items-center gap-2">
                <Briefcase className="w-4 h-4 text-accent" />
                Target Job Description (JD)
              </h2>
            </div>
            
            <p className="text-xs text-text-muted leading-relaxed">
              Paste the job opening specs or upload a JD document. Our AI will align every question to these requirements.
            </p>

            {/* Quick Sample Presets */}
            <div className="p-3.5 rounded-lg bg-bg border border-border space-y-2">
              <div className="text-[11px] font-mono uppercase tracking-wider text-text-muted">
                Sample Roles:
              </div>
              <div className="flex flex-wrap gap-1.5">
                <button
                  type="button"
                  onClick={() => handleApplyJdPreset('openai')}
                  className="px-2.5 py-1 rounded-md text-[11px] font-medium bg-surface hover:bg-border text-text border border-border transition-colors"
                >
                  OpenAI Distributed
                </button>
                <button
                  type="button"
                  onClick={() => handleApplyJdPreset('google')}
                  className="px-2.5 py-1 rounded-md text-[11px] font-medium bg-surface hover:bg-border text-text border border-border transition-colors"
                >
                  Google Spanner L4
                </button>
                <button
                  type="button"
                  onClick={() => handleApplyJdPreset('meta')}
                  className="px-2.5 py-1 rounded-md text-[11px] font-medium bg-surface hover:bg-border text-text border border-border transition-colors"
                >
                  Meta Infra E4
                </button>
              </div>
            </div>

            {/* Document Upload Input for Job Description */}
            <DocumentUploadInput
              label="Job Description Specs"
              sublabel="Upload PDF job specs, JD screenshots, or paste plain text"
              placeholder="Paste responsibilities, requirements, and tech stack, or upload a PDF/image..."
              value={jdText}
              onChange={setJdText}
              rows={6}
              badgeColor="indigo"
            />

            {parseError && (
              <div className="p-2.5 rounded-lg bg-danger/10 border border-danger/30 text-[11px] text-danger flex items-center gap-2 font-mono">
                <AlertCircle className="w-3.5 h-3.5 text-danger flex-shrink-0" />
                <span>{parseError}</span>
              </div>
            )}
          </div>

          {/* Launch Session Card */}
          <div className="p-6 rounded-xl bg-surface border border-border space-y-4">
            <div className="flex items-center gap-2 text-xs font-mono font-medium text-text">
              <CheckCircle2 className="w-4 h-4 text-accent" />
              {jdText.trim() ? 'Ready with JD & Attached Resume' : (resumeText.trim() ? 'Resume Ready • Launch Directly' : 'Sample Loaded')}
            </div>

            <p className="text-xs text-text-muted leading-relaxed">
              {jdText.trim() ? (
                <>AI interviewer will generate customized questioning based on your target JD and attached resume.</>
              ) : resumeText.trim() ? (
                <>Your profile resume is attached. Paste a JD above to tailor questions to a specific opening, or start directly.</>
              ) : (
                <>Upload your resume or paste a JD to customize your interview session.</>
              )}
            </p>

            {loading && stepMessage && (
              <div className="p-3 rounded-lg bg-bg border border-border text-xs text-text flex items-center gap-2.5 font-mono">
                <Loader2 className="w-4 h-4 animate-spin text-accent shrink-0" />
                <span>{stepMessage}</span>
              </div>
            )}

            <button
              onClick={handleStartInterview}
              disabled={loading || (!resumeText.trim() && !structuredResume)}
              className="w-full py-3.5 rounded-xl text-sm font-medium bg-accent text-accent-contrast hover:opacity-90 flex items-center justify-center gap-2 transition-opacity disabled:opacity-40"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Launching Technical Interview...
                </>
              ) : (
                <>
                  Enter AI Technical Interview Room
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </div>

        {/* Right Details: Extracted Projects & Relevance Ranking */}
        <div className="lg:col-span-2 space-y-6">
          {structuredResume ? (
            <div className="space-y-6">
              {/* Profile Card */}
              <div className="p-6 rounded-xl bg-surface border border-border flex flex-wrap items-center justify-between gap-4">
                <div>
                  <h3 className="text-xl font-serif text-text">{structuredResume.candidate_name}</h3>
                  <p className="text-xs text-text-muted font-mono">{structuredResume.candidate_email || candidateEmail || 'Attached Candidate Profile'}</p>
                  <div className="flex flex-wrap items-center gap-1.5 mt-3">
                    {structuredResume.skills.slice(0, 8).map((sk, i) => (
                      <span key={i} className="px-2 py-0.5 rounded bg-bg border border-border text-[11px] text-text-muted font-mono">
                        {sk}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="text-xs text-right text-text-muted font-mono space-y-0.5">
                  <div>Work Exp Weight: 30%</div>
                  <div>Projects Weight: 30%</div>
                  <div>Skills Weight: 15%</div>
                </div>
              </div>

              {/* Projects Ranked by Priority */}
              <div className="p-6 rounded-xl bg-surface border border-border space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-lg font-serif text-text">
                      Extracted Projects & Questioning Priority
                    </h4>
                    <p className="text-xs text-text-muted mt-0.5">
                      Ranked by relevance to {role}. High relevance topics receive deep situational follow-ups.
                    </p>
                  </div>
                </div>

                <div className="space-y-3">
                  {structuredResume.projects.map((proj, idx) => (
                    <div
                      key={idx}
                      className="p-4 rounded-lg bg-bg border border-border space-y-2.5"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="w-5 h-5 rounded bg-surface border border-border text-accent text-xs font-mono font-medium flex items-center justify-center">
                            #{proj.questioning_priority}
                          </span>
                          <span className="text-xs sm:text-sm font-semibold text-text">{proj.title}</span>
                        </div>

                        <span className="px-2.5 py-0.5 rounded text-[11px] font-mono font-medium bg-success/10 text-success border border-success/30">
                          {Math.round(proj.overall_relevance * 100)}% Relevance
                        </span>
                      </div>

                      <p className="text-xs text-text-muted leading-relaxed">{proj.description}</p>

                      <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-border text-[11px]">
                        <div className="flex items-center gap-1 text-text-muted">
                          <span className="font-medium text-text">Target Topics:</span>
                          <span>{proj.relevant_topics.join(', ')}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-12 text-center rounded-xl border border-dashed border-border text-text-muted font-mono text-xs">
              No structured resume loaded.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
