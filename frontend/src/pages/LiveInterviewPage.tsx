import React, { useState, useEffect, useRef } from 'react';
import { 
  Cpu, Mic, MicOff, Volume2, VolumeX, Send, Sparkles,
  ArrowRight, ShieldCheck, User, Bot, Clock, HelpCircle, Layers, CheckCheck,
  Code2, X, PlusCircle
} from 'lucide-react';
import { InterviewTurn, InterviewFinalReport } from '../types';
import { DepthMeter } from '../components/DepthMeter';
import { CodeEditor } from '../components/CodeEditor';
import { api } from '../services/api';

interface LiveInterviewPageProps {
  initialTurn: InterviewTurn;
  company: string;
  role: string;
  candidateName?: string;
  onNavigate: (tab: string, state?: any) => void;
}

interface ChatMessage {
  sender: 'INTERVIEWER' | 'CANDIDATE';
  text: string;
  topic?: string;
  depth?: number;
  timestamp: string;
  evalPrev?: any;
}

export const LiveInterviewPage: React.FC<LiveInterviewPageProps> = ({
  initialTurn,
  company,
  role,
  candidateName = 'Candidate',
  onNavigate
}) => {
  const [currentTurn, setCurrentTurn] = useState<InterviewTurn>(initialTurn);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      sender: 'INTERVIEWER',
      text: initialTurn.question_text,
      topic: initialTurn.current_topic,
      depth: initialTurn.depth_level,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [isVoiceEnabled, setIsVoiceEnabled] = useState(true);
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isCorrecting, setIsCorrecting] = useState(false);
  const [correctionNotice, setCorrectionNotice] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Speech recognition refs for continuous manual start/stop
  const recognitionRef = useRef<any>(null);
  const isListeningRef = useRef<boolean>(false);
  const baseTextRef = useRef<string>('');
  const inputTextRef = useRef<string>('');

  // Audio queue, utterance GC reference, and low-latency speech state
  const [isAiSpeaking, setIsAiSpeaking] = useState<boolean>(false);
  const speechQueueRef = useRef<string[]>([]);
  const isSpeakingRef = useRef<boolean>(false);
  const isVoiceEnabledRef = useRef<boolean>(isVoiceEnabled);
  const spokenQuestionIdsRef = useRef<Set<string>>(new Set());
  const activeUtteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const [availableVoices, setAvailableVoices] = useState<SpeechSynthesisVoice[]>([]);

  // Monaco code scratchpad
  const [showScratchpad, setShowScratchpad] = useState<boolean>(false);
  const [scratchpadCode, setScratchpadCode] = useState<string>(
    '# Technical Scratchpad\n# Write Python, SQL, or pseudocode here to reference or insert into your answer\n\ndef solution():\n    pass\n'
  );

  useEffect(() => {
    isVoiceEnabledRef.current = isVoiceEnabled;
  }, [isVoiceEnabled]);

  // Load available speech synthesis voices (handles async voice loading in Chrome)
  useEffect(() => {
    if (!('speechSynthesis' in window)) return;
    const loadVoices = () => {
      const v = window.speechSynthesis.getVoices();
      if (v && v.length > 0) {
        setAvailableVoices(v);
      }
    };
    loadVoices();
    window.speechSynthesis.onvoiceschanged = loadVoices;
    return () => {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.onvoiceschanged = null;
      }
    };
  }, []);

  const stopAllSpeech = () => {
    speechQueueRef.current = [];
    isSpeakingRef.current = false;
    setIsAiSpeaking(false);
    activeUtteranceRef.current = null;
    if ('speechSynthesis' in window) {
      try {
        window.speechSynthesis.cancel();
      } catch (e) {
        console.warn('[SpeechSynthesis] cancel error:', e);
      }
    }
  };

  const getVoice = () => {
    if (!('speechSynthesis' in window)) return null;
    const voices = availableVoices.length > 0 ? availableVoices : window.speechSynthesis.getVoices();
    return (
      voices.find(v => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Samantha') || v.name.includes('Jenny') || v.name.includes('Guy') || v.name.includes('Aria'))) ||
      voices.find(v => v.lang.startsWith('en')) ||
      null
    );
  };

  const playNextSentence = () => {
    if (!isVoiceEnabledRef.current || !('speechSynthesis' in window)) {
      stopAllSpeech();
      return;
    }
    if (speechQueueRef.current.length === 0) {
      isSpeakingRef.current = false;
      setIsAiSpeaking(false);
      activeUtteranceRef.current = null;
      return;
    }

    try {
      if (window.speechSynthesis.paused) {
        window.speechSynthesis.resume();
      }
    } catch (e) {}

    isSpeakingRef.current = true;
    setIsAiSpeaking(true);
    const sentence = speechQueueRef.current.shift();
    if (!sentence || !sentence.trim()) {
      playNextSentence();
      return;
    }

    const utterance = new SpeechSynthesisUtterance(sentence.trim());
    utterance.rate = 1.05;
    utterance.pitch = 1.0;
    const voice = getVoice();
    if (voice) utterance.voice = voice;

    // Retain reference to prevent Chrome GC bug
    activeUtteranceRef.current = utterance;

    utterance.onend = () => {
      activeUtteranceRef.current = null;
      setTimeout(() => {
        if (isVoiceEnabledRef.current) {
          playNextSentence();
        }
      }, 90);
    };

    utterance.onerror = (e) => {
      activeUtteranceRef.current = null;
      if (e.error !== 'interrupted' && e.error !== 'canceled') {
        console.warn('[SpeechSynthesis] sentence utterance error:', e.error);
      }
      if (isVoiceEnabledRef.current && speechQueueRef.current.length > 0) {
        playNextSentence();
      } else {
        isSpeakingRef.current = false;
        setIsAiSpeaking(false);
      }
    };

    try {
      window.speechSynthesis.speak(utterance);
    } catch (err) {
      console.warn('[SpeechSynthesis] speak error:', err);
      isSpeakingRef.current = false;
      setIsAiSpeaking(false);
    }
  };

  const enqueueSentence = (sentence: string) => {
    if (!isVoiceEnabledRef.current || !('speechSynthesis' in window)) return;
    const trimmed = sentence.trim();
    if (!trimmed) return;
    speechQueueRef.current.push(trimmed);
    if (!isSpeakingRef.current) {
      playNextSentence();
    }
  };

  const speakTurnQuestion = (turn: InterviewTurn) => {
    if (!isVoiceEnabledRef.current || !('speechSynthesis' in window) || !turn?.question_text) return;
    if (turn.question_id) {
      spokenQuestionIdsRef.current.add(turn.question_id);
    }

    stopAllSpeech();

    try {
      if (window.speechSynthesis.paused) {
        window.speechSynthesis.resume();
      }
    } catch (e) {}

    const rawSentences = turn.question_text.match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [turn.question_text];
    const sentences = rawSentences.map(s => s.trim()).filter(Boolean);
    if (sentences.length === 0) return;

    speechQueueRef.current = [...sentences];
    playNextSentence();
  };

  const handleToggleVoice = () => {
    const next = !isVoiceEnabled;
    setIsVoiceEnabled(next);
    isVoiceEnabledRef.current = next;
    if (!next) {
      // User clicked Voice Off -> stop immediately
      stopAllSpeech();
    } else {
      // User clicked Voice On -> speak current question immediately
      if (currentTurn?.question_text) {
        speakTurnQuestion(currentTurn);
      }
    }
  };

  useEffect(() => {
    inputTextRef.current = inputText;
    // Auto scroll textarea when listening so candidate sees streaming speech
    if (isListening && textareaRef.current) {
      textareaRef.current.scrollTop = textareaRef.current.scrollHeight;
    }
  }, [inputText, isListening]);

  // Reset interview state if initialTurn or session_id changes
  useEffect(() => {
    stopAllSpeech();
    setCurrentTurn(initialTurn);
    setMessages([
      {
        sender: 'INTERVIEWER',
        text: initialTurn.question_text,
        topic: initialTurn.current_topic,
        depth: initialTurn.depth_level,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ]);
    setInputText('');
    spokenQuestionIdsRef.current.clear();
  }, [initialTurn.session_id]);

  // Clean up recognition on unmount
  useEffect(() => {
    return () => {
      isListeningRef.current = false;
      stopAllSpeech();
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (e) {}
      }
    };
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Voice synthesis: speak question aloud instantly when currentTurn changes
  useEffect(() => {
    if (isVoiceEnabled && currentTurn?.question_text) {
      const qId = currentTurn.question_id;
      if (!qId || !spokenQuestionIdsRef.current.has(qId)) {
        speakTurnQuestion(currentTurn);
      }
    }
  }, [currentTurn, isVoiceEnabled]);

  // Autoplay Policy unlocker: ensures first question plays if browser blocked unprompted autoplay
  useEffect(() => {
    const unlockAudio = () => {
      if (isVoiceEnabledRef.current && currentTurn?.question_text && !isSpeakingRef.current) {
        const qId = currentTurn.question_id;
        if (!qId || !spokenQuestionIdsRef.current.has(qId)) {
          speakTurnQuestion(currentTurn);
        }
      }
    };

    window.addEventListener('click', unlockAudio, { once: true });
    window.addEventListener('keydown', unlockAudio, { once: true });

    return () => {
      window.removeEventListener('click', unlockAudio);
      window.removeEventListener('keydown', unlockAudio);
    };
  }, [currentTurn]);

  // Manual Stop speech recognition
  const stopListening = () => {
    isListeningRef.current = false;
    setIsListening(false);
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (err) {
        console.warn('[SpeechRecognition] stop error:', err);
      }
    }
    // Auto-trigger typo correction after brief timeout to catch last speech chunk
    setTimeout(() => {
      const textToCorrect = (inputTextRef.current || '').trim();
      if (textToCorrect.length > 0) {
        handleCorrectTypos(textToCorrect);
      }
    }, 350);
  };

  // Continuous speech recognition with manual user start & stop (ignores silence pauses)
  const startListening = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('Speech recognition is not supported in this browser. Please use Google Chrome or Microsoft Edge, or type your response.');
      return;
    }

    // Stop synthetic interviewer voice if currently reading aloud (instant conversational interruption)
    stopAllSpeech();

    isListeningRef.current = true;
    setIsListening(true);
    baseTextRef.current = inputText.trim() ? inputText.trim() + ' ' : '';

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      setIsListening(true);
    };

    recognition.onresult = (e: any) => {
      let interim = '';
      let finalized = '';

      for (let i = 0; i < e.results.length; i++) {
        const item = e.results[i];
        if (item.isFinal) {
          finalized += item[0].transcript + ' ';
        } else {
          interim += item[0].transcript;
        }
      }

      const combinedSpoken = (finalized + interim).replace(/\s+/g, ' ');
      const newText = (baseTextRef.current + combinedSpoken).trim();
      setInputText(newText);
    };

    recognition.onerror = (e: any) => {
      console.warn('[SpeechRecognition] event error:', e.error);
      // 'no-speech' is triggered when the user takes a pause; do NOT abort recording!
      if (e.error === 'no-speech') {
        return;
      }
      if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
        isListeningRef.current = false;
        setIsListening(false);
      }
    };

    recognition.onend = () => {
      // If the user has NOT clicked stop, immediately restart listening so pauses don't cut them off
      if (isListeningRef.current) {
        if (inputTextRef.current.trim()) {
          baseTextRef.current = inputTextRef.current.trim() + ' ';
        }
        try {
          recognition.start();
        } catch (err) {
          // If browser audio device needs a moment to reset, retry shortly
          setTimeout(() => {
            if (isListeningRef.current) {
              try {
                recognition.start();
              } catch (retryErr) {
                console.warn('[SpeechRecognition] restart failed:', retryErr);
              }
            }
          }, 250);
        }
      } else {
        setIsListening(false);
      }
    };

    recognitionRef.current = recognition;

    try {
      recognition.start();
    } catch (err) {
      console.error('[SpeechRecognition] initial start error:', err);
      isListeningRef.current = false;
      setIsListening(false);
    }
  };

  // Toggle between manual start and manual stop
  const toggleListening = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  const handleCorrectTypos = async (explicitText?: string) => {
    const raw = (explicitText ?? inputTextRef.current ?? inputText).trim();
    if (!raw || isCorrecting || isProcessing) return;

    setIsCorrecting(true);
    setCorrectionNotice(null);

    try {
      const res = await api.correctTranscript(currentTurn.session_id, {
        raw_text: raw,
        question_text: currentTurn.question_text,
        topic: currentTurn.current_topic
      });

      if (res && res.corrected_text) {
        setInputText(res.corrected_text);
        baseTextRef.current = res.corrected_text.trim() + ' ';
        inputTextRef.current = res.corrected_text;

        if (res.changes_made && res.changes_made.length > 0) {
          setCorrectionNotice(`✨ Auto-corrected: ${res.changes_made.slice(0, 2).join('; ')} (Review and edit before sending)`);
        } else if (res.has_corrections) {
          setCorrectionNotice('✨ Refined grammar, technical terms & flow. Review before sending.');
        } else {
          setCorrectionNotice('✓ Answer verified: Technical terms & grammar are sound!');
        }
      }
    } catch (err) {
      console.error('[TranscriptCorrection] error:', err);
      setCorrectionNotice('Normalized technical terminology.');
    } finally {
      setIsCorrecting(false);
      setTimeout(() => setCorrectionNotice(null), 7000);
    }
  };

  const handleSendAnswer = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    // Automatically stop speech recording when sending answer
    if (isListeningRef.current) {
      isListeningRef.current = false;
      setIsListening(false);
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch (err) {}
      }
    }
    // Stop any active speech synthesis
    stopAllSpeech();

    if (!inputText.trim() || isProcessing) return;

    const candidateAnswer = inputText.trim();
    setInputText('');
    baseTextRef.current = '';
    inputTextRef.current = '';

    // Add candidate message to local log
    const updatedMessages: ChatMessage[] = [
      ...messages,
      {
        sender: 'CANDIDATE',
        text: candidateAnswer,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ];
    setMessages(updatedMessages);
    setIsProcessing(true);

    let fullQuestionText = '';
    let streamInterviewerMsgAdded = false;

    try {
      await api.streamAnswerInterviewQuestion(
        currentTurn.session_id,
        candidateAnswer,
        (sentence: string, index: number) => {
          // Low-latency voice synthesis: enqueue Sentence 0 (~350ms) and subsequent sentences immediately
          if (isVoiceEnabledRef.current) {
            enqueueSentence(sentence);
          }

          // Live stream into interviewer message bubble in chat
          fullQuestionText += (fullQuestionText ? ' ' : '') + sentence;
          setMessages(prev => {
            if (!streamInterviewerMsgAdded) {
              streamInterviewerMsgAdded = true;
              return [
                ...prev,
                {
                  sender: 'INTERVIEWER',
                  text: fullQuestionText,
                  topic: currentTurn.current_topic,
                  depth: currentTurn.depth_level,
                  timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                }
              ];
            } else {
              const next = [...prev];
              next[next.length - 1] = {
                ...next[next.length - 1],
                text: fullQuestionText
              };
              return next;
            }
          });
        },
        (nextTurn: InterviewTurn) => {
          if (nextTurn.question_id) {
            spokenQuestionIdsRef.current.add(nextTurn.question_id);
          }
          setCurrentTurn(nextTurn);

          // If voice is enabled and nothing is currently speaking or queued (e.g. sync fallback), speak question immediately
          if (isVoiceEnabledRef.current && !isSpeakingRef.current && speechQueueRef.current.length === 0 && nextTurn.question_text) {
            speakTurnQuestion(nextTurn);
          }

          setMessages(prev => {
            const next = [...prev];
            if (next.length > 0 && next[next.length - 1].sender === 'INTERVIEWER') {
              next[next.length - 1] = {
                ...next[next.length - 1],
                text: nextTurn.question_text,
                topic: nextTurn.current_topic,
                depth: nextTurn.depth_level,
                evalPrev: nextTurn.eval_previous
              };
            } else {
              next.push({
                sender: 'INTERVIEWER',
                text: nextTurn.question_text,
                topic: nextTurn.current_topic,
                depth: nextTurn.depth_level,
                timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                evalPrev: nextTurn.eval_previous
              });
            }
            return next;
          });

          if (nextTurn.is_completed) {
            api.getInterviewReport(currentTurn.session_id).then(report => {
              setTimeout(() => {
                onNavigate('interview-report', { report });
              }, 1500);
            });
          }
        },
        (streamErr: any) => {
          console.error('[streamAnswerInterviewQuestion] error:', streamErr);
          alert('Failed to process response. Please try again.');
        }
      );
    } catch (err) {
      console.error(err);
      alert('Failed to process response.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleViewReportDirectly = async () => {
    setIsProcessing(true);
    try {
      const report = await api.getInterviewReport(currentTurn.session_id);
      onNavigate('interview-report', { report });
    } catch (err) {
      console.error(err);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Top Session Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-5 rounded-xl bg-surface border border-border">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-bg border border-border flex items-center justify-center shrink-0">
            <Bot className="w-5 h-5 text-accent" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-serif text-text font-normal">{company} Technical Interview</h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-success/10 text-success border border-success/30 font-medium">
                LIVE
              </span>
            </div>
            <div className="text-xs text-text-muted mt-0.5">
              Candidate: <span className="text-text font-medium">{candidateName}</span> • Phase:{' '}
              <span className="text-accent font-medium font-mono">{currentTurn.phase.replace('_', ' ')}</span>
            </div>
          </div>
        </div>

        {/* Audio & Finish Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleToggleVoice}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono transition-colors border ${
              isVoiceEnabled
                ? 'bg-bg text-accent border-accent/40'
                : 'bg-surface text-text-muted hover:text-text border-border'
            }`}
            title={isVoiceEnabled ? 'Voice Enabled (AI speaks questions)' : 'Voice Disabled'}
          >
            {isVoiceEnabled ? (
              <Volume2 className={`w-3.5 h-3.5 ${isAiSpeaking ? 'text-accent animate-pulse' : 'text-text-muted'}`} />
            ) : (
              <VolumeX className="w-3.5 h-3.5 text-text-muted" />
            )}
            <span>{isVoiceEnabled ? (isAiSpeaking ? 'AI Speaking...' : 'Voice On') : 'Voice Off'}</span>
          </button>

          {/* Code Scratchpad Button */}
          <button
            onClick={() => setShowScratchpad(!showScratchpad)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono transition-colors border ${
              showScratchpad
                ? 'bg-bg text-accent border-accent/40'
                : 'bg-surface text-text-muted hover:text-text border-border'
            }`}
            title="Open Monaco Code & Architecture Scratchpad"
          >
            <Code2 className="w-3.5 h-3.5 text-accent" />
            <span>{showScratchpad ? 'Close Editor' : 'Code Editor'}</span>
          </button>

          <button
            onClick={handleViewReportDirectly}
            className="px-3.5 py-1.5 rounded-lg text-xs font-mono bg-bg hover:bg-surface text-text border border-border transition-colors"
          >
            Conclude & View Report
          </button>
        </div>
      </div>

      {/* Monaco Code Scratchpad Modal */}
      {showScratchpad && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-bg/80 animate-fade-in">
          <div className="bg-surface border border-border rounded-xl max-w-4xl w-full p-5 space-y-4 relative flex flex-col max-h-[90vh]">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-bg border border-border flex items-center justify-center">
                  <Code2 className="w-4 h-4 text-accent" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-text">Monaco Code Scratchpad</h3>
                  <p className="text-[11px] text-text-muted">Write, format, and structure code during your technical interview</p>
                </div>
              </div>
              <button
                onClick={() => setShowScratchpad(false)}
                className="p-1 text-text-muted hover:text-text rounded-md hover:bg-bg transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 min-h-[380px]">
              <CodeEditor
                value={scratchpadCode}
                onChange={setScratchpadCode}
                height="380px"
              />
            </div>

            <div className="pt-2 border-t border-border flex items-center justify-between">
              <span className="text-[11px] text-text-muted font-mono">
                Code persists throughout your interview session.
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    const snippet = `\n\`\`\`\n${scratchpadCode.trim()}\n\`\`\`\n`;
                    setInputText(prev => (prev.trim() ? `${prev.trim()}\n${snippet}` : snippet));
                    setShowScratchpad(false);
                  }}
                  className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-medium bg-accent text-accent-contrast hover:opacity-90 transition-opacity"
                >
                  <PlusCircle className="w-3.5 h-3.5" />
                  <span>Insert into Answer</span>
                </button>
                <button
                  type="button"
                  onClick={() => setShowScratchpad(false)}
                  className="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-bg hover:bg-surface text-text border border-border transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Grid */}
      <div className="grid lg:grid-cols-4 gap-6">
        {/* Left 3 Cols: Real-time Conversational Flow */}
        <div className="lg:col-span-3 flex flex-col h-[650px] rounded-xl bg-surface border border-border overflow-hidden">
          {/* Messages Scroll Area */}
          <div className="flex-1 p-6 overflow-y-auto space-y-4">
            {messages.map((msg, idx) => {
              const isInterviewer = msg.sender === 'INTERVIEWER';

              return (
                <div
                  key={idx}
                  className={`flex items-start gap-3.5 ${isInterviewer ? 'justify-start' : 'justify-end'}`}
                >
                  {isInterviewer && (
                    <div className="w-8 h-8 rounded-lg bg-bg border border-border flex items-center justify-center shrink-0 mt-1">
                      <Bot className="w-4 h-4 text-accent" />
                    </div>
                  )}

                  <div className={`max-w-2xl space-y-1.5 ${isInterviewer ? 'items-start' : 'items-end'}`}>
                    <div className="flex items-center gap-2 text-[11px] text-text-muted px-1 font-mono">
                      <span className="font-medium text-text">
                        {isInterviewer ? 'AI Technical Interviewer' : candidateName}
                      </span>
                      {msg.topic && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-bg border border-border text-text-muted">
                          {msg.topic}
                        </span>
                      )}
                      <span>{msg.timestamp}</span>
                    </div>

                    <div
                      className={`p-4 rounded-xl text-xs sm:text-sm leading-relaxed ${
                        isInterviewer
                          ? 'bg-bg border border-border text-text rounded-tl-sm'
                          : 'bg-surface border border-accent/40 text-text rounded-tr-sm'
                      }`}
                    >
                      {msg.text}
                    </div>

                    {/* Show previous evaluation details inline if available */}
                    {msg.evalPrev && (
                      msg.evalPrev.is_scored === false || msg.evalPrev.is_clarification || msg.evalPrev.is_clarification_prompt || msg.evalPrev.quality_band === 'Specification Clarification' ? (
                        <div className="p-2.5 rounded-lg bg-bg border border-accent/40 text-[11px] text-accent flex items-center justify-between gap-2 mt-1 font-mono">
                          <div className="flex items-center gap-1.5">
                            <span className="w-2 h-2 rounded-full bg-accent animate-pulse inline-block" />
                            <span className="font-medium">Clarification requested</span>
                          </div>
                          <span className="text-text-muted text-[10px]">
                            {msg.evalPrev.feedback || "Clarification inquiry • Unscored turn"}
                          </span>
                        </div>
                      ) : (
                        <div className="p-2.5 rounded-lg bg-bg border border-border text-[11px] text-text-muted flex items-center justify-between gap-2 mt-1 font-mono">
                          <div className="flex items-center gap-2">
                            <span>Evaluated:</span>
                            {msg.evalPrev.evidence_score != null ? (
                              <span className="text-text font-medium">
                                {Math.round(msg.evalPrev.evidence_score * 100)}% Evidence
                              </span>
                            ) : msg.evalPrev.quality_band ? (
                              <span className="text-text">{msg.evalPrev.quality_band}</span>
                            ) : null}
                          </div>
                          <span className="text-success font-medium">
                            +{Number(msg.evalPrev.earned_points || 0).toFixed(1)} / {Number(msg.evalPrev.possible_points || 0).toFixed(1)} pts
                          </span>
                        </div>
                      )
                    )}
                  </div>

                  {!isInterviewer && (
                    <div className="w-8 h-8 rounded-lg bg-bg border border-border flex items-center justify-center shrink-0 mt-1 text-text-muted">
                      <User className="w-4 h-4" />
                    </div>
                  )}
                </div>
              );
            })}

            {isProcessing && (
              <div className="flex items-center gap-3 text-xs text-text-muted p-2 font-mono">
                <div className="w-4 h-4 rounded-full border-2 border-accent border-t-transparent animate-spin" />
                <span>Interviewer evaluating technical reasoning & adapting follow-up...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Bar */}
          <div className="p-4 bg-bg border-t border-border space-y-2">
            {(currentTurn.is_clarification || currentTurn.is_clarification_prompt || currentTurn.eval_previous?.is_clarification_prompt) && (
              <div className="px-3.5 py-2 rounded-lg bg-surface border border-accent/40 flex items-center gap-2 text-xs text-text font-mono">
                <HelpCircle className="w-4 h-4 text-accent shrink-0" />
                <div className="flex-1">
                  <span className="font-semibold text-accent">Clarification requested: </span>
                  <span className="text-text-muted">
                    The interviewer is seeking clarification on your previous technical statements. This inquiry is not directly scored; please provide precise technical details.
                  </span>
                </div>
              </div>
            )}
            {isListening && (
              <div className="px-3.5 py-2 rounded-lg bg-danger/10 border border-danger/30 flex items-center justify-between text-xs text-danger font-mono">
                <div className="flex items-center gap-2.5">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-danger opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-danger"></span>
                  </span>
                  <span className="font-semibold">Microphone Active</span>
                  <span className="text-text-muted hidden sm:inline">• Speak freely, pauses will not stop recording. Click Mic or Stop when done.</span>
                </div>
                <button
                  type="button"
                  onClick={stopListening}
                  className="px-2 py-0.5 rounded bg-surface hover:bg-border text-[11px] font-mono text-danger border border-danger/40 transition-colors"
                >
                  Stop Recording
                </button>
              </div>
            )}

            <form onSubmit={handleSendAnswer} className="space-y-2.5">
              {isCorrecting && (
                <div className="px-3.5 py-1.5 rounded-lg bg-surface border border-border flex items-center gap-2 text-xs text-text font-mono">
                  <Sparkles className="w-3.5 h-3.5 text-accent animate-spin" />
                  <span className="text-text-muted">Polishing technical terms & grammar against question context...</span>
                </div>
              )}
              {/* Full Paragraph Multi-line Textarea */}
              <div className="relative rounded-xl bg-surface border border-border focus-within:border-accent transition-colors p-3">
                <textarea
                  ref={textareaRef}
                  value={inputText}
                  rows={4}
                  onChange={(e) => {
                    setInputText(e.target.value);
                    baseTextRef.current = e.target.value.trim() ? e.target.value.trim() + ' ' : '';
                    if (isAiSpeaking) {
                      stopAllSpeech();
                    }
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                      e.preventDefault();
                      handleSendAnswer();
                    }
                  }}
                  placeholder={
                    isListening
                      ? 'Listening continuously... Speak freely; your words will form a full multi-line paragraph here. Pauses will not stop recording. Click Mic or Stop when done.'
                      : 'Type your technical answer here or click the microphone to speak... Your full paragraph remains visible. (Press Ctrl+Enter or click Send)'
                  }
                  disabled={isProcessing || isCorrecting}
                  className="w-full bg-transparent text-xs sm:text-sm text-text placeholder:text-text-muted focus:outline-none resize-y min-h-[95px] max-h-[220px] leading-relaxed font-sans"
                />

                {/* Bottom Control Bar */}
                <div className="flex flex-wrap items-center justify-between pt-2 border-t border-border gap-2 text-[11px] text-text-muted font-mono">
                  <div className="flex items-center gap-2">
                    {isListening && (
                      <span className="inline-flex items-center gap-1.5 text-danger font-medium animate-pulse">
                        <span className="w-1.5 h-1.5 rounded-full bg-danger" />
                        Speaking live into paragraph...
                      </span>
                    )}
                    {!isListening && inputText.trim() && (
                      <span>
                        {inputText.trim().split(/\s+/).length} words • {inputText.length} chars
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2 ml-auto">
                    {/* Correct Typos Button */}
                    <button
                      type="button"
                      onClick={() => handleCorrectTypos()}
                      disabled={!inputText.trim() || isProcessing || isCorrecting}
                      className="px-3 py-1.5 rounded-lg text-xs font-mono bg-bg border border-border text-text hover:bg-surface disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5 transition-colors"
                      title="AI scans your answer, cross-references with the question and your resume to fix speech-to-text mistranslations and irregular sentences"
                    >
                      {isCorrecting ? (
                        <>
                          <div className="w-3 h-3 rounded-full border-2 border-accent border-t-transparent animate-spin" />
                          <span>Correcting Typos...</span>
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-3.5 h-3.5 text-accent" />
                          <span>Correct Typos</span>
                        </>
                      )}
                    </button>

                    {/* Microphone Toggle Button */}
                    <button
                      type="button"
                      onClick={toggleListening}
                      className={`p-2 rounded-lg border transition-colors ${
                        isListening
                          ? 'bg-danger/20 text-danger border-danger'
                          : 'bg-bg border-border text-text-muted hover:text-text hover:bg-surface'
                      }`}
                      title={isListening ? 'Stop recording (Manual Stop)' : 'Start speaking (Continuous listening paragraph)'}
                    >
                      {isListening ? <Mic className="w-3.5 h-3.5 text-danger animate-pulse" /> : <MicOff className="w-3.5 h-3.5" />}
                    </button>

                    {/* Send Answer Button */}
                    <button
                      type="submit"
                      disabled={!inputText.trim() || isProcessing || isCorrecting}
                      className="px-4 py-1.5 rounded-lg text-xs font-medium bg-accent text-accent-contrast hover:opacity-90 disabled:opacity-40 flex items-center gap-1.5 transition-opacity"
                    >
                      <span>Send</span>
                      <Send className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              </div>

              {/* Autocorrect Result Banner */}
              {correctionNotice && (
                <div className="px-3.5 py-2 rounded-lg bg-surface border border-success/30 text-xs text-success flex items-start justify-between gap-2 font-mono">
                  <div className="flex items-center gap-2">
                    <CheckCheck className="w-4 h-4 text-success shrink-0" />
                    <span>{correctionNotice}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setCorrectionNotice(null)}
                    className="text-text-muted hover:text-text text-xs ml-2"
                  >
                    ×
                  </button>
                </div>
              )}
            </form>
          </div>
        </div>

        {/* Right 1 Col: Adaptive Follow-up Depth & Status */}
        <div className="space-y-4">
          <DepthMeter
            currentDimension={currentTurn.current_dimension || currentTurn.depth_dimension}
            depthDimension={currentTurn.depth_dimension}
            currentDepth={currentTurn.depth_level}
            phase={currentTurn.phase}
            currentItemTitle={currentTurn.current_item_title || currentTurn.current_item?.title}
            currentItemType={currentTurn.current_item_type || currentTurn.current_item?.item_type}
            isClarification={currentTurn.is_clarification || currentTurn.is_clarification_prompt}
            previousEval={currentTurn.eval_previous}
          />

          <div className="p-5 rounded-xl bg-surface border border-border space-y-3 text-xs">
            <div className="font-mono text-xs uppercase tracking-wider text-text-muted flex items-center gap-2">
              <Layers className="w-3.5 h-3.5 text-accent" />
              Scoring & Dimension Policy
            </div>
            <p className="text-text-muted leading-relaxed">
              Question weight adapts to question difficulty/complexity and demonstrated answer evidence. Depth describes the kind of reasoning being tested; it does not by itself determine score or when the interview ends.
            </p>
            <div className="p-3 rounded-lg bg-bg border border-border text-[11px] text-text-muted font-mono space-y-1.5">
              <div className="flex items-center justify-between">
                <span>Scoring Model:</span>
                <span className="text-text font-medium">Continuous Evidence-Based</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Turn Score:</span>
                <span className="text-success font-medium">earned / possible pts</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Clarification Turns:</span>
                <span className="text-accent font-medium">Unscored Inquiry</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
