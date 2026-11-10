import { getAuthSession, setAuthSession, clearAuthSession, subscribeAuthSync } from './utils/auth_sync';
import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { AuthModal } from './components/AuthModal';
import { CandidateSetupModal } from './components/CandidateSetupModal';
import { LandingPage } from './pages/LandingPage';
import { DashboardPage } from './pages/DashboardPage';
import { JDIntakePage } from './pages/JDIntakePage';
import { PracticeConfigPage } from './pages/PracticeConfigPage';
import { PracticePage } from './pages/PracticePage';
import { TimedSessionPage } from './pages/TimedSessionPage';
import { PracticeDebugPage } from './pages/PracticeDebugPage';
import { PracticeRunnerPage } from './pages/PracticeRunnerPage';
import { MockOARunnerPage } from './pages/MockOARunnerPage';
import { OAReportPage } from './pages/OAReportPage';
import { InterviewIntakePage } from './pages/InterviewIntakePage';
import { LiveInterviewPage } from './pages/LiveInterviewPage';
import { InterviewReportPage } from './pages/InterviewReportPage';
import { AdminReviewPage } from './pages/AdminReviewPage';
import { CandidateProfile } from './types';
import { api } from './services/api';

const TAB_TO_PATH: Record<string, string> = {
  'landing': '/',
  'dashboard': '/dashboard',
  'jd-intake': '/role-profiler',
  'role-profiler': '/role-profiler',
  'practice': '/practice',
  'practice-runner': '/practice-runner',
  'mock-oa': '/mock-oa',
  'oa-report': '/oa-report',
  'interview': '/interview',
  'live-interview': '/live-interview',
  'interview-report': '/interview-report',
  'admin-review': '/admin-review',
};

const getActiveTab = (pathname: string): string => {
  if (pathname.startsWith('/practice')) return 'practice';
  if (pathname.startsWith('/dashboard')) return 'dashboard';
  if (pathname.startsWith('/role-profiler') || pathname.startsWith('/jd-intake')) return 'jd-intake';
  if (pathname.startsWith('/mock-oa')) return 'mock-oa';
  if (pathname.startsWith('/interview-report')) return 'interview-report';
  if (pathname.startsWith('/interview') || pathname.startsWith('/live-interview')) return 'interview';
  if (pathname.startsWith('/admin')) return 'admin-review';
  return 'landing';
};

const getProfileStorageKey = (userId?: string | null): string => {
  return userId ? `intervyn_candidate_profile_${userId}` : 'intervyn_candidate_profile_guest';
};

const getDefaultCandidateProfile = (user?: any): CandidateProfile => {
  if (user && user.name) {
    return {
      name: user.name,
      email: user.email || '',
      company: 'Google',
      role: 'Software Engineer II (L4)',
      experience: '1-3 years',
      resumeText: '',
      resumeWordCount: 0,
      jdText: ''
    };
  }
  return {
    name: 'Alex Mercer',
    email: 'alex.mercer@intervyn.ai',
    company: 'Google',
    role: 'Software Engineer II (L4)',
    experience: '1-3 years',
    resumeText: '',
    resumeWordCount: 0,
    jdText: ''
  };
};

export const App: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const [navState, setNavState] = useState<any>({});
  const [showCandidateSetup, setShowCandidateSetup] = useState<boolean>(false);
  const [showAuthModal, setShowAuthModal] = useState<boolean>(false);
  const [currentUser, setCurrentUser] = useState<any>(() => {
    try {
      return JSON.parse(localStorage.getItem('intervyn_user') || 'null');
    } catch {
      return null;
    }
  });

  const [candidate, setCandidate] = useState<CandidateProfile>(() => {
    try {
      const savedUser = JSON.parse(localStorage.getItem('intervyn_user') || 'null');
      const key = getProfileStorageKey(savedUser?.id);
      const savedProfile = localStorage.getItem(key);
      if (savedProfile) {
        return JSON.parse(savedProfile);
      }
      return getDefaultCandidateProfile(savedUser);
    } catch {
      return getDefaultCandidateProfile();
    }
  });

  const loadUserProfile = async (user: any) => {
    if (!user) {
      setCandidate(getDefaultCandidateProfile());
      return;
    }

    const key = getProfileStorageKey(user.id);
    let loadedFromCache = false;
    try {
      const cached = localStorage.getItem(key);
      if (cached) {
        const parsed = JSON.parse(cached);
        setCandidate(parsed);
        loadedFromCache = true;
      }
    } catch {}

    try {
      const serverProfile = await api.getCandidateProfile();
      if (serverProfile) {
        setCandidate(prev => {
          const merged: CandidateProfile = {
            ...prev,
            name: serverProfile.name || user.name || prev.name,
            email: serverProfile.email || user.email || prev.email,
            company: serverProfile.company || prev.company || 'Google',
            role: serverProfile.role || prev.role || 'Software Engineer II (L4)',
            experience: serverProfile.experience || prev.experience || '1-3 years',
            resumeText: serverProfile.resumeText !== undefined ? serverProfile.resumeText : prev.resumeText,
            resumeFileName: serverProfile.resumeFileName || prev.resumeFileName,
            resumeWordCount: serverProfile.resumeWordCount ?? prev.resumeWordCount ?? 0,
            jdText: serverProfile.jdText !== undefined ? serverProfile.jdText : prev.jdText
          };
          try {
            localStorage.setItem(key, JSON.stringify(merged));
          } catch {}
          return merged;
        });
      }
    } catch (e) {
      console.warn('Failed to fetch candidate profile from server:', e);
      if (!loadedFromCache) {
        setCandidate(getDefaultCandidateProfile(user));
      }
    }
  };

  useEffect(() => {
    if (currentUser?.id) {
      loadUserProfile(currentUser);
    }
  }, []);

  useEffect(() => {
    const unsubscribe = subscribeAuthSync((event) => {
      if (event.type === 'LOGOUT') {
        setCurrentUser(null);
        setCandidate(getDefaultCandidateProfile());
        navigate('/', { replace: true });
      } else if (event.type === 'LOGIN' || event.type === 'ACCOUNT_SWITCH') {
        if (event.user) {
          setCurrentUser(event.user);
          loadUserProfile(event.user);
        }
      }
    });
    return () => {
      unsubscribe();
    };
  }, [navigate]);

  // Strict gating: Non-authenticated users can only view the landing page
  useEffect(() => {
    if (!currentUser && location.pathname !== '/') {
      navigate('/', { replace: true });
    }
  }, [currentUser, location.pathname, navigate]);

  const handleSaveProfile = (updatedProfile: Partial<CandidateProfile>) => {
    setCandidate(prev => {
      const merged: CandidateProfile = {
        ...prev,
        ...updatedProfile,
        name: updatedProfile.name !== undefined ? updatedProfile.name : prev.name,
        email: updatedProfile.email !== undefined ? updatedProfile.email : prev.email,
        company: updatedProfile.company !== undefined ? updatedProfile.company : prev.company,
        role: updatedProfile.role !== undefined ? updatedProfile.role : prev.role,
        resumeText: updatedProfile.resumeText !== undefined ? updatedProfile.resumeText : prev.resumeText,
        resumeFileName: updatedProfile.resumeFileName !== undefined ? updatedProfile.resumeFileName : prev.resumeFileName,
        resumeWordCount: updatedProfile.resumeWordCount !== undefined ? updatedProfile.resumeWordCount : prev.resumeWordCount,
        jdText: updatedProfile.jdText !== undefined ? updatedProfile.jdText : prev.jdText
      };
      try {
        const key = getProfileStorageKey(currentUser?.id);
        localStorage.setItem(key, JSON.stringify(merged));
      } catch (e) {
        console.error('Failed to store candidate profile', e);
      }
      if (currentUser?.id) {
        api.updateCandidateProfile(merged).catch(err => {
          console.warn('Failed to persist profile to backend:', err);
        });
      }
      return merged;
    });
  };

  const handleAuthSuccess = (user: any, token: string) => {
    setAuthSession(token, user);
    setCurrentUser(user);
    loadUserProfile(user);
    setShowAuthModal(false);
  };

  const handleSignOut = () => {
    api.logout().catch(console.error);
    setCurrentUser(null);
    setCandidate(getDefaultCandidateProfile());
    navigate('/');
  };

  const handleAuthChange = (user: any) => {
    setCurrentUser(user);
    if (user) {
      loadUserProfile(user);
    } else {
      localStorage.removeItem('intervyn_token');
      localStorage.removeItem('intervyn_user');
      setCandidate(getDefaultCandidateProfile());
    }
  };

  const handleNavigate = (tab: string, state?: any) => {
    if (tab !== 'landing' && tab !== '/' && !currentUser) {
      setShowAuthModal(true);
      return;
    }
    if (state) setNavState(state);

    const targetPath = TAB_TO_PATH[tab] || (tab.startsWith('/') ? tab : `/${tab}`);
    navigate(targetPath, { state });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleCandidateSetupSuccess = (data: {
    user: any;
    company: string;
    role: string;
    turn: any;
    candidateName?: string;
  }) => {
    setShowCandidateSetup(false);
    const chosenName = data.candidateName || data.turn?.candidate_name || data.user?.name || 'Candidate';
    const updated: CandidateProfile = {
      ...candidate,
      name: chosenName,
      email: data.user?.email || candidate.email,
      company: data.company,
      role: data.role
    };
    handleSaveProfile(updated);
    const statePayload = {
      turn: data.turn,
      company: data.company,
      role: data.role,
      candidateName: chosenName
    };
    setNavState(statePayload);
    navigate('/live-interview', { state: statePayload });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen flex flex-col bg-bg text-text font-sans antialiased selection:bg-accent/25 selection:text-text">
      {/* Top Navigation (hidden during dedicated timed assessment runner to avoid double headers) */}
      {!location.pathname.startsWith('/practice/timed-session') && (
        <Navbar 
          currentTab={getActiveTab(location.pathname)} 
          setCurrentTab={handleNavigate} 
          candidate={candidate}
          onOpenCandidateSetup={() => {
            if (!currentUser) {
              setShowAuthModal(true);
              return;
            }
            setShowCandidateSetup(true);
          }}
          onAuthChange={handleAuthChange}
          currentUser={currentUser}
          onOpenAuth={() => setShowAuthModal(true)}
          onSignOut={handleSignOut}
        />
      )}

      {/* Candidate & Custom JD Setup Modal */}
      <CandidateSetupModal
        isOpen={showCandidateSetup}
        onClose={() => setShowCandidateSetup(false)}
        currentUser={currentUser}
        initialCandidate={candidate}
        onSaveProfile={handleSaveProfile}
        onSuccess={handleCandidateSetupSuccess}
      />

      {/* Google Authentication Modal */}
      <AuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        onSuccess={handleAuthSuccess}
      />

      {/* Dynamic Routed Page Views */}
      <main className="flex-1">
        <Routes>
          <Route
            path="/"
            element={
              <LandingPage 
                onNavigate={handleNavigate} 
                currentUser={currentUser}
                onOpenAuth={() => setShowAuthModal(true)}
              />
            }
          />

          <Route
            path="/dashboard"
            element={
              <DashboardPage 
                onNavigate={handleNavigate} 
                candidate={candidate}
                onOpenCandidateSetup={() => setShowCandidateSetup(true)}
              />
            }
          />

          <Route
            path="/role-profiler"
            element={
              <JDIntakePage
                initialCompany={navState.company || location.state?.company}
                initialRole={navState.role || location.state?.role}
                onNavigate={handleNavigate}
              />
            }
          />

          <Route
            path="/jd-intake"
            element={<Navigate to="/role-profiler" replace />}
          />

          <Route
            path="/practice"
            element={
              <PracticePage
                initialQuestionId={navState.questionId || location.state?.questionId}
                onNavigate={handleNavigate}
              />
            }
          />

          <Route
            path="/practice/timed-session/:sessionId"
            element={<TimedSessionPage />}
          />

          <Route
            path="/practice/timed-session"
            element={<TimedSessionPage />}
          />

          <Route
            path="/practice/:problemSlug"
            element={
              <PracticePage
                onNavigate={handleNavigate}
              />
            }
          />

          <Route
            path="/practice/:problemSlug/debug"
            element={<PracticeDebugPage />}
          />

          <Route
            path="/practice-runner"
            element={
              (navState.session || location.state?.session) ? (
                <PracticeRunnerPage
                  session={navState.session || location.state?.session}
                  onBack={() => handleNavigate('practice')}
                />
              ) : (
                <Navigate to="/practice" replace />
              )
            }
          />

          <Route
            path="/mock-oa"
            element={
              <MockOARunnerPage
                initialCompany={navState.company || location.state?.company}
                initialRole={navState.role || location.state?.role}
                onNavigate={handleNavigate}
              />
            }
          />

          <Route
            path="/oa-report"
            element={
              (navState.report || location.state?.report) ? (
                <OAReportPage
                  report={navState.report || location.state?.report}
                  onNavigate={handleNavigate}
                />
              ) : (
                <Navigate to="/dashboard" replace />
              )
            }
          />

          <Route
            path="/interview"
            element={
              <InterviewIntakePage
                initialCompany={navState.company || location.state?.company || candidate.company}
                initialRole={navState.role || location.state?.role || candidate.role}
                candidateProfile={candidate}
                onSaveProfile={handleSaveProfile}
                onNavigate={handleNavigate}
              />
            }
          />

          <Route
            path="/live-interview"
            element={
              (navState.turn || location.state?.turn) ? (
                <LiveInterviewPage
                  key={(navState.turn || location.state?.turn)?.session_id}
                  initialTurn={navState.turn || location.state?.turn}
                  company={navState.company || location.state?.company}
                  role={navState.role || location.state?.role}
                  candidateName={navState.candidateName || location.state?.candidateName}
                  onNavigate={handleNavigate}
                />
              ) : (
                <Navigate to="/interview" replace />
              )
            }
          />

          <Route
            path="/interview-report"
            element={
              (navState.report || location.state?.report) ? (
                <InterviewReportPage
                  report={navState.report || location.state?.report}
                  onNavigate={handleNavigate}
                />
              ) : (
                <Navigate to="/dashboard" replace />
              )
            }
          />

          <Route
            path="/admin-review"
            element={<AdminReviewPage />}
          />

          <Route
            path="*"
            element={<Navigate to="/" replace />}
          />
        </Routes>
      </main>

      {/* Footer */}
      <footer className="bg-bg border-t border-border py-8 text-xs text-text-muted">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-serif text-base text-text">intervyn</span>
            <span className="text-border">•</span>
            <span className="text-text-muted">Technical Hiring & Assessment Studio</span>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-4 sm:gap-6 text-xs text-text-muted font-mono">
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-success"></span>
              Systems Operational
            </span>
            <span className="text-border hidden sm:inline">/</span>
            <span>Deterministic Scoring</span>
            <span className="text-border hidden sm:inline">/</span>
            <span>Evidence-Backed Verification</span>
          </div>
        </div>
      </footer>
    </div>
  );
};
