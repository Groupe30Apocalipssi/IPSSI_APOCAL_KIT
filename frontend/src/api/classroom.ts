/**
 * Appels API de l'espace enseignant (classroom) : classes, roster, documents,
 * génération/relecture/publication de quiz, statistiques de classe.
 */
import { api } from './client';

export type Classe = {
  id: number;
  name: string;
  code: string;
  created_at: string;
  students_count: number;
};

export type CourseDocument = {
  id: number;
  original_name: string;
  size_bytes: number;
  uploaded_at: string;
  file: string;
};

export type TemplateQuestion = {
  index: number;
  prompt: string;
  options: string[];
  correct_index: number;
};

export type TemplateQuiz = {
  id: number;
  title: string;
  status: 'draft' | 'published';
  created_at: string;
  questions: TemplateQuestion[];
};

export type RosterStudent = {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  joined_at: string;
  quizzes_assigned: number;
  quizzes_taken: number;
  average_score: number | null;
};

export type StudentDetail = {
  student: { id: number; email: string; first_name: string; last_name: string };
  average_score: number | null;
  quizzes: {
    quiz_id: number;
    template_id: number | null;
    title: string;
    score: number | null;
    created_at: string;
  }[];
};

export type AtRiskStudent = {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  average_score: number | null;
  quizzes_taken: number;
  reason: string;
};

export type QuizStats = {
  quiz_id: number;
  title: string;
  assigned: number;
  taken: number;
  average_score: number | null;
  per_question: {
    index: number;
    prompt: string;
    answered: number;
    correct: number;
    success_rate: number | null;
  }[];
  results: { student_id: number; student_email: string; score: number | null }[];
};

// --- Classes -----------------------------------------------------------

export async function listClasses(): Promise<Classe[]> {
  const { data } = await api.get<Classe[]>('/classroom/classes/');
  return data;
}

export async function createClass(name: string): Promise<Classe> {
  const { data } = await api.post<Classe>('/classroom/classes/', { name });
  return data;
}

export async function getClass(id: number): Promise<Classe> {
  const { data } = await api.get<Classe>(`/classroom/classes/${id}/`);
  return data;
}

export async function joinClass(code: string): Promise<Classe> {
  const { data } = await api.post<Classe>('/classroom/join/', { code });
  return data;
}

// --- Roster / scores / difficulté --------------------------------------

export async function getRoster(classId: number): Promise<{ count: number; students: RosterStudent[] }> {
  const { data } = await api.get(`/classroom/classes/${classId}/students/`);
  return data;
}

export async function getStudentDetail(classId: number, studentId: number): Promise<StudentDetail> {
  const { data } = await api.get<StudentDetail>(`/classroom/classes/${classId}/students/${studentId}/`);
  return data;
}

export async function getAtRiskStudents(
  classId: number,
  threshold = 5,
): Promise<{ threshold: number; count: number; students: AtRiskStudent[] }> {
  const { data } = await api.get(`/classroom/classes/${classId}/at-risk/`, { params: { threshold } });
  return data;
}

// --- Documents -----------------------------------------------------------

export async function listDocuments(classId: number): Promise<CourseDocument[]> {
  const { data } = await api.get<CourseDocument[]>(`/classroom/classes/${classId}/documents/`);
  return data;
}

export async function uploadDocument(classId: number, file: File): Promise<CourseDocument> {
  const form = new FormData();
  form.append('file', file);
  const { data } = await api.post<CourseDocument>(`/classroom/classes/${classId}/documents/`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

// --- Quiz de classe ------------------------------------------------------

export async function listClassQuizzes(classId: number): Promise<TemplateQuiz[]> {
  const { data } = await api.get<TemplateQuiz[]>(`/classroom/classes/${classId}/quizzes/`);
  return data;
}

export async function generateClassQuiz(
  classId: number,
  input: { title: string; pdf?: File; source_text?: string },
): Promise<TemplateQuiz> {
  const form = new FormData();
  form.append('title', input.title);
  if (input.pdf) form.append('pdf', input.pdf);
  if (input.source_text) form.append('source_text', input.source_text);
  const { data } = await api.post<TemplateQuiz>(`/classroom/classes/${classId}/quizzes/generate/`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 600_000,
  });
  return data;
}

export async function getClassQuiz(classId: number, quizId: number): Promise<TemplateQuiz> {
  const { data } = await api.get<TemplateQuiz>(`/classroom/classes/${classId}/quizzes/${quizId}/`);
  return data;
}

export async function updateClassQuizQuestion(
  classId: number,
  quizId: number,
  index: number,
  patch: { prompt?: string; options?: string[]; correct_index?: number },
): Promise<TemplateQuiz> {
  const { data } = await api.patch<TemplateQuiz>(
    `/classroom/classes/${classId}/quizzes/${quizId}/questions/${index}/`,
    patch,
  );
  return data;
}

export async function publishClassQuiz(classId: number, quizId: number): Promise<TemplateQuiz> {
  const { data } = await api.post<TemplateQuiz>(`/classroom/classes/${classId}/quizzes/${quizId}/publish/`);
  return data;
}

export async function getClassQuizStats(classId: number, quizId: number): Promise<QuizStats> {
  const { data } = await api.get<QuizStats>(`/classroom/classes/${classId}/quizzes/${quizId}/stats/`);
  return data;
}
