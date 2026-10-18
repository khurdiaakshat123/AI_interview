import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { 
  Sparkles, Terminal, Code2, Cpu, FileCheck2, UserCheck, Compass,
  Key, Check, Settings, X, ExternalLink, UserPlus, LogOut,
  ChevronDown, FileText, Briefcase
} from 'lucide-react';
import { BASE_URL } from '../services/api';
import { AuthModal } from './AuthModal';
import { CandidateProfile } from '../types';
import { ThemeToggle } from './ThemeToggle';

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
    <header className="sticky top-0 z-50 bg-bg border-b border-border transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Wordmark & Mark */}
          <div 
            className="flex items-center gap-[10px] cursor-pointer select-none group"
            onClick={() => setCurrentTab('landing')}
          >
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none" className="shrink-0">
              <rect x="0.5" y="0.5" width="27" height="27" rx="7" stroke="var(--border)" fill="var(--surface)"/>
              <circle cx="14" cy="8.5" r="2.2" fill="var(--accent)"/>
              <rect x="12.4" y="13" width="3.2" height="9" rx="1.2" fill="var(--text)"/>
            </svg>
            <span className="font-serif text-[26px] text-text tracking-tight font-normal leading-none">
              Intervyn
            </span>
          </div>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-8 ml-8 mr-auto">
            {navItems.map((item) => {
              const isActive = currentTab === item.id;
              const displayLabel = item.id === 'jd-intake' ? 'Role profiler' : item.label;
              return (
                <button
                  key={item.id}
                  onClick={() => handleNavClick(item.id)}
                  className={`text-[14px] font-medium transition-colors ${
                    isActive ? 'text-text font-semibold' : 'text-text-muted hover:text-text'
                  }`}
                >
                  {displayLabel}
                </button>
              );
            })}
          </nav>

          {/* Top Right: Candidate Switcher & User Profile */}
          <div className="flex items-center gap-4">
            {/* Active Candidate & Target Role Switcher */}
            {currentUser && (
              <button
                type="button"
                onClick={handleCandidateSetupClick}
                className="hidden sm:flex items-center gap-1.5 text-[13px] text-text-muted hover:text-text transition-colors group cursor-pointer"
                title="Click to switch candidate, upload new resume, or change target position"
              >
                <span className="text-text font-medium">{candidate.name || 'Candidate'}</span>
                <span>·</span>
                <span>Targeting {candidate.company || 'Google'}, {candidate.role || 'SWE II'}</span>
              </button>
            )}

            {/* Theme Toggle Button */}
            <ThemeToggle />

            {currentUser ? (
              <div>
                {/* Circular Profile Button on Side */}
                <button
                  type="button"
                  onClick={() => setProfileDropdownOpen(prev => !prev)}
                  className={`relative w-8 h-8 rounded-full flex items-center justify-center transition-colors focus:outline-none ${
                    profileDropdownOpen 
                      ? 'border-2 border-accent' 
                      : 'border border-border hover:border-text text-text'
                  }`}
                  title={`${currentUser.name || candidate.name} - View Profile & Actions`}
                >
                  {currentUser.avatar_url ? (
                    <img
                      src={currentUser.avatar_url}
                      alt={currentUser.name || candidate.name}
                      className="w-full h-full rounded-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full rounded-full bg-surface flex items-center justify-center text-xs font-serif font-medium text-text">
                      {(currentUser.name || candidate.name)?.[0]?.toUpperCase() || 'A'}
                    </div>
                  )}
                </button>
              </div>
            ) : (
              <button
                onClick={triggerOpenAuth}
                className="flex items-center gap-2 px-3.5 py-1.5 rounded-md bg-accent hover:opacity-90 text-accent-contrast text-xs font-medium transition-opacity"
                title="Sign in with Google"
              >
                <span>Sign In</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Extreme Right Slide-out Drawer mounted directly on document.body via Portal */}
      {profileDropdownOpen && typeof document !== 'undefined' && createPortal(
        <>
          {/* Backdrop Overlay */}
          <div
            className="fixed inset-0 bg-black/60 z-[9998] transition-opacity"
            onClick={() => setProfileDropdownOpen(false)}
            aria-hidden="true"
          />

          {/* Extreme Right Drawer */}
          <div
            ref={profileMenuRef}
            className="fixed top-0 right-0 bottom-0 h-screen w-80 sm:w-96 max-w-[85vw] bg-surface border-l border-border z-[9999] flex flex-col justify-between p-6 overflow-y-auto animate-in slide-in-from-right duration-200"
          >
            <div className="space-y-4">
              {/* Drawer Header with Title and Close X Button */}
              <div className="flex items-center justify-between pb-3.5 border-b border-border">
                <div className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-success"></span>
                  <span className="text-xs font-mono uppercase tracking-wider text-text-muted">
                    Candidate Profile
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setProfileDropdownOpen(false)}
                  className="p-1 rounded-md text-text-muted hover:text-text hover:bg-surface-hover transition-colors"
                  title="Close Profile Panel"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* User Identity Header */}
              <div className="flex items-center gap-3.5 p-3.5 rounded-xl bg-bg border border-border">
                {currentUser?.avatar_url ? (
                  <img
                    src={currentUser.avatar_url}
                    alt={currentUser.name || candidate.name}
                    className="w-10 h-10 rounded-full object-cover border border-border shrink-0"
                  />
                ) : (
                  <div className="w-10 h-10 rounded-full bg-surface border border-border flex items-center justify-center text-sm font-mono font-medium text-text shrink-0">
                    {(currentUser?.name || candidate.name)?.[0] || 'U'}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-medium text-text truncate">
                      {currentUser?.name || candidate.name}
                    </h4>
                    <span className="px-1.5 py-0.2 rounded text-[10px] font-mono text-success bg-success-subtle border border-success/30 shrink-0">
                      Active
                    </span>
                  </div>
                  <p className="text-xs text-text-muted truncate font-mono mt-0.5">
                    {currentUser?.email || candidate.email}
                  </p>
                </div>
              </div>

              {/* Target Position Card */}
              <div className="p-3.5 rounded-xl bg-bg border border-border space-y-1">
                <div className="flex items-center justify-between text-[11px] font-mono text-text-muted">
                  <span>Target Position</span>
                  <span className="text-success text-[10px]">Configured</span>
                </div>
                <div className="text-xs font-semibold text-text truncate">{candidate.role || 'Software Engineer'}</div>
                <div className="text-[11px] font-mono text-text-muted truncate">{candidate.company || 'Target Company'}</div>
              </div>

              {/* Stored Resume Status Card */}
              <div className="p-3.5 rounded-xl bg-bg border border-border flex items-center justify-between gap-3">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="w-8 h-8 rounded-lg bg-surface border border-border flex items-center justify-center shrink-0 text-text-muted">
                    <FileText className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs font-medium text-text truncate">
                      {candidate.resumeFileName || (candidate.resumeText ? 'Resume Attached' : 'No Resume Uploaded')}
                    </div>
                    <div className="text-[11px] text-text-muted truncate font-mono">
                      {candidate.resumeText 
                        ? `${candidate.resumeWordCount || candidate.resumeText.split(/\s+/).filter(Boolean).length} words • Stored`
                        : 'Upload in profile'}
                    </div>
                  </div>
                </div>
                {candidate.resumeText ? (
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono text-success bg-success-subtle border border-success/30 shrink-0">
                    Ready
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono text-text-muted bg-surface border border-border shrink-0">
                    Not Set
                  </span>
                )}
              </div>

              {/* Profile & Resume Actions */}
              <div className="pt-1 space-y-1">
                <div className="text-[11px] font-mono uppercase tracking-wider text-text-muted px-1 pb-1">
                  Account & Profile
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setProfileDropdownOpen(false);
                    handleCandidateSetupClick();
                  }}
                  className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-medium text-text bg-bg hover:bg-surface-hover border border-border transition-colors text-left group"
                >
                  <FileText className="w-4 h-4 text-text-muted shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-medium text-text truncate">Update Profile & Resume</div>
                    <div className="text-[11px] text-text-muted truncate">Change resume file, target role, or company</div>
                  </div>
                </button>
              </div>

              {/* Platform Modes Shortcuts */}
              <div className="pt-2 space-y-1">
                <div className="text-[11px] font-mono uppercase tracking-wider text-text-muted px-1 pb-1">
                  Preparation Studio
                </div>

                <button
                  type="button"
                  onClick={() => {
                    setProfileDropdownOpen(false);
                    handleNavClick('interview');
                  }}
                  className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium text-text hover:bg-surface-hover border border-transparent hover:border-border transition-colors text-left"
                >
                  <Cpu className="w-4 h-4 text-text-muted shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-medium text-text truncate">1-on-1 AI Interview</div>
                    <div className="text-[11px] text-text-muted truncate">Deep situational interview tailored to JD</div>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setProfileDropdownOpen(false);
                    handleNavClick('mock-oa');
                  }}
                  className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium text-text hover:bg-surface-hover border border-transparent hover:border-border transition-colors text-left"
                >
                  <Terminal className="w-4 h-4 text-text-muted shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-medium text-text truncate">Timed Assessment (Mock OA)</div>
                    <div className="text-[11px] text-text-muted truncate">60-minute coding exam simulation</div>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setProfileDropdownOpen(false);
                    handleNavClick('practice');
                  }}
                  className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium text-text hover:bg-surface-hover border border-transparent hover:border-border transition-colors text-left"
                >
                  <Code2 className="w-4 h-4 text-text-muted shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-medium text-text truncate">Targeted Skill Practice</div>
                    <div className="text-[11px] text-text-muted truncate">Coding questions with hints & solutions</div>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setProfileDropdownOpen(false);
                    handleNavClick('dashboard');
                  }}
                  className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium text-text hover:bg-surface-hover border border-transparent hover:border-border transition-colors text-left"
                >
                  <Compass className="w-4 h-4 text-text-muted shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-medium text-text truncate">Candidate Dashboard</div>
                    <div className="text-[11px] text-text-muted truncate">Readiness scores & past attempts</div>
                  </div>
                </button>
              </div>
            </div>

            {/* Drawer Bottom: Sign Out */}
            <div className="pt-4 border-t border-border mt-4">
              <button
                type="button"
                onClick={() => {
                  setProfileDropdownOpen(false);
                  handleSignOut();
                }}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-md text-xs font-medium text-danger hover:bg-danger-subtle border border-border hover:border-danger/40 transition-colors"
              >
                <LogOut className="w-3.5 h-3.5" />
                Sign Out
              </button>
            </div>
          </div>
        </>,
        document.body
      )}

      {/* LLM Configuration Modal */}
      {showSettings && (
        <div className="fixed inset-0 z-50 bg-bg/80 flex items-center justify-center p-4">
          <div className="w-full max-w-lg p-6 rounded-xl bg-surface border border-border space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-border">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-bg border border-border flex items-center justify-center">
                  <Key className="w-4 h-4 text-text-muted" />
                </div>
                <div>
                  <h3 className="font-serif text-lg font-normal text-text">AI Models & LLM Configuration</h3>
                  <p className="text-xs text-text-muted">Power Agent 1, Interview Agents, and Evaluation</p>
                </div>
              </div>
              <button
                onClick={() => setShowSettings(false)}
                className="p-1 rounded-lg text-text-muted hover:text-text hover:bg-surface-hover transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Current Active Engine Badge */}
            <div className="p-3.5 rounded-lg bg-bg border border-border text-xs space-y-1">
              <span className="text-text-muted block text-[11px] font-mono uppercase">Currently Active AI Provider:</span>
              <span className="font-medium text-text font-mono text-xs">{activeProvider}</span>
            </div>

            <form onSubmit={handleSaveKeys} className="space-y-3.5 text-xs">
              <div>
                <label className="block text-text font-medium mb-1">
                  Google Gemini API Key (gemini-3.6-flash)
                </label>
                <input
                  type="password"
                  value={geminiKey}
                  onChange={(e) => setGeminiKey(e.target.value)}
                  placeholder="AQ... or AIzaSy..."
                  className="w-full px-3 py-2 rounded-lg bg-bg border border-border text-xs text-text placeholder-text-muted/50 focus:border-accent focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-text font-medium mb-1">
                  Groq API Key (GPT-OSS 120B / Qwen 27B)
                </label>
                <input
                  type="password"
                  value={groqKey}
                  onChange={(e) => setGroqKey(e.target.value)}
                  placeholder="gsk_..."
                  className="w-full px-3 py-2 rounded-lg bg-bg border border-border text-xs text-text placeholder-text-muted/50 focus:border-accent focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-text font-medium mb-1">
                  OpenAI API Key (GPT-4o)
                </label>
                <input
                  type="password"
                  value={openaiKey}
                  onChange={(e) => setOpenaiKey(e.target.value)}
                  placeholder="sk-..."
                  className="w-full px-3 py-2 rounded-lg bg-bg border border-border text-xs text-text placeholder-text-muted/50 focus:border-accent focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-text font-medium mb-1">
                  Anthropic API Key (Claude 3.5 Sonnet)
                </label>
                <input
                  type="password"
                  value={anthropicKey}
                  onChange={(e) => setAnthropicKey(e.target.value)}
                  placeholder="sk-ant-..."
                  className="w-full px-3 py-2 rounded-lg bg-bg border border-border text-xs text-text placeholder-text-muted/50 focus:border-accent focus:outline-none"
                />
              </div>

              <div className="text-[11px] text-text-muted italic">
                * If no key is entered, the built-in <strong>Domain Expert Deterministic Engine</strong> provides accurate responses and evaluations.
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-border">
                {isSaved ? (
                  <span className="text-success text-xs font-medium flex items-center gap-1.5">
                    <Check className="w-4 h-4" /> Keys updated & active!
                  </span>
                ) : (
                  <span />
                )}

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setShowSettings(false)}
                    className="px-4 py-2 rounded-lg text-xs font-medium bg-surface hover:bg-surface-hover text-text border border-border transition-colors"
                  >
                    Close
                  </button>
                  <button
                    type="submit"
                    disabled={isSaving}
                    className="px-5 py-2 rounded-lg text-xs font-medium bg-accent text-accent-contrast disabled:opacity-50 hover:opacity-90 transition-opacity"
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
