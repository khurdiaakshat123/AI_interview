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

export const api = {
  // Role Profiles
  async getRoleProfiles(): Promise<RoleTopicProfile[]> {
    const res = await fetch(`${BASE_URL}/role-profiles`);
    return handleResponse<RoleTopicProfile[]>(res);
  },

  async createRoleProfile(payload: {
    company: string;
    role: string;
    job_type?: string;
    experience_requirement?: string;
    jd_text?: string;
  }): Promise<RoleTopicProfile> {
    const res = await fetch(`${BASE_URL}/role-profiles`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return handleResponse<RoleTopicProfile>(res);
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
    const res = await fetch(`${BASE_URL}/practice/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return handleResponse<PracticeSession>(res);
  },

  async checkAnswer(questionId: string, answer: any): Promise<CheckAnswerResponse> {
    const res = await fetch(`${BASE_URL}/practice/questions/${questionId}/check-answer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question_id: questionId, answer })
    });
    return handleResponse<CheckAnswerResponse>(res);
  },

  async getHint(questionId: string): Promise<{ question_id: string; hint: string }> {
    const res = await fetch(`${BASE_URL}/practice/questions/${questionId}/hint`);
    return handleResponse(res);
  },

  async getApproach(questionId: string): Promise<{ question_id: string; approach: string }> {
    const res = await fetch(`${BASE_URL}/practice/questions/${questionId}/approach`);
    return handleResponse(res);
  },

  async getSolution(questionId: string): Promise<{ question_id: string; solution: string; explanation?: string }> {
    const res = await fetch(`${BASE_URL}/practice/questions/${questionId}/solution`);
    return handleResponse(res);
  },

  // Mock OA
  async startMockOA(payload: { company: string; role: string }): Promise<MockOAVariant> {
    const res = await fetch(`${BASE_URL}/mock-oa/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return handleResponse<MockOAVariant>(res);
  },

  async submitMockOA(attemptId: string, payload: {
    answers: Record<string, any>;
    time_spent_per_question?: Record<string, number>;
  }): Promise<MockOAReport> {
    const res = await fetch(`${BASE_URL}/mock-oa/attempts/${attemptId}/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return handleResponse<MockOAReport>(res);
  },

  async getMockOAReport(attemptId: string): Promise<MockOAReport> {
    const res = await fetch(`${BASE_URL}/mock-oa/attempts/${attemptId}/report`);
    return handleResponse<MockOAReport>(res);
  },

  // Interview
  async parseResume(payload: {
    candidate_name: string;
    candidate_email?: string;
    resume_text: string;
    company: string;
    role: string;
  }): Promise<StructuredResume> {
    const res = await fetch(`${BASE_URL}/interview/parse-resume`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return handleResponse<StructuredResume>(res);
  },

  async getSampleResume(): Promise<StructuredResume> {
    const res = await fetch(`${BASE_URL}/interview/resumes/sample`);
    return handleResponse<StructuredResume>(res);
  },

  async startInterview(payload: {
    company: string;
    role: string;
    resume_id?: string;
    candidate_name?: string;
    resume_text?: string;
  }): Promise<InterviewTurn> {
    const res = await fetch(`${BASE_URL}/interview/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return handleResponse<InterviewTurn>(res);
  },

  async answerInterviewQuestion(sessionId: string, answer: string): Promise<InterviewTurn> {
    const res = await fetch(`${BASE_URL}/interview/sessions/${sessionId}/answer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ answer })
    });
    return handleResponse<InterviewTurn>(res);
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
    const res = await fetch(`${BASE_URL}/interview/sessions/${sessionId}/correct-transcript`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return handleResponse(res);
  },

  async getInterviewReport(sessionId: string): Promise<InterviewFinalReport> {
    const res = await fetch(`${BASE_URL}/interview/sessions/${sessionId}/report`);
    return handleResponse<InterviewFinalReport>(res);
  },

  // Admin
  async getReviewQueue(): Promise<ReviewQueueItem[]> {
    const res = await fetch(`${BASE_URL}/admin/review-queue`);
    return handleResponse<ReviewQueueItem[]>(res);
  },

  async approveQuestion(questionId: string): Promise<{ message: string }> {
    const res = await fetch(`${BASE_URL}/admin/review-queue/${questionId}/approve`, {
      method: 'POST'
    });
    return handleResponse(res);
  },

  async rejectQuestion(questionId: string): Promise<{ message: string }> {
    const res = await fetch(`${BASE_URL}/admin/review-queue/${questionId}/reject`, {
      method: 'POST'
    });
    return handleResponse(res);
  },

  // Auth & Google Login
  async loginWithGoogle(credential: string, userInfo?: any): Promise<{ access_token: string; user: any }> {
    const res = await fetch(`${BASE_URL}/auth/google`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ credential, user_info: userInfo })
    });
    return handleResponse(res);
  },

  async login(email: string, password: string): Promise<{ access_token: string; user: any }> {
    const res = await fetch(`${BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    return handleResponse(res);
  },

  async signup(name: string, email: string, password: string): Promise<{ access_token: string; user: any }> {
    const res = await fetch(`${BASE_URL}/auth/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password })
    });
    return handleResponse(res);
  },

  async getMe(token?: string): Promise<any> {
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const res = await fetch(`${BASE_URL}/auth/me`, { headers });
    return handleResponse(res);
  }
};

export { BASE_URL };

