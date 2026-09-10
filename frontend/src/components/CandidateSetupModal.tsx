import React, { useState } from 'react';
import { 
  UserPlus, Sparkles, Building2, Briefcase, FileText, CheckCircle2,
  ArrowRight, X, Layers, Cpu, Check, Loader2, AlertCircle, RefreshCw
} from 'lucide-react';
import { DocumentUploadInput } from './DocumentUploadInput';

interface CandidateSetupModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (candidateData: {
    user: any;
    company: string;
    role: string;
    turn: any;
  }) => void;
}

const SAMPLE_JDS = {
  openai: {
    company: 'OpenAI',
    role: 'Distributed Training Systems Engineer',
    experience: '3-5 years',
    jd: 'OpenAI is hiring a Distributed Training Infrastructure Engineer. You will scale training jobs across thousands of GPUs, optimize NCCL all-reduce routines, implement Megatron-LM tensor parallelism, and ensure fault-tolerant checkpointing with high-speed NVMe and InfiniBand fabrics. Strong background in Linux systems programming, Python/C++, and distributed systems required.'
  },
  google: {
    company: 'Google',
    role: 'Software Engineer II (L4) - Cloud Spanner',
    experience: '1-3 years',
    jd: 'Google Cloud Spanner team is seeking a Software Engineer II (L4). You will design distributed transaction protocols, optimize query execution plans, maintain Paxos replication consensus, and manage multi-region high availability. Experience with Go, C++, Paxos/Raft, and relational database internals is strongly preferred.'
  },
  meta: {
    company: 'Meta',
    role: 'Production Engineer (E4) - Infrastructure',
    experience: '1-3 years',
    jd: 'Meta is hiring a Production Engineer for core infrastructure. You will manage large-scale distributed caching services (Memcached/Tao), optimize network telemetry, automate multi-region failovers, and debug kernel/network bottlenecks. Proficiency in Python, Go, or C++, and solid OS/networking fundamentals required.'
  }
};

const SAMPLE_RESUMES = {
  systems: "Alex Mercer | alex.mercer@gmail.com | (555) 345-6789\n" +
    "SUMMARY:\nDistributed Systems Engineer with 3+ years building high-throughput backend infrastructure.\n\n" +
    "PROJECTS:\n1. Distributed Key-Value Store & Cache Cluster\n" +
    "- Architected distributed in-memory cache handling 65k QPS using consistent hashing and Raft consensus.\n" +
    "- Optimized network communication with gRPC multiplexing and Protobuf serialization, reducing p99 latency by 42%.\n" +
    "- Implemented WAL (Write-Ahead Logging) and snapshotting to ensure durability against power failures.\n" +
    "Technologies: Go, Raft, gRPC, Protobuf, Redis, Docker, Prometheus.\n\n" +
    "2. Real-Time Webhook Processing Engine\n" +
    "- Engineered idempotent payment notification pipeline using Apache Kafka and PostgreSQL.\n" +
    "- Implemented consumer group auto-balancing and dead-letter queues, processing 10M events/day with zero loss.\n" +
    "Technologies: Python, FastAPI, Apache Kafka, PostgreSQL, Docker.\n\n" +
    "WORK EXPERIENCE:\nSoftware Engineer at ScaleTech Labs (2022 - Present)\n" +
    "- Designed asynchronous task queue for distributed batch jobs, decreasing server memory pressure by 30%.\n" +
    "- Conducted database query optimizations and index tuning on PostgreSQL clusters.\n\n" +
    "EDUCATION:\nB.S. in Computer Science, State University (2022)",
  ai_ml: "Maya Lin | maya.lin@ai-systems.dev | (555) 789-1234\n" +
    "SUMMARY:\nMachine Learning Systems Engineer focused on multi-node GPU cluster acceleration and distributed training.\n\n" +
    "PROJECTS:\n1. GPU-Accelerated Distributed Training Pipeline\n" +
    "- Scaled Megatron-LM 3D parallelism across 128 GPU nodes with custom pipeline execution schedules.\n" +
    "- Optimized NCCL all-reduce bandwidth utilizing GPUDirect RDMA over RoCEv2 networks.\n" +
    "Technologies: PyTorch, CUDA, Megatron-LM, NCCL, InfiniBand, Python, C++.\n\n" +
    "2. Low-Latency Model Inference Gateway\n" +
    "- Built Triton Inference Server cluster with dynamic batching and INT8 quantization, serving 40k req/s at <12ms p99.\n" +
    "Technologies: Triton, TensorRT, FastAPI, Docker, Kubernetes.\n\n" +
    "WORK EXPERIENCE:\nML Infrastructure Engineer at NeuroScale (2023 - Present)\n" +
    "- Optimized checkpoint serialization speeds by 4x using asynchronous I/O and S3 chunked uploads.\n\n" +
    "EDUCATION:\nM.S. in Computer Science & Machine Learning, Tech Institute (2023)"
};

export const CandidateSetupModal: React.FC<CandidateSetupModalProps> = ({
  isOpen,
  onClose,
  onSuccess
}) => {
  const [name, setName] = useState('Maya Lin');
  const [email, setEmail] = useState('maya.lin@example.com');
  const [experience, setExperience] = useState('3-5 years');
  const [company, setCompany] = useState(SAMPLE_JDS.openai.company);
  const [role, setRole] = useState(SAMPLE_JDS.openai.role);
  const [jdText, setJdText] = useState(SAMPLE_JDS.openai.jd);
  const [resumeText, setResumeText] = useState(SAMPLE_RESUMES.ai_ml);
  const [loading, setLoading] = useState(false);
  const [stepMessage, setStepMessage] = useState('');
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleApplyPreset = (preset: 'openai' | 'google' | 'meta') => {
    const p = SAMPLE_JDS[preset];
    setCompany(p.company);
    setRole(p.role);
    setExperience(p.experience);
    setJdText(p.jd);
    if (preset === 'openai') {
      setResumeText(SAMPLE_RESUMES.ai_ml);
      setName('Maya Lin');
      setEmail('maya.lin@ai-systems.dev');
    } else {
      setResumeText(SAMPLE_RESUMES.systems);
      setName('David Park');
      setEmail('david.park@tech.org');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !email.trim() || !company.trim() || !role.trim()) {
      setError('Please provide all required profile fields.');
      return;
    }

    setError(null);
    setLoading(true);
    setStepMessage('Agent 1: Extracting Job Description topics with Live AI...');

    try {
      const response = await fetch('/api/candidate/setup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim(),
          experience_years: experience,
          target_company: company.trim(),
          target_role: role.trim(),
          job_type: 'Full-Time',
          jd_text: jdText.trim(),
          resume_text: resumeText.trim()
        })
      });

      if (!response.ok) {
        const errText = await response.text();
        throw new Error(`Server returned status ${response.status}: ${errText}`);
      }

      setStepMessage('Parsing resume projects & calculating relevance weights...');
      const data = await response.json();

      setStepMessage('Initializing adaptive live interviewer...');
      setTimeout(() => {
        onSuccess({
          user: data.user,
          company: data.company,
          role: data.role,
          turn: data.initial_turn
        });
        onClose();
      }, 500);

    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to setup candidate and JD. Please try again.');
    } finally {
      setLoading(false);
      setStepMessage('');
    }
  };

  return (
    <div className='fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4 overflow-y-auto'>
      <div className='w-full max-w-3xl my-8 p-6 sm:p-8 rounded-3xl bg-slate-900 border border-slate-800 shadow-2xl space-y-6 relative'>
        {/* Header */}
        <div className='flex items-start justify-between pb-4 border-b border-slate-800'>
          <div className='flex items-center gap-3'>
            <div className='w-10 h-10 rounded-2xl bg-gradient-to-tr from-brand-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-brand-500/20'>
              <UserPlus className='w-5 h-5 text-white' />
            </div>
            <div>
              <h2 className='text-xl font-extrabold text-white tracking-tight'>
                New Candidate & Opportunity Setup
              </h2>
              <p className='text-xs text-slate-400 mt-0.5'>
                Input your details, target Job Description, and Resume. Intervyn structures the topics and tailors the live interview to you.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={loading}
            className='p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-all'
          >
            <X className='w-5 h-5' />
          </button>
        </div>

        {/* Quick Presets */}
        <div className='flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-2xl bg-slate-950/60 border border-slate-800/80 text-xs'>
          <span className='text-slate-400 font-medium flex items-center gap-1.5'>
            <Sparkles className='w-3.5 h-3.5 text-amber-400' />
            Quick Sample Roles:
          </span>
          <div className='flex flex-wrap items-center gap-2'>
            <button
              type='button'
              onClick={() => handleApplyPreset('openai')}
              className='px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-all'
            >
              OpenAI (Distributed Training)
            </button>
            <button
              type='button'
              onClick={() => handleApplyPreset('google')}
              className='px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-all'
            >
              Google L4 (Cloud Spanner)
            </button>
            <button
              type='button'
              onClick={() => handleApplyPreset('meta')}
              className='px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-all'
            >
              Meta E4 (Infrastructure)
            </button>
          </div>
        </div>

        {error && (
          <div className='p-3.5 rounded-xl bg-red-950/50 border border-red-800/60 text-xs text-red-300 flex items-center gap-2'>
            <AlertCircle className='w-4 h-4 flex-shrink-0 text-red-400' />
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className='space-y-6'>
          {/* Section 1: Candidate Details */}
          <div className='space-y-3'>
            <div className='flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-brand-400'>
              <Cpu className='w-3.5 h-3.5' />
              1. Candidate Profile
            </div>
            <div className='grid sm:grid-cols-3 gap-3'>
              <div>
                <label className='block text-xs font-medium text-slate-300 mb-1'>Full Name</label>
                <input
                  type='text'
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder='e.g. Maya Lin'
                  className='w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:border-brand-500 focus:outline-none'
                  required
                />
              </div>
              <div>
                <label className='block text-xs font-medium text-slate-300 mb-1'>Email Address</label>
                <input
                  type='email'
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder='e.g. maya.lin@example.com'
                  className='w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:border-brand-500 focus:outline-none'
                  required
                />
              </div>
              <div>
                <label className='block text-xs font-medium text-slate-300 mb-1'>Experience Level</label>
                <select
                  value={experience}
                  onChange={(e) => setExperience(e.target.value)}
                  className='w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:border-brand-500 focus:outline-none cursor-pointer'
                >
                  <option value='0-1 years'>0-1 years (Entry / Intern)</option>
                  <option value='1-3 years'>1-3 years (Junior SWE)</option>
                  <option value='3-5 years'>3-5 years (Mid-Level SWE)</option>
                  <option value='5+ years'>5+ years (Senior / Lead)</option>
                </select>
              </div>
            </div>
          </div>

          {/* Section 2: Target Opportunity & JD */}
          <div className='space-y-3'>
            <div className='flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-indigo-400'>
              <Building2 className='w-3.5 h-3.5' />
              2. Target Company & Job Description (JD)
            </div>
            <div className='grid sm:grid-cols-2 gap-3'>
              <div>
                <label className='block text-xs font-medium text-slate-300 mb-1'>Target Company</label>
                <input
                  type='text'
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  placeholder='e.g. OpenAI, Google, Stripe'
                  className='w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:border-indigo-500 focus:outline-none'
                  required
                />
              </div>
              <div>
                <label className='block text-xs font-medium text-slate-300 mb-1'>Target Role Title</label>
                <input
                  type='text'
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  placeholder='e.g. Distributed Systems Engineer'
                  className='w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:border-indigo-500 focus:outline-none'
                  required
                />
              </div>
            </div>
            <DocumentUploadInput
              label="Job Description (JD)"
              sublabel="Upload PDF job specs, JD screenshots (PNG/JPG), or paste raw text"
              value={jdText}
              onChange={setJdText}
              placeholder="Paste requirements, tech stack, and responsibilities, or upload a PDF/screenshot..."
              rows={4}
              badgeColor="indigo"
            />
          </div>

          {/* Section 3: Candidate Resume */}
          <div className='space-y-3'>
            <div className='flex items-center justify-between'>
              <div className='flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-emerald-400'>
                <FileText className='w-3.5 h-3.5' />
                3. Candidate Resume (Projects & Skills)
              </div>
              <button
                type='button'
                onClick={() => setResumeText('')}
                className='text-[11px] text-slate-400 hover:text-slate-200 underline'
              >
                Clear Resume
              </button>
            </div>
            <DocumentUploadInput
              label="Resume Content"
              sublabel="Upload PDF resume, scan/screenshot, or paste text"
              value={resumeText}
              onChange={setResumeText}
              onMetaExtracted={({ name: extractedName, email: extractedEmail }) => {
                if (extractedName) {
                  setName(extractedName);
                }
                if (extractedEmail) {
                  setEmail(extractedEmail);
                }
              }}
              placeholder="Paste candidate resume text with projects, technologies, and achievements, or upload a PDF/image..."
              rows={5}
              badgeColor="emerald"
              required
            />
          </div>

          {/* Progress Banner during submission */}
          {loading && (
            <div className='p-4 rounded-2xl bg-brand-950/40 border border-brand-800/60 flex items-center gap-3 text-xs text-brand-300'>
              <Loader2 className='w-5 h-5 animate-spin text-brand-400 flex-shrink-0' />
              <div>
                <span className='font-semibold block text-white'>Running AI Pipeline</span>
                <span>{stepMessage}</span>
              </div>
            </div>
          )}

          {/* Footer Actions */}
          <div className='flex items-center justify-between pt-4 border-t border-slate-800'>
            <button
              type='button'
              onClick={onClose}
              disabled={loading}
              className='px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white hover:bg-slate-800 transition-all'
            >
              Cancel
            </button>

            <button
              type='submit'
              disabled={loading}
              className='flex items-center gap-2 px-6 py-2.5 rounded-xl text-xs font-bold bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white shadow-lg shadow-brand-500/25 transition-all disabled:opacity-50'
            >
              {loading ? (
                <>
                  <Loader2 className='w-4 h-4 animate-spin' />
                  Analyzing JD & Resume...
                </>
              ) : (
                <>
                  <Sparkles className='w-4 h-4' />
                  Save Candidate & Launch Live Interview
                  <ArrowRight className='w-4 h-4' />
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
