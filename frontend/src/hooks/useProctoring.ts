import { useState, useEffect, useRef, useCallback } from 'react';
import { ProctoringIncident, ProctoringSummary } from '../types';

interface UseProctoringOptions {
  assessmentId?: string;
  isEnabled?: boolean;
  warnOnTabSwitch?: boolean;
  warnOnPaste?: boolean;
  maxAllowedTabSwitches?: number;
}

export interface ProctoringAlert {
  id: string;
  type: 'warning' | 'danger';
  title: string;
  message: string;
  timestamp: string;
}

export const useProctoring = ({
  assessmentId = 'session',
  isEnabled = true,
  warnOnTabSwitch = true,
  warnOnPaste = true,
  maxAllowedTabSwitches = 3
}: UseProctoringOptions = {}) => {
  const [tabSwitchCount, setTabSwitchCount] = useState<number>(0);
  const [windowBlurCount, setWindowBlurCount] = useState<number>(0);
  const [pasteBurstCount, setPasteBurstCount] = useState<number>(0);
  const [fullscreenExits, setFullscreenExits] = useState<number>(0);
  const [totalTimeAwaySeconds, setTotalTimeAwaySeconds] = useState<number>(0);
  const [incidents, setIncidents] = useState<ProctoringIncident[]>([]);
  const [currentAlert, setCurrentAlert] = useState<ProctoringAlert | null>(null);

  const awayStartTimeRef = useRef<number | null>(null);
  const startTimeRef = useRef<number>(Date.now());
  const alertTimeoutRef = useRef<any>(null);

  const showAlert = useCallback((title: string, message: string, type: 'warning' | 'danger' = 'warning') => {
    if (alertTimeoutRef.current) clearTimeout(alertTimeoutRef.current);
    const alert: ProctoringAlert = {
      id: Math.random().toString(36).slice(2, 9),
      type,
      title,
      message,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    };
    setCurrentAlert(alert);
    alertTimeoutRef.current = setTimeout(() => {
      setCurrentAlert(null);
    }, 6000);
  }, []);

  const addIncident = useCallback((type: ProctoringIncident['type'], detail: string, duration?: number) => {
    const newIncident: ProctoringIncident = {
      type,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      detail,
      duration_seconds: duration
    };
    setIncidents(prev => [...prev, newIncident]);
  }, []);

  // 1. Tab visibility tracking (document.visibilitychange)
  useEffect(() => {
    if (!isEnabled) return;

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'hidden') {
        awayStartTimeRef.current = Date.now();
        setTabSwitchCount(prev => {
          const next = prev + 1;
          addIncident('TAB_SWITCH', 'Navigated away from assessment tab (Incident #' + next + ')');
          if (warnOnTabSwitch) {
            const isDanger = next >= maxAllowedTabSwitches;
            showAlert(
              isDanger ? 'Critical Proctoring Alert' : 'Assessment Tab Focus Lost',
              isDanger
                ? 'You have switched tabs ' + next + ' times. Continued infractions may result in assessment flag.'
                : 'Tab switch detected (#' + next + '). Please remain on the assessment window.',
              isDanger ? 'danger' : 'warning'
            );
          }
          return next;
        });
      } else if (document.visibilityState === 'visible') {
        if (awayStartTimeRef.current) {
          const duration = Math.round((Date.now() - awayStartTimeRef.current) / 1000);
          setTotalTimeAwaySeconds(prev => prev + duration);
          awayStartTimeRef.current = null;
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [isEnabled, warnOnTabSwitch, maxAllowedTabSwitches, addIncident, showAlert]);

  // 2. Window Blur tracking (losing application focus or moving to secondary monitor)
  useEffect(() => {
    if (!isEnabled) return;

    const handleBlur = () => {
      if (document.visibilityState !== 'hidden') {
        setWindowBlurCount(prev => {
          const next = prev + 1;
          addIncident('WINDOW_BLUR', 'Window lost focus (Incident #' + next + ')');
          return next;
        });
      }
    };

    window.addEventListener('blur', handleBlur);
    return () => {
      window.removeEventListener('blur', handleBlur);
    };
  }, [isEnabled, addIncident]);

  // 3. Paste Burst tracking
  useEffect(() => {
    if (!isEnabled) return;

    const handlePaste = (e: ClipboardEvent) => {
      const pastedText = e.clipboardData?.getData('text') || '';
      if (pastedText.length > 60) {
        setPasteBurstCount(prev => {
          const next = prev + 1;
          addIncident('PASTE_BURST', 'Large text paste detected (' + pastedText.length + ' characters)');
          if (warnOnPaste) {
            showAlert(
              'Large Paste Event Detected',
              'Pasted ' + pastedText.length + ' characters. Code structure will be verified for integrity & original authorship.',
              'warning'
            );
          }
          return next;
        });
      }
    };

    window.addEventListener('paste', handlePaste);
    return () => {
      window.removeEventListener('paste', handlePaste);
    };
  }, [isEnabled, warnOnPaste, addIncident, showAlert]);

  // Dynamic integrity score (0-100)
  const rawScore = 100 - (tabSwitchCount * 6) - (windowBlurCount * 2) - (pasteBurstCount * 5) - Math.floor(totalTimeAwaySeconds / 5) * 2;
  const integrityScore = Math.max(0, Math.min(100, rawScore));

  const integrityStatus: ProctoringSummary['integrity_status'] =
    integrityScore >= 85 ? 'HIGH_INTEGRITY' :
    integrityScore >= 65 ? 'MODERATE_CONCERN' : 'FLAGGED_FOR_REVIEW';

  const totalSessionSeconds = Math.max(1, Math.round((Date.now() - startTimeRef.current) / 1000));
  const focusPercentage = Math.max(0, Math.min(100, Math.round(((totalSessionSeconds - totalTimeAwaySeconds) / totalSessionSeconds) * 100)));

  const getProctoringSummary = useCallback((): ProctoringSummary => {
    return {
      integrity_score: integrityScore,
      integrity_status: integrityStatus,
      tab_switch_count: tabSwitchCount,
      window_blur_count: windowBlurCount,
      paste_burst_count: pasteBurstCount,
      fullscreen_exits: fullscreenExits,
      total_time_away_seconds: totalTimeAwaySeconds,
      focus_percentage: focusPercentage,
      incidents
    };
  }, [integrityScore, integrityStatus, tabSwitchCount, windowBlurCount, pasteBurstCount, fullscreenExits, totalTimeAwaySeconds, focusPercentage, incidents]);

  return {
    integrityScore,
    integrityStatus,
    tabSwitchCount,
    windowBlurCount,
    pasteBurstCount,
    fullscreenExits,
    totalTimeAwaySeconds,
    focusPercentage,
    incidents,
    currentAlert,
    clearAlert: () => setCurrentAlert(null),
    getProctoringSummary
  };
};
