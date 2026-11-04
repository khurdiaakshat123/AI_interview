import {
  RoleTopicProfile, PracticeSession, CheckAnswerResponse,
  MockOAVariant, MockOAReport, StructuredResume,
  InterviewTurn, InterviewFinalReport, ReviewQueueItem,
  LCQuestionSummary, LCQuestionDetail, LCSubmission, LCAnalytics, LCRunResult, LCSubmitResult,
  DebugTraceResult,
  MCQBroadTopic, MCQQuestionSummary, MCQQuestionDetail, MCQSubmitResult, MCQAnalytics, MCQQuiz, MCQQuizSubmitResult
} from '../types';

const LIVE_RENDER_API = 'https://ai-interview-4bio.onrender.com/api';

const rawEnvBase = (import.meta as any).env?.VITE_API_BASE_URL;
const isValidEnvBase = typeof rawEnvBase === 'string' &&
  rawEnvBase.trim() !== '' &&
  !rawEnvBase.includes('[SENSITIVE]') &&
  !rawEnvBase.includes('undefined') &&
  (rawEnvBase.startsWith('http://') || rawEnvBase.startsWith('https://') || rawEnvBase.startsWith('/'));

const isLocalhost = typeof window !== 'undefined' && 
  (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.hostname === '0.0.0.0');

const BASE_URL = isValidEnvBase
  ? (rawEnvBase.trim().replace(/\/$/, '').endsWith('/api')
      ? rawEnvBase.trim().replace(/\/$/, '')
      : `${rawEnvBase.trim().replace(/\/$/, '')}/api`)
  : (isLocalhost
      ? 'http://127.0.0.1:8000/api'
      : '/api');

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(errorText || `Request failed with status ${res.status}`);
  }
  const text = await res.text();
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error(`Server returned non-JSON response (${res.status}). Verify API proxy or backend server status.`);
  }
}

export function getAuthToken(): string {
  if (typeof window === 'undefined') return '';

  // Clean up any stale or oversized (> 255 chars) token
  let token = localStorage.getItem('intervyn_token');
  if (token && (token.startsWith('guest_anon_') || token.length > 255)) {
    try {
      localStorage.removeItem('intervyn_token');
    } catch {}
    token = null;
  }
  if (token) return token;

  let guestId = localStorage.getItem('intervyn_guest_id');
  // Auto-heal: Purge any legacy, corrupted, or oversized (> 36 chars) guest ID
  if (!guestId || guestId.length > 36 || guestId.startsWith('guest_anon_')) {
    // Generate clean 24-character guest ID: 'g_' + 10 chars + timestamp
    guestId = 'g_' + Math.random().toString(36).substring(2, 12) + Date.now().toString(36);
    try {
      localStorage.setItem('intervyn_guest_id', guestId);
    } catch {}
  }
  return guestId;
}

export function getAuthHeaders(customHeaders?: HeadersInit): Headers {
  const headers = new Headers(customHeaders || {});
  if (typeof window !== 'undefined') {
    const token = getAuthToken();
    if (token && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${token}`);
    }
  }
  return headers;
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = getAuthHeaders(options.headers);
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  const primaryUrl = endpoint.startsWith('http') ? endpoint : `${BASE_URL}${endpoint}`;
  try {
    const res = await fetch(primaryUrl, {
      ...options,
      headers
    });
    return await handleResponse<T>(res);
  } catch (primaryErr: any) {
    // If primary failed (network error, connection refused, or non-JSON/HTML 200 response),
    // and it wasn't already calling the direct live Render backend:
    const isDirectRender = primaryUrl.startsWith(LIVE_RENDER_API);
    if (!isDirectRender && !endpoint.startsWith('http')) {
      const fallbackUrl = `${LIVE_RENDER_API}${endpoint}`;
      try {
        console.warn(`Primary API call to ${primaryUrl} failed (${primaryErr?.message}). Retrying with live Render backend: ${fallbackUrl}`);
        const fallbackRes = await fetch(fallbackUrl, {
          ...options,
          headers
        });
        return await handleResponse<T>(fallbackRes);
      } catch (fallbackErr: any) {
        throw new Error(primaryErr?.message || (fallbackErr as any)?.message || 'Failed to connect to backend server');
      }
    }
    throw primaryErr;
  }
}

export const api = {
  // Role Profiles
  async getRoleProfiles(): Promise<RoleTopicProfile[]> {
    return request<RoleTopicProfile[]>('/role-profiles');
  },

  async createRoleProfile(payload: {
    company: string;
    role: string;
    job_type?: string;
    experience_requirement?: string;
    jd_text?: string;
  }): Promise<RoleTopicProfile> {
    return request<RoleTopicProfile>('/role-profiles', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },

  // Practice
  async createPracticeSession(payload: {
    company: string;
    role: string;
    selected_topics: string[];
    proficiency_vector?: Record<string, string>;
    total_questions?: number;
    allocation_mode?: string;
  }): Promise<PracticeSession> {
    return request<PracticeSession>('/practice/sessions', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },

  async checkAnswer(questionId: string, answer: any): Promise<CheckAnswerResponse> {
    return request<CheckAnswerResponse>(`/practice/questions/${questionId}/check-answer`, {
      method: 'POST',
      body: JSON.stringify({ question_id: questionId, answer })
    });
  },

  async getHint(questionId: string): Promise<{ question_id: string; hint: string }> {
    return request<{ question_id: string; hint: string }>(`/practice/questions/${questionId}/hint`);
  },

  async getApproach(questionId: string): Promise<{ question_id: string; approach: string }> {
    return request<{ question_id: string; approach: string }>(`/practice/questions/${questionId}/approach`);
  },

  async getSolution(questionId: string): Promise<{ question_id: string; solution: string; explanation?: string }> {
    return request<{ question_id: string; solution: string; explanation?: string }>(`/practice/questions/${questionId}/solution`);
  },

  // Mock OA
  async startMockOA(payload: { company: string; role: string }): Promise<MockOAVariant> {
    return request<MockOAVariant>('/mock-oa/start', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },

  async submitMockOA(attemptId: string, payload: {
    answers: Record<string, any>;
    time_spent_per_question?: Record<string, number>;
    proctoring_data?: any;
  }): Promise<MockOAReport> {
    return request<MockOAReport>(`/mock-oa/attempts/${attemptId}/submit`, {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },

  async getMockOAReport(attemptId: string): Promise<MockOAReport> {
    return request<MockOAReport>(`/mock-oa/attempts/${attemptId}/report`);
  },

  async getMockOAAttempts(): Promise<Array<{
    id: string;
    company: string;
    role: string;
    attempt_number: number;
    score: number;
    time_spent_seconds: number;
    correct_count: number;
    total_questions: number;
    started_at: string;
    submitted_at?: string;
    is_submitted: boolean;
  }>> {
    return request('/mock-oa/attempts');
  },

  async runCode(payload: {
    question_id: string;
    code: string;
    language: string;
    custom_input?: string;
  }): Promise<{
    status: 'ACCEPTED' | 'WRONG_ANSWER' | 'COMPILATION_ERROR' | 'RUNTIME_ERROR' | 'TLE';
    runtime_ms: number;
    memory_mb: number;
    test_case_results: Array<{
      test_case_index: number;
      input_data: string;
      expected_output: string;
      actual_output: string;
      passed: boolean;
      runtime_ms: number;
      memory_mb: number;
    }>;
    compiler_output?: string;
    feedback?: string;
  }> {
    return request('/mock-oa/run', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },

  // Interview
  async parseResume(payload: {
    candidate_name: string;
    candidate_email?: string;
    resume_text: string;
    company: string;
    role: string;
  }): Promise<StructuredResume> {
    return request<StructuredResume>('/interview/parse-resume', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },

  async getSampleResume(): Promise<StructuredResume> {
    return request<StructuredResume>('/interview/resumes/sample');
  },

  async startInterview(payload: {
    company: string;
    role: string;
    resume_id?: string;
    candidate_name?: string;
    resume_text?: string;
  }): Promise<InterviewTurn> {
    return request<InterviewTurn>('/interview/sessions', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },

  async answerInterviewQuestion(sessionId: string, answer: string): Promise<InterviewTurn> {
    return request<InterviewTurn>(`/interview/sessions/${sessionId}/answer`, {
      method: 'POST',
      body: JSON.stringify({ answer })
    });
  },

  async streamAnswerInterviewQuestion(
    sessionId: string,
    answer: string,
    onSentence: (text: string, index: number) => void,
    onTurn: (turn: InterviewTurn) => void,
    onError: (err: any) => void
  ): Promise<void> {
    try {
      const headers = getAuthHeaders({ 'Content-Type': 'application/json' });
      const res = await fetch(`${BASE_URL}/interview/sessions/${sessionId}/answer-stream`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ answer })
      });

      if (!res.ok || !res.body) {
        // Fallback to synchronous endpoint
        const fallbackTurn = await api.answerInterviewQuestion(sessionId, answer);
        onTurn(fallbackTurn);
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('data: ')) {
            try {
              const data = JSON.parse(trimmed.slice(6));
              if (data.type === 'sentence' && data.text) {
                onSentence(data.text, data.index);
              } else if (data.type === 'turn' && data.payload) {
                onTurn(data.payload as InterviewTurn);
              } else if (data.type === 'error') {
                onError(new Error(data.message));
                return;
              }
            } catch (jsonErr) {
              console.warn('[SSE] JSON parse warning:', jsonErr);
            }
          }
        }
      }
    } catch (err) {
      console.warn('[SSE Stream] Stream error, falling back to sync:', err);
      try {
        const fallbackTurn = await api.answerInterviewQuestion(sessionId, answer);
        onTurn(fallbackTurn);
      } catch (fallbackErr) {
        onError(fallbackErr);
      }
    }
  },

  async correctTranscript(sessionId: string, payload: {
    raw_text: string;
    question_text?: string;
    topic?: string;
  }): Promise<{
    corrected_text: string;
    original_text: string;
    changes_made: string[];
    has_corrections: boolean;
  }> {
    return request(`/interview/sessions/${sessionId}/correct-transcript`, {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },

  async getInterviewReport(sessionId: string): Promise<InterviewFinalReport> {
    return request<InterviewFinalReport>(`/interview/sessions/${sessionId}/report`);
  },

  async getPastInterviews(): Promise<Array<{
    id: string;
    company: string;
    role: string;
    candidate_name: string;
    status: string;
    current_phase: string;
    turn_count: number;
    created_at: string;
    completed_at?: string;
    score?: number;
    has_report: boolean;
  }>> {
    return request('/interview/sessions');
  },

  async getInterviewTranscript(sessionId: string): Promise<{
    id: string;
    company: string;
    role: string;
    candidate_name: string;
    created_at: string;
    completed_at?: string;
    status: string;
    current_phase?: string;
    current_depth?: number;
    transcript: Array<{
      turn_index: number;
      sender: 'INTERVIEWER' | 'CANDIDATE';
      text: string;
      topic?: string;
      subtopic?: string;
      depth_level?: number;
      timestamp?: string;
    }>;
    final_report: any;
  }> {
    return request(`/interview/sessions/${sessionId}/transcript`);
  },

  // Admin
  async getReviewQueue(): Promise<ReviewQueueItem[]> {
    return request<ReviewQueueItem[]>('/admin/review-queue');
  },

  async approveQuestion(questionId: string): Promise<{ message: string }> {
    return request<{ message: string }>(`/admin/review-queue/${questionId}/approve`, {
      method: 'POST'
    });
  },

  async rejectQuestion(questionId: string): Promise<{ message: string }> {
    return request<{ message: string }>(`/admin/review-queue/${questionId}/reject`, {
      method: 'POST'
    });
  },

  // Auth & Google Login
  async loginWithGoogle(credential: string, userInfo?: any): Promise<{ access_token: string; user: any }> {
    return request<{ access_token: string; user: any }>('/auth/google', {
      method: 'POST',
      body: JSON.stringify({ credential, user_info: userInfo })
    });
  },

  async login(email: string, password: string): Promise<{ access_token: string; user: any }> {
    return request<{ access_token: string; user: any }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
  },

  async signup(name: string, email: string, password: string): Promise<{ access_token: string; user: any }> {
    return request<{ access_token: string; user: any }>('/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ name, email, password })
    });
  },

  async getMe(token?: string): Promise<any> {
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return request('/auth/me', { headers });
  },

  // LeetCode Practice Question Bank API
  async getLCQuestions(params: {
    category?: string;
    subcategory?: string;
    difficulty?: string;
    status?: string;
    search?: string;
    my_list_only?: boolean;
    page?: number;
    limit?: number;
    sort_by?: string;
    order?: string;
  } = {}): Promise<{
    total: number;
    page: number;
    limit: number;
    totalPages: number;
    questions: LCQuestionSummary[];
  }> {
    const qp = new URLSearchParams();
    if (params.category) qp.set('category', params.category);
    if (params.subcategory) qp.set('subcategory', params.subcategory);
    if (params.difficulty) qp.set('difficulty', params.difficulty);
    if (params.status) qp.set('status', params.status);
    if (params.search) qp.set('search', params.search);
    if (params.my_list_only) qp.set('my_list_only', 'true');
    if (params.page) qp.set('page', String(params.page));
    if (params.limit) qp.set('limit', String(params.limit));
    if (params.sort_by) qp.set('sort_by', params.sort_by);
    if (params.order) qp.set('order', params.order);
    return request(`/practice/lc/questions?${qp.toString()}`);
  },

  async getLCQuestion(idOrSlug: string): Promise<LCQuestionDetail> {
    return request<LCQuestionDetail>(`/practice/lc/questions/${idOrSlug}`);
  },

  async getLCAnalytics(): Promise<LCAnalytics> {
    return request<LCAnalytics>('/practice/lc/analytics');
  },

  async runLCCode(idOrSlug: string, code: string, language: string = 'python3'): Promise<LCRunResult> {
    return request<LCRunResult>(`/practice/lc/questions/${idOrSlug}/run`, {
      method: 'POST',
      body: JSON.stringify({ code, language })
    });
  },

  async submitLCCode(idOrSlug: string, code: string, language: string = 'python3'): Promise<LCSubmitResult> {
    return request<LCSubmitResult>(`/practice/lc/questions/${idOrSlug}/submit`, {
      method: 'POST',
      body: JSON.stringify({ code, language })
    });
  },

  async debugLCCode(idOrSlug: string, code: string, language: string = 'python3', customInput?: string): Promise<DebugTraceResult> {
    return request<DebugTraceResult>(`/practice/lc/questions/${idOrSlug}/debug`, {
      method: 'POST',
      body: JSON.stringify({ code, language, custom_input: customInput })
    });
  },

  async toggleLCStar(idOrSlug: string): Promise<{ question_id: string; isStarred: boolean }> {
    return request<{ question_id: string; isStarred: boolean }>(`/practice/lc/questions/${idOrSlug}/star`, {
      method: 'POST'
    });
  },

  async getLCSubmissions(idOrSlug: string): Promise<{ submissions: LCSubmission[] }> {
    return request<{ submissions: LCSubmission[] }>(`/practice/lc/questions/${idOrSlug}/submissions`);
  },

  // ==========================================
  // MCQ Question Bank API
  // ==========================================
  async getMCQTopics(): Promise<MCQBroadTopic[]> {
    return request<MCQBroadTopic[]>('/practice/mcq/topics');
  },

  async getMCQQuestions(params: {
    topic?: string;
    topics?: string;
    difficulty?: string;
    status?: string;
    search?: string;
    has_code?: boolean;
    starred_only?: boolean;
    page?: number;
    limit?: number;
    sort_by?: string;
    order?: string;
  } = {}): Promise<{
    total: number;
    page: number;
    limit: number;
    total_pages: number;
    questions: MCQQuestionSummary[];
  }> {
    const qp = new URLSearchParams();
    if (params.topic && params.topic !== 'all') qp.append('topic', params.topic);
    if (params.topics) qp.append('topics', params.topics);
    if (params.difficulty && params.difficulty !== 'all') qp.append('difficulty', params.difficulty);
    if (params.status && params.status !== 'all') qp.append('status', params.status);
    if (params.search) qp.append('search', params.search);
    if (params.has_code !== undefined) qp.append('has_code', String(params.has_code));
    if (params.starred_only) qp.append('starred_only', 'true');
    if (params.page) qp.append('page', String(params.page));
    if (params.limit) qp.append('limit', String(params.limit));
    if (params.sort_by) qp.append('sort_by', params.sort_by);
    if (params.order) qp.append('order', params.order);

    return request(`/practice/mcq/questions?${qp.toString()}`);
  },

  async getMCQQuestion(questionId: string): Promise<MCQQuestionDetail> {
    return request<MCQQuestionDetail>(`/practice/mcq/questions/${encodeURIComponent(questionId)}`);
  },

  async submitMCQAnswer(questionId: string, selectedOption: string): Promise<MCQSubmitResult> {
    return request<MCQSubmitResult>(`/practice/mcq/questions/${encodeURIComponent(questionId)}/submit`, {
      method: 'POST',
      body: JSON.stringify({ selected_option: selectedOption })
    });
  },

  async toggleMCQStar(questionId: string): Promise<{ question_id: string; is_starred: boolean }> {
    return request<{ question_id: string; is_starred: boolean }>(`/practice/mcq/questions/${encodeURIComponent(questionId)}/star`, {
      method: 'POST'
    });
  },

  async saveMCQNotes(questionId: string, notes: string): Promise<{ question_id: string; notes: string }> {
    return request<{ question_id: string; notes: string }>(`/practice/mcq/questions/${encodeURIComponent(questionId)}/notes`, {
      method: 'POST',
      body: JSON.stringify({ notes })
    });
  },

  async generateMCQQuiz(payload: {
    topics?: string[];
    difficulties?: string[];
    count?: number;
    mode?: string;
  }): Promise<MCQQuiz> {
    return request<MCQQuiz>('/practice/mcq/quiz/generate', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },

  async submitMCQQuiz(payload: {
    answers: Record<string, string | null>;
    question_ids: string[];
    time_spent_seconds: number;
  }): Promise<MCQQuizSubmitResult> {
    return request<MCQQuizSubmitResult>('/practice/mcq/quiz/submit', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },

  async getMCQAnalytics(): Promise<MCQAnalytics> {
    return request<MCQAnalytics>('/practice/mcq/analytics');
  },

  async getMCQValidation(): Promise<{
    valid: boolean;
    total_mapped_subparts: number;
    total_discovered_subparts: number;
    missing_in_mapping: string[];
    extra_in_mapping: string[];
    broad_topic_count: number;
  }> {
    return request('/practice/mcq/validation');
  }
};

export { BASE_URL };
