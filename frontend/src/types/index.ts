export interface User {
  id: string;
  name: string;
  email: string;
  created_at: string;
}

export interface TopicDetail {
  topic: string;
  subtopics: string[];
  importance_score: number;
  expected_question_types: string[];
  expected_difficulty_distribution: {
    easy: number;
    medium: number;
    hard: number;
  };
}

export interface SubjectDetail {
  subject: string;
  topics: TopicDetail[];
}

export interface EvidenceFact {
  fact: string;
  source: string;
  trust_level: string;
  timestamp: string;
}

export interface RoleTopicProfile {
  id: string;
  company: string;
  role: string;
  job_type: string;
  experience_requirement: string;
  required_skills: string[];
  time_window_id?: string;
  subjects: SubjectDetail[];
  evidence: EvidenceFact[];
  created_at: string;
  refreshed_at: string;
}

export interface TestCase {
  input: any;
  expected_output: string;
  is_hidden?: boolean;
}

export interface Question {
  id: string;
  subject: string;
  topic: string;
  subtopic: string;
  question_type: string;
  difficulty: 'easy' | 'medium' | 'hard';
  title?: string;
  prompt: string;
  options?: string[];
  starter_code?: string;
  test_cases?: TestCase[];
}

export interface TestCaseResult {
  test_case_index: number;
  input_data: string;
  expected_output: string;
  actual_output?: string;
  passed: boolean;
  runtime_ms?: number;
  memory_mb?: number;
}

export interface CheckAnswerResponse {
  question_id: string;
  is_correct: boolean;
  score_fraction: number;
  feedback: string;
  test_case_results?: TestCaseResult[];
  optimal_complexity?: string;
}

export interface PracticeSession {
  id: string;
  practice_generation_key: string;
  company: string;
  role: string;
  selected_topics: string[];
  total_questions: number;
  allocation_mode: string;
  questions: Question[];
}

export interface MockOAVariant {
  id: string;
  company: string;
  role: string;
  time_window_id: string;
  attempt_number: number;
  user_attempt_count: number;
  duration_minutes: number;
  window_expires_in_days: number;
  questions: Question[];
  mock_oa_attempt_id: string;
}

export interface MockOAReport {
  attempt_id: string;
  company: string;
  role: string;
  attempt_number: number;
  total_score: number;
  max_possible_score: number;
  percentage: number;
  accuracy_by_topic: Record<string, {
    earned: number;
    possible: number;
    accuracy_percentage: number;
    questions_count: number;
  }>;
  strong_topics: string[];
  weak_topics: string[];
  time_spent_seconds: number;
  questions_review: {
    question_id: string;
    title: string;
    subject: string;
    topic: string;
    difficulty: string;
    question_type: string;
    prompt: string;
    user_answer: any;
    correct_answer: any;
    approach?: string;
    score: number;
    is_correct: boolean;
    feedback: string;
    test_case_results?: TestCaseResult[];
    time_spent_seconds: number;
  }[];
  submitted_at: string;
  proctoring_summary?: ProctoringSummary;
}

export interface ProctoringIncident {
  type: 'TAB_SWITCH' | 'WINDOW_BLUR' | 'PASTE_BURST' | 'FULLSCREEN_EXIT';
  timestamp: string;
  detail: string;
  duration_seconds?: number;
}

export interface ProctoringSummary {
  integrity_score: number;
  integrity_status: 'HIGH_INTEGRITY' | 'MODERATE_CONCERN' | 'FLAGGED_FOR_REVIEW';
  tab_switch_count: number;
  window_blur_count: number;
  paste_burst_count: number;
  fullscreen_exits: number;
  total_time_away_seconds: number;
  focus_percentage: number;
  incidents: ProctoringIncident[];
}

export interface ProjectRelevance {
  project_id: string;
  title: string;
  description: string;
  technologies: string[];
  overall_relevance: number;
  questioning_priority: number;
  relevant_topics: string[];
  irrelevant_topics: string[];
}

export interface StructuredResume {
  id: string;
  candidate_name: string;
  candidate_email?: string;
  work_experience: any[];
  projects: ProjectRelevance[];
  skills: string[];
  education: any[];
  section_weights: Record<string, number>;
}

export interface InterviewTurn {
  session_id: string;
  phase: string;
  current_topic: string;
  question_id: string;
  question_text: string;
  depth_level: number;
  max_depth: number;
  is_completed: boolean;
  is_clarification_prompt?: boolean;
  eval_previous?: {
    quality_band: string;
    earned_points: number;
    possible_points: number;
    severity: string;
    feedback: string;
    detected_gap?: string;
    is_clarification_prompt?: boolean;
  };
}

export interface InterviewEvidenceRecord {
  id: string;
  project_id_or_topic: string;
  question_id: string;
  follow_up_index: number;
  topic: string;
  subtopic: string;
  user_answer: string;
  expected_concept: string;
  detected_gap?: string;
  severity: string;
  earned_points: number;
  possible_points: number;
  evaluator_reason: string;
  evidence_ref?: string;
}

export interface ProjectScoreCard {
  project_id: string;
  title: string;
  score: number;
  star_rating: number;
  relevance_weight: number;
  strengths: string[];
  identified_gaps: string[];
  topics_covered: string[];
}

export interface InterviewFinalReport {
  session_id: string;
  company: string;
  role: string;
  candidate_name: string;
  resume_related_score: number;
  subject_knowledge_score: number;
  section_scores: Record<string, number>;
  project_cards: ProjectScoreCard[];
  subject_topic_breakdown: Record<string, string>;
  evidence_trail: InterviewEvidenceRecord[];
  strengths: string[];
  weaknesses: string[];
  improvement_recommendations: string[];
  completed_at: string;
}

export interface ReviewQueueItem {
  id: string;
  subject: string;
  topic: string;
  subtopic: string;
  question_type: string;
  difficulty: string;
  title?: string;
  prompt: string;
  status: string;
  review_report: {
    all_passed: boolean;
    checklist: Record<string, boolean>;
    passed_checks_count: number;
    total_checks: number;
    notes: string[];
  };
  created_at: string;
}
