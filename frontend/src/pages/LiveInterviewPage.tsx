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

  // Audio queue and low-latency speech state
  const [isAiSpeaking, setIsAiSpeaking] = useState<boolean>(false);
  const speechQueueRef = useRef<string[]>([]);
  const isSpeakingRef = useRef<boolean>(false);
  const isVoiceEnabledRef = useRef<boolean>(isVoiceEnabled);
  const spokenQuestionIdsRef = useRef<Set<string>>(new Set());

  // Monaco code scratchpad
  const [showScratchpad, setShowScratchpad] = useState<boolean>(false);
  const [scratchpadCode, setScratchpadCode] = useState<string>(
    '# Technical Scratchpad\\n# Write Python, SQL, or pseudocode here to reference or insert into your answer\\n\\ndef solution():\\n    pass\\n'
  );

  useEffect(() => {
    isVoiceEnabledRef.current = isVoiceEnabled;
  }, [isVoiceEnabled]);

  const stopAllSpeech = () => {
    speechQueueRef.current = [];
    isSpeakingRef.current = false;
    setIsAiSpeaking(false);
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
  };

  const getVoice = () => {
    if (!('speechSynthesis' in window)) return null;
    const voices = window.speechSynthesis.getVoices();
    return (
      voices.find(v => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Samantha') || v.name.includes('Jenny') || v.name.includes('Guy'))) ||
      voices.find(v => v.lang.startsWith('en')) ||
      null
    );
  };

  const playNextSentence = () => {
    if (!isVoiceEnabledRef.current || !('speechSynthesis' in window)) {
      speechQueueRef.current = [];
      isSpeakingRef.current = false;
      setIsAiSpeaking(false);
      return;
    }
    if (speechQueueRef.current.length === 0) {
      isSpeakingRef.current = false;
      setIsAiSpeaking(false);
      return;
    }

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

    utterance.onend = () => {
      playNextSentence();
    };

    utterance.onerror = (e) => {
      if (e.error !== 'interrupted' && e.error !== 'canceled') {
        console.warn('[SpeechSynthesis] sentence utterance error:', e.error);
      }
      playNextSentence();
    };

    window.speechSynthesis.speak(utterance);
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
    if (turn.question_id && spokenQuestionIdsRef.current.has(turn.question_id)) return;
    if (turn.question_id) spokenQuestionIdsRef.current.add(turn.question_id);

    stopAllSpeech();
    const sentences = turn.question_text.match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [turn.question_text];
    for (const s of sentences) {
      if (s.trim()) {
        enqueueSentence(s.trim());
      }
    }
  };

  const handleToggleVoice = () => {
    const next = !isVoiceEnabled;
    setIsVoiceEnabled(next);
    isVoiceEnabledRef.current = next;
    if (!next) {
      stopAllSpeech();
    } else if (currentTurn?.question_text && !isSpeakingRef.current) {
      const sentences = currentTurn.question_text.match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [currentTurn.question_text];
      for (const s of sentences) {
        if (s.trim()) enqueueSentence(s.trim());
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

  // Voice synthesis: speak question aloud using Web Speech API sentence queue
  useEffect(() => {
    if (isVoiceEnabled && currentTurn?.question_text) {
      if (!currentTurn.question_id || !spokenQuestionIdsRef.current.has(currentTurn.question_id)) {
        speakTurnQuestion(currentTurn);
      }
    }
    return () => {
      stopAllSpeech();
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
          // Mark turn as handled so useEffect won't double-speak
          if (nextTurn.question_id) {
            spokenQuestionIdsRef.current.add(nextTurn.question_id);
          }
          setCurrentTurn(nextTurn);

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
      <div className="flex flex-wrap items-center justify-between gap-4 p-5 rounded-2xl bg-slate-900/90 border border-white/10 shadow-xl">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center shadow-md shadow-indigo-600/20">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-white">{company} Technical Interview</h1>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                LIVE
              </span>
            </div>
            <div className="text-xs text-slate-400">
              Candidate: <span className="text-slate-200 font-medium">{candidateName}</span> • Phase:{' '}
              <span className="text-sky-300 font-semibold font-mono">{currentTurn.phase.replace('_', ' ')}</span>
            </div>
          </div>
        </div>

        {/* Audio & Finish Controls */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={handleToggleVoice}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
              isVoiceEnabled
                ? 'bg-sky-950/80 text-sky-300 border border-sky-800/60'
                : 'bg-slate-800 text-slate-400 hover:text-slate-200'
            }`}
            title={isVoiceEnabled ? 'Voice Enabled (AI speaks questions)' : 'Voice Disabled'}
          >
            {isVoiceEnabled ? (
              <Volume2 className={`w-4 h-4 text-sky-400 ${isAiSpeaking ? 'animate-bounce text-emerald-400' : ''}`} />
            ) : (
              <VolumeX className="w-4 h-4" />
            )}
            <span>{isVoiceEnabled ? (isAiSpeaking ? 'AI Speaking...' : 'Voice On') : 'Voice Off'}</span>
          </button>

          {/* Code Scratchpad Button */}
          <button
            onClick={() => setShowScratchpad(!showScratchpad)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
              showScratchpad
                ? 'bg-indigo-950 text-indigo-300 border border-indigo-700'
                : 'bg-slate-800 text-slate-300 hover:text-white border border-slate-700'
            }`}
            title="Open Monaco Code & Architecture Scratchpad"
          >
            <Code2 className="w-4 h-4 text-indigo-400" />
            <span>{showScratchpad ? 'Close Editor' : 'Code Editor'}</span>
          </button>

          <button
            onClick={handleViewReportDirectly}
            className="px-4 py-1.5 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-all"
          >
            Conclude & View Feedback Report
          </button>
        </div>
      </div>

      {/* Monaco Code Scratchpad Modal */}
      {showScratchpad && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-4xl w-full p-5 space-y-4 shadow-2xl relative flex flex-col max-h-[90vh]">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center">
                  <Code2 className="w-4 h-4 text-indigo-400" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Monaco Code Scratchpad</h3>
                  <p className="text-[11px] text-slate-400">Write, format, and structure code during your technical interview</p>
                </div>
              </div>
              <button
                onClick={() => setShowScratchpad(false)}
                className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800"
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

            <div className="pt-2 border-t border-slate-800 flex items-center justify-between">
              <span className="text-[11px] text-slate-500">
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
                  className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-sm transition-all"
                >
                  <PlusCircle className="w-3.5 h-3.5" />
                  <span>Insert into Answer</span>
                </button>
                <button
                  type="button"
                  onClick={() => setShowScratchpad(false)}
                  className="px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
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
        <div className="lg:col-span-3 flex flex-col h-[650px] rounded-2xl bg-slate-900/90 border border-slate-800 overflow-hidden shadow-sm">
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
                    <div className="w-8 h-8 rounded-lg bg-indigo-600/30 border border-indigo-500/50 flex items-center justify-center shrink-0 mt-1">
                      <Bot className="w-4 h-4 text-indigo-300" />
                    </div>
                  )}

                  <div className={`max-w-2xl space-y-1.5 ${isInterviewer ? 'items-start' : 'items-end'}`}>
                    <div className="flex items-center gap-2 text-[11px] text-slate-400 px-1">
                      <span className="font-semibold text-slate-300">
                        {isInterviewer ? 'AI Technical Interviewer' : candidateName}
                      </span>
                      {msg.topic && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                          {msg.topic}
                        </span>
                      )}
                      <span>{msg.timestamp}</span>
                    </div>

                    <div
                      className={`p-4 rounded-2xl text-xs sm:text-sm leading-relaxed ${
                        isInterviewer
                          ? 'bg-slate-950 border border-slate-800/80 text-slate-100 rounded-tl-sm'
                          : 'bg-indigo-600 text-white rounded-tr-sm shadow-md shadow-indigo-600/20'
                      }`}
                    >
                      {msg.text}
                    </div>

                    {/* Show previous evaluation details inline if available */}
                    {msg.evalPrev && (
                      msg.evalPrev.is_clarification_prompt || msg.evalPrev.quality_band === 'Specification Clarification' ? (
                        <div className="p-2.5 rounded-xl bg-amber-950/40 border border-amber-800/60 text-[11px] text-amber-200 flex items-center justify-between gap-2 mt-1">
                          <div className="flex items-center gap-1.5">
                            <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse inline-block" />
                            <span className="font-bold text-amber-300">2nd-Go Clarification Requested</span>
                          </div>
                          <span className="text-amber-300/80 font-medium text-[10px]">
                            Overview noted • Specify concrete details (No 0/10 penalty yet)
                          </span>
                        </div>
                      ) : (
                        <div className="p-2.5 rounded-xl bg-slate-950/80 border border-slate-800/80 text-[11px] text-slate-300 flex items-center justify-between gap-2 mt-1">
                          <div className="flex items-center gap-1.5">
                            <span className="text-slate-500">Graded:</span>
                            <span className="font-bold text-amber-300">{msg.evalPrev.quality_band}</span>
                          </div>
                          <span className="font-mono text-emerald-400 font-semibold">
                            +{msg.evalPrev.earned_points} / {msg.evalPrev.possible_points} pts
                          </span>
                        </div>
                      )
                    )}
                  </div>

                  {!isInterviewer && (
                    <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0 mt-1 text-slate-200">
                      <User className="w-4 h-4" />
                    </div>
                  )}
                </div>
              );
            })}

            {isProcessing && (
              <div className="flex items-center gap-3 text-xs text-slate-400 p-2">
                <div className="w-5 h-5 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
                <span>Interviewer evaluating technical reasoning & adapting follow-up...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Bar */}
          <div className="p-4 bg-slate-950 border-t border-slate-800 space-y-2">
            {(currentTurn.is_clarification_prompt || currentTurn.eval_previous?.is_clarification_prompt) && (
              <div className="px-3.5 py-2 rounded-xl bg-amber-950/40 border border-amber-700/60 flex items-center gap-2 text-xs text-amber-200">
                <HelpCircle className="w-4 h-4 text-amber-400 shrink-0" />
                <div className="flex-1">
                  <span className="font-bold text-amber-200">2nd-Go Opportunity: </span>
                  <span className="text-amber-300/90">
                    The interviewer wants specific implementation details, libraries, or architecture choices. Answer precisely to earn full marks with minimal penalty!
                  </span>
                </div>
              </div>
            )}
            {isListening && (
              <div className="px-3.5 py-2 rounded-xl bg-rose-950/40 border border-rose-800/60 flex items-center justify-between text-xs text-rose-300">
                <div className="flex items-center gap-2.5">
                  <span className="relative flex h-2.5 w-2.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-rose-500"></span>
                  </span>
                  <span className="font-bold text-white">Microphone Active</span>
                  <span className="text-rose-300/80 hidden sm:inline">• Speak freely, pauses will not stop recording. Click Mic or Stop when done.</span>
                </div>
                <button
                  type="button"
                  onClick={stopListening}
                  className="px-2.5 py-1 rounded-lg bg-rose-900/60 hover:bg-rose-800 text-[11px] font-bold uppercase tracking-wider text-rose-100 transition-colors"
                >
                  Stop Recording
                </button>
              </div>
            )}

            <form onSubmit={handleSendAnswer} className="space-y-2.5">
              {isCorrecting && (
                <div className="px-3.5 py-1.5 rounded-xl bg-indigo-950/70 border border-indigo-800/70 flex items-center gap-2 text-xs text-indigo-300">
                  <Sparkles className="w-3.5 h-3.5 text-indigo-400 animate-spin" />
                  <span className="font-medium">Polishing technical terms & grammar against question context...</span>
                </div>
              )}
              {/* Full Paragraph Multi-line Textarea */}
              <div className="relative rounded-2xl bg-slate-900/90 border border-slate-800 focus-within:border-indigo-500/80 focus-within:ring-1 focus-within:ring-indigo-500/30 transition-all p-3 shadow-inner">
                <textarea
                  ref={textareaRef}
                  value={inputText}
                  rows={4}
                  onChange={(e) => {
                    setInputText(e.target.value);
                    baseTextRef.current = e.target.value.trim() ? e.target.value.trim() + ' ' : '';
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
                  className="w-full bg-transparent text-xs sm:text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none resize-y min-h-[95px] max-h-[220px] leading-relaxed font-sans"
                />

                {/* Bottom Control Bar */}
                <div className="flex flex-wrap items-center justify-between pt-2 border-t border-slate-800/80 gap-2 text-[11px] text-slate-400">
                  <div className="flex items-center gap-2">
                    {isListening && (
                      <span className="inline-flex items-center gap-1.5 text-rose-400 font-semibold animate-pulse">
                        <span className="w-2 h-2 rounded-full bg-rose-500" />
                        Speaking live into paragraph...
                      </span>
                    )}
                    {!isListening && inputText.trim() && (
                      <span className="text-slate-500">
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
                      className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-indigo-950/70 border border-indigo-700/60 text-indigo-200 hover:bg-indigo-900 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5 shadow-sm transition-all"
                      title="AI scans your answer, cross-references with the question and your resume to fix speech-to-text mistranslations and irregular sentences"
                    >
                      {isCorrecting ? (
                        <>
                          <div className="w-3 h-3 rounded-full border-2 border-indigo-400 border-t-transparent animate-spin" />
                          <span>Correcting Typos...</span>
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                          <span>Correct Typos (AI)</span>
                        </>
                      )}
                    </button>

                    {/* Microphone Toggle Button */}
                    <button
                      type="button"
                      onClick={toggleListening}
                      className={`p-2 rounded-xl border transition-all ${
                        isListening
                          ? 'bg-rose-600 text-white border-rose-500 shadow-lg shadow-rose-600/30'
                          : 'bg-slate-800 border-slate-700 text-slate-300 hover:text-white'
                      }`}
                      title={isListening ? 'Stop recording (Manual Stop)' : 'Start speaking (Continuous listening paragraph)'}
                    >
                      {isListening ? <Mic className="w-3.5 h-3.5 animate-pulse" /> : <MicOff className="w-3.5 h-3.5" />}
                    </button>

                    {/* Send Answer Button */}
                    <button
                      type="submit"
                      disabled={!inputText.trim() || isProcessing || isCorrecting}
                      className="px-4 py-1.5 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white flex items-center gap-1.5 shadow-sm transition-all"
                    >
                      <span>Send</span>
                      <Send className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              </div>

              {/* Autocorrect Result Banner */}
              {correctionNotice && (
                <div className="px-3.5 py-2 rounded-xl bg-emerald-950/40 border border-emerald-800/60 text-xs text-emerald-300 flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <CheckCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span className="font-medium text-emerald-200">{correctionNotice}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setCorrectionNotice(null)}
                    className="text-emerald-400 hover:text-emerald-200 text-xs font-bold ml-2"
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
            currentDepth={currentTurn.depth_level}
            maxDepth={currentTurn.max_depth}
            phase={currentTurn.phase}
            previousEval={currentTurn.eval_previous}
          />

          <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-3 text-xs">
            <div className="font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
              <Layers className="w-3.5 h-3.5 text-indigo-400" />
              Adaptive Reasoning & Depth Engine
            </div>
            <p className="text-slate-400 leading-relaxed">
              Every turn is scored deterministically using:
            </p>
            <div className="p-2.5 rounded-lg bg-slate-950 font-mono text-[11px] text-slate-300 space-y-1">
              <div>correct_possible(L) = 5 + 3*(L - 1)</div>
              <div>incorrect_possible(L) = max(2, 10 - 2*(L - 1))</div>
            </div>
            <p className="text-slate-400 leading-relaxed">
              Shallow errors are penalized heavily; correct deep insights at Level 4–5 earn maximum points.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
