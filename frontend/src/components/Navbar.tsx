import React, { useState, useEffect, useRef } from 'react';
import { 
  Sparkles, Terminal, Code2, Cpu, FileCheck2, UserCheck, Compass,
  Key, Check, Settings, X, ExternalLink, UserPlus, LogOut,
  ChevronDown, FileText, Briefcase
} from 'lucide-react';
import { BASE_URL } from '../services/api';
import { AuthModal } from './AuthModal';
import { CandidateProfile } from '../types';

interface NavbarProps {
  currentTab: string;
  setCurrentTab: (tab: string) => void;
  candidate?: CandidateProfile;
  onOpenCandidateSetup?: () => void;
  onAuthChange?: (user: any) => void;
  currentUser?: any;
  onOpenAuth?: () => void;
  onSignOut?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ 
  currentTab, 
  setCurrentTab,
  candidate = { name: "Alex Mercer", email: "alex.mercer@intervyn.ai", company: "Google", role: "Software Engineer II (L4)" },
  onOpenCandidateSetup,
  onAuthChange,
  currentUser: propUser,
  onOpenAuth,
  onSignOut
}) => {
  const [showSettings, setShowSettings] = useState(false);
  const [internalAuthModal, setInternalAuthModal] = useState(false);
  const [profileDropdownOpen, setProfileDropdownOpen] = useState(false);
  const profileMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (profileMenuRef.current && !profileMenuRef.current.contains(event.target as Node)) {
        setProfileDropdownOpen(false);
      }
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setProfileDropdownOpen(false);
      }
    }
    if (profileDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [profileDropdownOpen]);

  const [internalUser, setInternalUser] = useState<any>(() => {
    try {
      return JSON.parse(localStorage.getItem('intervyn_user') || 'null');
    } catch {
      return null;
    }
  });

  const currentUser = propUser !== undefined ? propUser : internalUser;

  const triggerOpenAuth = () => {
    if (onOpenAuth) {
      onOpenAuth();
    } else {
      setInternalAuthModal(true);
    }
  };

  const [activeProvider, setActiveProvider] = useState('Loading...');
  const [geminiKey, setGeminiKey] = useState('');
  const [groqKey, setGroqKey] = useState('');
  const [openaiKey, setOpenaiKey] = useState('');
  const [anthropicKey, setAnthropicKey] = useState('');
  const [isSaved, setIsSaved] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const handleAuthSuccess = (user: any, token: string) => {
    setInternalUser(user);
    if (onAuthChange) {
      onAuthChange(user);
    }
  };

  const handleSignOut = () => {
    localStorage.removeItem('intervyn_token');
    localStorage.removeItem('intervyn_user');
    setInternalUser(null);
    if (onSignOut) {
      onSignOut();
    } else if (onAuthChange) {
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
  ];

  const handleNavClick = (tabId: string) => {
    if (!currentUser) {
      triggerOpenAuth();
      return;
    }
    setCurrentTab(tabId);
  };

  const handleSettingsClick = () => {
    if (!currentUser) {
      triggerOpenAuth();
      return;
    }
    setShowSettings(true);
  };

  const handleCandidateSetupClick = () => {
    if (!currentUser) {
      triggerOpenAuth();
      return;
    }
    if (onOpenCandidateSetup) onOpenCandidateSetup();
  };



  return (
    <header className="sticky top-0 z-50 bg-[#070b14]/85 backdrop-blur-xl border-b border-white/[0.08] transition-all">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo */}
          <div 
            className="flex items-center gap-3 cursor-pointer group"
            onClick={() => setCurrentTab('landing')}
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/25 group-hover:scale-105 group-hover:shadow-indigo-500/40 transition-all">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div className="flex items-center">
              <span className="text-xl font-extrabold tracking-tight text-white group-hover:text-slate-100 transition-colors">
                intervyn<span className="bg-gradient-to-r from-sky-400 to-indigo-400 bg-clip-text text-transparent">.ai</span>
              </span>
              <span className="hidden sm:inline-flex items-center gap-1.5 ml-3 px-2.5 py-0.5 text-[11px] font-medium bg-gradient-to-r from-blue-500/10 to-indigo-500/10 text-sky-300 border border-sky-500/20 rounded-full">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                Technical Interview & Assessment
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
                  onClick={() => handleNavClick(item.id)}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold tracking-wide transition-all ${
                    isActive
                      ? 'bg-gradient-to-r from-blue-600/20 to-indigo-600/20 text-sky-300 border border-sky-500/30 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.1)]'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-sky-400' : 'text-slate-400'}`} />
                  {item.label}
                </button>
              );
            })}
          </nav>

          {/* Top Right: Unified User Profile Dropdown */}
          <div className="flex items-center gap-3">
            {currentUser ? (
              <div>
                {/* Circular Profile Button on Side */}
                <button
                  type="button"
                  onClick={() => setProfileDropdownOpen(prev => !prev)}
                  className={`relative w-9 h-9 sm:w-10 sm:h-10 rounded-full flex items-center justify-center transition-all shadow-md group focus:outline-none ${
                    profileDropdownOpen 
                      ? 'ring-2 ring-sky-400 ring-offset-2 ring-offset-slate-950 scale-105' 
                      : 'hover:scale-105 hover:ring-2 hover:ring-indigo-500/50'
                  }`}
                  title={`${currentUser.name || candidate.name} - View Profile & Actions`}
                >
                  {currentUser.avatar_url ? (
                    <img
                      src={currentUser.avatar_url}
                      alt={currentUser.name || candidate.name}
                      className="w-full h-full rounded-full object-cover border-2 border-indigo-500/60 group-hover:border-sky-400 transition-colors"
                    />
                  ) : (
                    <div className="w-full h-full rounded-full bg-gradient-to-tr from-blue-600 via-indigo-600 to-violet-600 border-2 border-indigo-400/50 flex items-center justify-center text-xs sm:text-sm font-bold text-white uppercase shadow-inner group-hover:border-sky-300 transition-colors">
                      {(currentUser.name || candidate.name)?.[0] || 'U'}
                    </div>
                  )}
                  <span className="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full bg-emerald-400 border-2 border-slate-950"></span>
                </button>

                {/* Extreme Right Slide-out Drawer */}
                {profileDropdownOpen && (
                  <>
                    {/* Backdrop Overlay */}
                    <div
                      className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 transition-opacity animate-in fade-in duration-200"
                      onClick={() => setProfileDropdownOpen(false)}
                      aria-hidden="true"
                    />

                    {/* Extreme Right Drawer */}
                    <div
                      ref={profileMenuRef}
                      className="fixed top-0 right-0 bottom-0 w-80 sm:w-96 max-w-[85vw] bg-[#090e1a]/98 backdrop-blur-2xl border-l border-white/10 shadow-2xl shadow-black z-50 flex flex-col justify-between p-5 sm:p-6 overflow-y-auto animate-in slide-in-from-right duration-250"
                    >
                      <div className="space-y-4">
                        {/* Drawer Header with Title and Close X Button */}
                        <div className="flex items-center justify-between pb-3.5 border-b border-white/[0.08]">
                          <div className="flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                            <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                              Candidate Profile
                            </span>
                          </div>
                          <button
                            type="button"
                            onClick={() => setProfileDropdownOpen(false)}
                            className="p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-white/[0.08] transition-all"
                            title="Close Profile Panel"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>

                        {/* User Identity Header */}
                        <div className="flex items-center gap-3.5 p-3.5 rounded-2xl bg-slate-950/70 border border-white/[0.06]">
                          {currentUser.avatar_url ? (
                            <img
                              src={currentUser.avatar_url}
                              alt={currentUser.name || candidate.name}
                              className="w-12 h-12 rounded-full object-cover border-2 border-indigo-500/70 shadow-md shrink-0"
                            />
                          ) : (
                            <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-blue-600 via-indigo-600 to-violet-600 flex items-center justify-center text-base font-bold text-white uppercase shadow-inner shrink-0 border border-indigo-400/40">
                              {(currentUser.name || candidate.name)?.[0] || 'U'}
                            </div>
                          )}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <h4 className="text-sm font-bold text-white truncate">
                                {currentUser.name || candidate.name}
                              </h4>
                              <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 shrink-0">
                                Active
                              </span>
                            </div>
                            <p className="text-xs text-slate-400 truncate font-mono mt-0.5">
                              {currentUser.email || candidate.email}
                            </p>
                          </div>
                        </div>

                        {/* Target Position Card */}
                        <div className="p-3.5 rounded-2xl bg-slate-950/70 border border-white/[0.06] space-y-1">
                          <div className="flex items-center justify-between text-[10px] text-slate-400">
                            <span>Target Role & Company</span>
                            <span className="text-emerald-400 font-mono text-[9px] font-semibold">Configured</span>
                          </div>
                          <div className="text-xs font-bold text-white truncate">{candidate.role || 'Software Engineer'}</div>
                          <div className="text-[11px] font-medium text-sky-400 font-mono truncate">{candidate.company || 'Target Company'}</div>
                        </div>

                        {/* Stored Resume Status Card */}
                        <div className="p-3.5 rounded-2xl bg-slate-950/70 border border-white/[0.06] flex items-center justify-between gap-3">
                          <div className="flex items-center gap-2.5 min-w-0">
                            <div className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${
                              candidate.resumeText ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-slate-800 text-slate-400'
                            }`}>
                              <FileText className="w-4 h-4" />
                            </div>
                            <div className="min-w-0">
                              <div className="text-xs font-semibold text-white truncate">
                                {candidate.resumeFileName || (candidate.resumeText ? 'Resume Attached' : 'No Resume Uploaded')}
                              </div>
                              <div className="text-[10px] text-slate-400 truncate font-mono">
                                {candidate.resumeText 
                                  ? `${candidate.resumeWordCount || candidate.resumeText.split(/\s+/).filter(Boolean).length} words • Loaded`
                                  : 'Upload in profile'}
                              </div>
                            </div>
                          </div>
                          {candidate.resumeText ? (
                            <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 shrink-0">
                              Ready
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded-full text-[9px] font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/30 shrink-0">
                              Not Set
                            </span>
                          )}
                        </div>

                        {/* Profile & Resume Actions */}
                        <div className="pt-1 space-y-1">
                          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 px-1 pb-1">
                            Account & Profile
                          </div>
                          <button
                            type="button"
                            onClick={() => {
                              setProfileDropdownOpen(false);
                              handleCandidateSetupClick();
                            }}
                            className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-medium text-slate-200 hover:text-white bg-slate-950/40 hover:bg-white/[0.06] border border-white/5 hover:border-white/10 transition-all text-left group"
                          >
                            <FileText className="w-4 h-4 text-indigo-400 shrink-0 group-hover:scale-110 transition-transform" />
                            <div className="flex-1 min-w-0">
                              <div className="text-xs font-semibold text-slate-200 group-hover:text-white truncate">Update Profile & Resume</div>
                              <div className="text-[10px] text-slate-400 truncate">Change resume file, target role, or company</div>
                            </div>
                          </button>
                        </div>

                        {/* Platform Modes Shortcuts */}
                        <div className="pt-2 space-y-1">
                          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 px-1 pb-1">
                            Preparation Studio
                          </div>

                          <button
                            type="button"
                            onClick={() => {
                              setProfileDropdownOpen(false);
                              handleNavClick('interview');
                            }}
                            className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium text-slate-300 hover:text-white hover:bg-white/[0.06] transition-all text-left group"
                          >
                            <Cpu className="w-4 h-4 text-sky-400 shrink-0 group-hover:scale-110 transition-transform" />
                            <div className="flex-1 min-w-0">
                              <div className="text-xs font-semibold text-slate-200 group-hover:text-white truncate">1-on-1 AI Interview</div>
                              <div className="text-[10px] text-slate-500 truncate">Deep situational interview tailored to JD</div>
                            </div>
                          </button>

                          <button
                            type="button"
                            onClick={() => {
                              setProfileDropdownOpen(false);
                              handleNavClick('mock-oa');
                            }}
                            className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium text-slate-300 hover:text-white hover:bg-white/[0.06] transition-all text-left group"
                          >
                            <Terminal className="w-4 h-4 text-cyan-400 shrink-0 group-hover:scale-110 transition-transform" />
                            <div className="flex-1 min-w-0">
                              <div className="text-xs font-semibold text-slate-200 group-hover:text-white truncate">Timed Assessment (Mock OA)</div>
                              <div className="text-[10px] text-slate-500 truncate">60-minute coding exam simulation</div>
                            </div>
                          </button>

                          <button
                            type="button"
                            onClick={() => {
                              setProfileDropdownOpen(false);
                              handleNavClick('practice');
                            }}
                            className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium text-slate-300 hover:text-white hover:bg-white/[0.06] transition-all text-left group"
                          >
                            <Code2 className="w-4 h-4 text-indigo-400 shrink-0 group-hover:scale-110 transition-transform" />
                            <div className="flex-1 min-w-0">
                              <div className="text-xs font-semibold text-slate-200 group-hover:text-white truncate">Targeted Skill Practice</div>
                              <div className="text-[10px] text-slate-500 truncate">Coding questions with hints & solutions</div>
                            </div>
                          </button>

                          <button
                            type="button"
                            onClick={() => {
                              setProfileDropdownOpen(false);
                              handleNavClick('dashboard');
                            }}
                            className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium text-slate-300 hover:text-white hover:bg-white/[0.06] transition-all text-left group"
                          >
                            <Compass className="w-4 h-4 text-slate-400 shrink-0 group-hover:scale-110 transition-transform" />
                            <div className="flex-1 min-w-0">
                              <div className="text-xs font-semibold text-slate-200 group-hover:text-white truncate">Candidate Dashboard</div>
                              <div className="text-[10px] text-slate-500 truncate">Readiness scores & past attempts</div>
                            </div>
                          </button>
                        </div>
                      </div>

                      {/* Drawer Bottom: Sign Out */}
                      <div className="pt-4 border-t border-white/[0.08] mt-4">
                        <button
                          type="button"
                          onClick={() => {
                            setProfileDropdownOpen(false);
                            handleSignOut();
                          }}
                          className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl text-xs font-semibold text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 border border-rose-500/20 hover:border-rose-500/40 transition-all"
                        >
                          <LogOut className="w-3.5 h-3.5" />
                          Sign Out
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </div>
            ) : (
              <button
                onClick={triggerOpenAuth}
                className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-white hover:bg-slate-100 text-slate-900 text-xs font-bold transition-all shadow-md shadow-white/10 active:scale-[0.98]"
                title="Sign in with Google"
              >
                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                </svg>
                <span>Sign In</span>
              </button>
            )}
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

      {/* Auth Modal (Google & Email) fallback when unmanaged by parent */}
      {!onOpenAuth && (
        <AuthModal 
          isOpen={internalAuthModal} 
          onClose={() => setInternalAuthModal(false)} 
          onSuccess={handleAuthSuccess} 
        />
      )}
    </header>
  );
};
