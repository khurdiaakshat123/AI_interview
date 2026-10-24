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
import { PracticeRunnerPage } from './pages/PracticeRunnerPage';
import { MockOARunnerPage } from './pages/MockOARunnerPage';
import { OAReportPage } from './pages/OAReportPage';
import { InterviewIntakePage } from './pages/InterviewIntakePage';
import { LiveInterviewPage } from './pages/LiveInterviewPage';
import { InterviewReportPage } from './pages/InterviewReportPage';
import { AdminReviewPage } from './pages/AdminReviewPage';
import { CandidateProfile } from './types';

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
      const savedProfile = localStorage.getItem('intervyn_candidate_profile');
      if (savedProfile) {
        return JSON.parse(savedProfile);
      }
      const savedUser = JSON.parse(localStorage.getItem('intervyn_user') || 'null');
      if (savedUser && savedUser.name) {
        return {
          name: savedUser.name,
          email: savedUser.email || '',
          company: 'Google',
          role: 'Software Engineer II (L4)'
        };
      }
    } catch {}
    return {
      name: 'Alex Mercer',
      email: 'alex.mercer@intervyn.ai',
      company: 'Google',
      role: 'Software Engineer II (L4)'
    };
  });

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
        name: updatedProfile.name || prev.name,
        email: updatedProfile.email || prev.email,
        company: updatedProfile.company || prev.company,
        role: updatedProfile.role || prev.role
      };
      try {
        localStorage.setItem('intervyn_candidate_profile', JSON.stringify(merged));
      } catch (e) {
        console.error('Failed to store candidate profile', e);
      }
      return merged;
    });
  };

  const handleAuthSuccess = (user: any, token: string) => {
    setCurrentUser(user);
    if (user) {
      handleSaveProfile({
        name: user.name || candidate.name,
        email: user.email || candidate.email
      });
    }
    setShowAuthModal(false);
  };

  const handleSignOut = () => {
    localStorage.removeItem('intervyn_token');
    localStorage.removeItem('intervyn_user');
    setCurrentUser(null);
    navigate('/');
  };

  const handleAuthChange = (user: any) => {
    setCurrentUser(user);
    if (user) {
      handleSaveProfile({
        name: user.name,
        email: user.email
      });
    } else {
      setCandidate(prev => ({
        ...prev,
        name: 'Alex Mercer',
        email: 'alex.mercer@intervyn.ai'
      }));
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
      {/* Top Navigation */}
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
            path="/practice/:problemSlug"
            element={
              <PracticePage
                onNavigate={handleNavigate}
              />
            }
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
