import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { AuthModal } from './components/AuthModal';
import { CandidateSetupModal } from './components/CandidateSetupModal';
import { LandingPage } from './pages/LandingPage';
import { DashboardPage } from './pages/DashboardPage';
import { JDIntakePage } from './pages/JDIntakePage';
import { PracticeConfigPage } from './pages/PracticeConfigPage';
import { PracticeRunnerPage } from './pages/PracticeRunnerPage';
import { MockOARunnerPage } from './pages/MockOARunnerPage';
import { OAReportPage } from './pages/OAReportPage';
import { InterviewIntakePage } from './pages/InterviewIntakePage';
import { LiveInterviewPage } from './pages/LiveInterviewPage';
import { InterviewReportPage } from './pages/InterviewReportPage';
import { AdminReviewPage } from './pages/AdminReviewPage';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<string>('landing');
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

  const [candidate, setCandidate] = useState<{
    name: string;
    email: string;
    company: string;
    role: string;
  }>(() => {
    try {
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
    if (!currentUser && currentTab !== 'landing') {
      setCurrentTab('landing');
    }
  }, [currentUser, currentTab]);

  const handleAuthSuccess = (user: any, token: string) => {
    setCurrentUser(user);
    if (user) {
      setCandidate(prev => ({
        ...prev,
        name: user.name || prev.name,
        email: user.email || prev.email
      }));
    }
    setShowAuthModal(false);
  };

  const handleSignOut = () => {
    localStorage.removeItem('intervyn_token');
    localStorage.removeItem('intervyn_user');
    setCurrentUser(null);
    setCurrentTab('landing');
  };

  const handleAuthChange = (user: any) => {
    setCurrentUser(user);
    if (user) {
      setCandidate(prev => ({
        ...prev,
        name: user.name,
        email: user.email
      }));
    } else {
      setCandidate(prev => ({
        ...prev,
        name: 'Alex Mercer',
        email: 'alex.mercer@intervyn.ai'
      }));
    }
  };

  const handleNavigate = (tab: string, state?: any) => {
    if (tab !== 'landing' && !currentUser) {
      setShowAuthModal(true);
      return;
    }
    if (state) setNavState(state);
    setCurrentTab(tab);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleCandidateSetupSuccess = (data: {
    user: any;
    company: string;
    role: string;
    turn: any;
  }) => {
    const updated = {
      name: data.user.name,
      email: data.user.email,
      company: data.company,
      role: data.role
    };
    setCandidate(updated);
    setNavState({
      turn: data.turn,
      company: data.company,
      role: data.role,
      candidateName: data.user.name
    });
    setCurrentTab('live-interview');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100 antialiased selection:bg-brand-500/30 selection:text-white">
      {/* Top Navigation */}
      <Navbar 
        currentTab={currentTab} 
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
        onSuccess={handleCandidateSetupSuccess}
      />

      {/* Google Authentication Modal */}
      <AuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        onSuccess={handleAuthSuccess}
      />

      {/* Dynamic Page Views */}
      <main className="flex-1">
        {currentTab === 'landing' && (
          <LandingPage 
            onNavigate={handleNavigate} 
            currentUser={currentUser}
            onOpenAuth={() => setShowAuthModal(true)}
          />
        )}

        {currentTab === 'dashboard' && (
          <DashboardPage 
            onNavigate={handleNavigate} 
            candidate={candidate}
            onOpenCandidateSetup={() => setShowCandidateSetup(true)}
          />
        )}

        {currentTab === 'jd-intake' && (
          <JDIntakePage
            initialCompany={navState.company}
            initialRole={navState.role}
            onNavigate={handleNavigate}
          />
        )}

        {currentTab === 'practice' && (
          <PracticeConfigPage
            initialCompany={navState.company}
            initialRole={navState.role}
            onNavigate={handleNavigate}
          />
        )}

        {currentTab === 'practice-runner' && navState.session && (
          <PracticeRunnerPage
            session={navState.session}
            onBack={() => handleNavigate('practice')}
          />
        )}

        {currentTab === 'mock-oa' && (
          <MockOARunnerPage
            initialCompany={navState.company}
            initialRole={navState.role}
            onNavigate={handleNavigate}
          />
        )}

        {currentTab === 'oa-report' && navState.report && (
          <OAReportPage
            report={navState.report}
            onNavigate={handleNavigate}
          />
        )}

        {currentTab === 'interview' && (
          <InterviewIntakePage
            initialCompany={navState.company}
            initialRole={navState.role}
            onNavigate={handleNavigate}
          />
        )}

        {currentTab === 'live-interview' && navState.turn && (
          <LiveInterviewPage
            initialTurn={navState.turn}
            company={navState.company}
            role={navState.role}
            candidateName={navState.candidateName}
            onNavigate={handleNavigate}
          />
        )}

        {currentTab === 'interview-report' && navState.report && (
          <InterviewReportPage
            report={navState.report}
            onNavigate={handleNavigate}
          />
        )}

        {currentTab === 'admin-review' && (
          <AdminReviewPage />
        )}
      </main>

      {/* Footer */}
      <footer className="bg-[#070b14] border-t border-white/[0.06] py-10 text-xs text-slate-400">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex flex-col sm:flex-row items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-white text-sm">intervyn<span className="text-sky-400">.ai</span></span>
              <span className="text-slate-600">•</span>
              <span className="text-slate-400">The Technical Hiring & Assessment Studio</span>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-4 sm:gap-6 text-xs text-slate-400">
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              All Systems Operational
            </span>
            <span className="text-slate-700 hidden sm:inline">|</span>
            <span>Enterprise Proctoring</span>
            <span className="text-slate-700 hidden sm:inline">|</span>
            <span>18-Point Verification Standard</span>
          </div>
        </div>
      </footer>
    </div>
  );
};
