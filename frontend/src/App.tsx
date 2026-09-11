import React, { useState } from 'react';
import { Navbar } from './components/Navbar';
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
          email: savedUser.email,
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

  const handleAuthChange = (user: any) => {
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
        onOpenCandidateSetup={() => setShowCandidateSetup(true)}
        onAuthChange={handleAuthChange}
      />

      {/* Candidate & Custom JD Setup Modal */}
      <CandidateSetupModal
        isOpen={showCandidateSetup}
        onClose={() => setShowCandidateSetup(false)}
        onSuccess={handleCandidateSetupSuccess}
      />

      {/* Dynamic Page Views */}
      <main className="flex-1">
        {currentTab === 'landing' && (
          <LandingPage onNavigate={handleNavigate} />
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
      <footer className="bg-slate-950 border-t border-slate-900 py-8 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-300">intervyn.ai</span>
            <span>•</span>
            <span>AI-Powered OA & Mock Interview Preparation Platform</span>
          </div>

          <div className="flex items-center gap-6 font-mono text-[11px]">
            <span>FastAPI Backend (:8000)</span>
            <span>SQLite / PostgreSQL Store</span>
            <span>18-Point Audit Verified</span>
          </div>
        </div>
      </footer>
    </div>
  );
};
