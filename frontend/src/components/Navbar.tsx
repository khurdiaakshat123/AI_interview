import React, { useState, useEffect } from 'react';
import { 
  Sparkles, Terminal, Code2, Cpu, FileCheck2, UserCheck, Compass,
  ShieldCheck, Key, Check, Settings, X, ExternalLink, UserPlus, LogOut
} from 'lucide-react';
import { BASE_URL } from '../services/api';
import { AuthModal } from './AuthModal';

interface NavbarProps {
  currentTab: string;
  setCurrentTab: (tab: string) => void;
  candidate?: { name: string; email: string; company: string; role: string };
  onOpenCandidateSetup?: () => void;
  onAuthChange?: (user: any) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ 
  currentTab, 
  setCurrentTab,
  candidate = { name: "Alex Mercer", email: "alex.mercer@intervyn.ai", company: "Google", role: "Software Engineer II (L4)" },
  onOpenCandidateSetup,
  onAuthChange
}) => {
  const [showSettings, setShowSettings] = useState(false);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [currentUser, setCurrentUser] = useState<any>(() => {
    try {
      return JSON.parse(localStorage.getItem('intervyn_user') || 'null');
    } catch {
      return null;
    }
  });

  const [activeProvider, setActiveProvider] = useState('Loading...');
  const [geminiKey, setGeminiKey] = useState('');
  const [groqKey, setGroqKey] = useState('');
  const [openaiKey, setOpenaiKey] = useState('');
  const [anthropicKey, setAnthropicKey] = useState('');
  const [isSaved, setIsSaved] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const handleAuthSuccess = (user: any, token: string) => {
    setCurrentUser(user);
    if (onAuthChange) {
      onAuthChange(user);
    }
  };

  const handleSignOut = () => {
    localStorage.removeItem('intervyn_token');
    localStorage.removeItem('intervyn_user');
    setCurrentUser(null);
    if (onAuthChange) {
      onAuthChange(null);
    }
  };

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${BASE_URL}/settings/llm-status`);
      if (res.ok) {
        const data = await res.json();
        setActiveProvider(data.active_provider);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, [showSettings]);

  const handleSaveKeys = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      const res = await fetch(`${BASE_URL}/settings/llm-keys`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          gemini_key: geminiKey,
          groq_key: groqKey,
          openai_key: openaiKey,
          anthropic_key: anthropicKey
        })
      });
      if (res.ok) {
        const data = await res.json();
        setActiveProvider(data.active_provider);
        setIsSaved(true);
        setTimeout(() => setIsSaved(false), 3000);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsSaving(false);
    }
  };

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: Compass },
    { id: 'jd-intake', label: 'Role Profiler', icon: Sparkles },
    { id: 'practice', label: 'OA Practice', icon: Code2 },
    { id: 'mock-oa', label: 'Mock OA Exam', icon: Terminal },
    { id: 'interview', label: 'AI Interview', icon: Cpu },
    { id: 'admin-review', label: '18-Pt Audit Queue', icon: ShieldCheck },
  ];

  return (
    <header className="sticky top-0 z-50 bg-slate-900/80 backdrop-blur-md border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo */}
          <div 
            className="flex items-center gap-3 cursor-pointer group"
            onClick={() => setCurrentTab('landing')}
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-brand-500/20 group-hover:scale-105 transition-all">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="text-xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-brand-400 bg-clip-text text-transparent">
                intervyn<span className="text-brand-400">.ai</span>
              </span>
              <span className="hidden sm:inline-block ml-2 px-2 py-0.5 text-[10px] font-semibold bg-brand-950/60 text-brand-300 border border-brand-800/60 rounded-full">
                OA & Mock AI
              </span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = currentTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setCurrentTab(item.id)}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-brand-600/20 text-brand-300 border border-brand-500/30'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-brand-400' : 'text-slate-400'}`} />
                  {item.label}
                </button>
              );
            })}
          </nav>

          {/* Settings & Candidate Pill & Google Auth */}
          <div className="flex items-center gap-2 sm:gap-3">
            {/* Google Authentication Button / User Profile */}
            {currentUser ? (
              <div className="flex items-center gap-2 px-2.5 py-1 rounded-xl bg-slate-800/90 border border-slate-700/80 shadow-sm">
                {currentUser.avatar_url ? (
                  <img
                    src={currentUser.avatar_url}
                    alt={currentUser.name}
                    className="w-6 h-6 rounded-full object-cover border border-brand-400/50"
                  />
                ) : (
                  <div className="w-6 h-6 rounded-full bg-gradient-to-tr from-brand-600 to-indigo-600 flex items-center justify-center text-[10px] font-bold text-white uppercase">
                    {currentUser.name?.[0] || 'U'}
                  </div>
                )}
                <div className="hidden md:flex flex-col text-left leading-none">
                  <span className="text-xs font-bold text-white truncate max-w-[90px]">{currentUser.name}</span>
                  <span className="text-[10px] text-slate-400 truncate max-w-[90px]">{currentUser.email}</span>
                </div>
                <button
                  onClick={handleSignOut}
                  className="ml-1 p-1 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-700/50 transition-all"
                  title="Sign Out"
                >
                  <LogOut className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <button
                onClick={() => setShowAuthModal(true)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white hover:bg-slate-100 text-slate-900 text-xs font-bold transition-all shadow-sm shadow-white/10 active:scale-[0.98]"
                title="Sign in with Google"
              >
                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                </svg>
                <span className="hidden sm:inline">Google Sign In</span>
                <span className="sm:hidden">Sign In</span>
              </button>
            )}

            <button
              onClick={() => setShowSettings(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700 text-slate-300 hover:text-white hover:border-slate-600 text-xs font-semibold transition-all"
              title="Configure LLM & AI Models"
            >
              <Key className="w-3.5 h-3.5 text-amber-400" />
              <span className="hidden lg:inline">LLM Keys</span>
            </button>

            {/* Candidate Setup Trigger */}
            <button
              onClick={onOpenCandidateSetup}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-brand-600/30 to-indigo-600/30 border border-brand-500/40 text-brand-200 hover:text-white hover:border-brand-400 text-xs font-semibold transition-all shadow-sm shadow-brand-500/10"
              title="Setup New Candidate & Custom JD / Resume"
            >
              <UserPlus className="w-3.5 h-3.5 text-brand-400" />
              <span className="hidden sm:inline">New Candidate</span>
            </button>

            <div 
              onClick={onOpenCandidateSetup}
              className="hidden xl:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/60 border border-slate-700/60 text-xs cursor-pointer hover:border-slate-500 transition-all"
              title="Click to customize candidate or JD"
            >
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></div>
              <span className="text-slate-200 font-medium">{candidate.name}</span>
              <span className="text-slate-500">|</span>
              <span className="text-brand-400 font-mono truncate max-w-[120px]">{candidate.company}</span>
            </div>

            <button
              onClick={() => setCurrentTab('interview')}
              className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-brand-600 hover:bg-brand-500 text-white shadow-sm shadow-brand-500/20 transition-all whitespace-nowrap"
            >
              Start Live Mock
            </button>
          </div>
        </div>
      </div>

      {/* LLM Configuration Modal */}
      {showSettings && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-lg p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-brand-600/20 border border-brand-500/40 flex items-center justify-center">
                  <Key className="w-4 h-4 text-brand-400" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">AI Models & LLM Configuration</h3>
                  <p className="text-[11px] text-slate-400">Power Agent 1, Interview Agents, and Evaluation</p>
                </div>
              </div>
              <button
                onClick={() => setShowSettings(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Current Active Engine Badge */}
            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-xs space-y-1">
              <span className="text-slate-400 block text-[11px]">Currently Active AI Provider:</span>
              <span className="font-bold text-emerald-400 font-mono text-xs">{activeProvider}</span>
            </div>

            <form onSubmit={handleSaveKeys} className="space-y-3.5 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Google Gemini API Key (gemini-3.6-flash)
                </label>
                <input
                  type="password"
                  value={geminiKey}
                  onChange={(e) => setGeminiKey(e.target.value)}
                  placeholder="AQ... or AIzaSy..."
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:border-brand-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Groq API Key (GPT-OSS 120B / Qwen 27B)
                </label>
                <input
                  type="password"
                  value={groqKey}
                  onChange={(e) => setGroqKey(e.target.value)}
                  placeholder="gsk_..."
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:border-brand-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  OpenAI API Key (GPT-4o)
                </label>
                <input
                  type="password"
                  value={openaiKey}
                  onChange={(e) => setOpenaiKey(e.target.value)}
                  placeholder="sk-..."
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:border-brand-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Anthropic API Key (Claude 3.5 Sonnet)
                </label>
                <input
                  type="password"
                  value={anthropicKey}
                  onChange={(e) => setAnthropicKey(e.target.value)}
                  placeholder="sk-ant-..."
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:border-brand-500 focus:outline-none"
                />
              </div>

              <div className="text-[11px] text-slate-400 italic">
                * If no key is entered, the built-in <strong>Domain Expert Deterministic Engine</strong> provides accurate responses and evaluations.
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-slate-800">
                {isSaved ? (
                  <span className="text-emerald-400 text-xs font-semibold flex items-center gap-1.5">
                    <Check className="w-4 h-4" /> Keys updated & active!
                  </span>
                ) : (
                  <span />
                )}

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setShowSettings(false)}
                    className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300"
                  >
                    Close
                  </button>
                  <button
                    type="submit"
                    disabled={isSaving}
                    className="px-5 py-2 rounded-xl text-xs font-bold bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white flex items-center gap-1.5 shadow-sm"
                  >
                    {isSaving ? 'Saving...' : 'Save & Activate'}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Auth Modal (Google & Email) */}
      <AuthModal 
        isOpen={showAuthModal} 
        onClose={() => setShowAuthModal(false)} 
        onSuccess={handleAuthSuccess} 
      />
    </header>
  );
};
