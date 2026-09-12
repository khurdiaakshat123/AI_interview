import {
  RoleTopicProfile, PracticeSession, CheckAnswerResponse,
  MockOAVariant, MockOAReport, StructuredResume,
  InterviewTurn, InterviewFinalReport, ReviewQueueItem
} from '../types';

const envBaseUrl = (import.meta as any).env?.VITE_API_BASE_URL;
const BASE_URL = envBaseUrl
  ? `${String(envBaseUrl).replace(/\/$/, '')}/api`
  : (typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
      ? 'http://127.0.0.1:8000/api'
      : '/api');

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(errorText || `Request failed with status ${res.status}`);
  }
  return res.json();
}

function getAuthHeaders(customHeaders?: HeadersInit): Headers {
  const headers = new Headers(customHeaders || {});
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('intervyn_token');
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
  const url = endpoint.startsWith('http') ? endpoint : `${BASE_URL}${endpoint}`;
  const res = await fetch(url, {
    ...options,
    headers
  });
  return handleResponse<T>(res);
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
  }
};

export { BASE_URL };
