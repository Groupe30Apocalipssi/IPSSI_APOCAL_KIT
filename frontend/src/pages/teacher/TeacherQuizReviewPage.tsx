/**
 * Relecture / édition / publication d'un gabarit de quiz (US-27), et une fois
 * publié, statistiques de classe (moyenne + % de réussite par question — US-28).
 */
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  getClassQuiz,
  getClassQuizStats,
  publishClassQuiz,
  updateClassQuizQuestion,
  type QuizStats,
  type TemplateQuestion,
  type TemplateQuiz,
} from '@/api/classroom';
import { getApiErrorMessage } from '@/api/errors';

function QuestionEditor({
  question,
  onSave,
  disabled,
}: {
  question: TemplateQuestion;
  onSave: (patch: { prompt: string; options: string[]; correct_index: number }) => Promise<void>;
  disabled: boolean;
}) {
  const [prompt, setPrompt] = useState(question.prompt);
  const [options, setOptions] = useState(question.options);
  const [correctIndex, setCorrectIndex] = useState(question.correct_index);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);

  const setOption = (i: number, value: string) => {
    const next = [...options];
    next[i] = value;
    setOptions(next);
    setDirty(true);
  };

  const save = async () => {
    setSaving(true);
    try {
      await onSave({ prompt, options, correct_index: correctIndex });
      setDirty(false);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="card space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-500">Question {question.index}</span>
        {dirty && !disabled && (
          <button onClick={save} disabled={saving} className="btn-secondary text-xs py-1 px-2">
            {saving ? 'Enregistrement…' : 'Enregistrer'}
          </button>
        )}
      </div>
      <textarea
        rows={2}
        value={prompt}
        disabled={disabled}
        onChange={(e) => {
          setPrompt(e.target.value);
          setDirty(true);
        }}
        className="input"
      />
      <div className="space-y-2">
        {options.map((opt, i) => (
          <label key={i} className="flex items-center gap-2 text-sm">
            <input
              type="radio"
              name={`correct-${question.index}`}
              checked={correctIndex === i}
              disabled={disabled}
              onChange={() => {
                setCorrectIndex(i);
                setDirty(true);
              }}
            />
            <input
              type="text"
              value={opt}
              disabled={disabled}
              onChange={(e) => setOption(i, e.target.value)}
              className="input flex-1"
            />
          </label>
        ))}
      </div>
    </div>
  );
}

export default function TeacherQuizReviewPage() {
  const { id, quizId } = useParams<{ id: string; quizId: string }>();
  const classId = Number(id);
  const quizIdNum = Number(quizId);

  const [quiz, setQuiz] = useState<TemplateQuiz | null>(null);
  const [stats, setStats] = useState<QuizStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [publishing, setPublishing] = useState(false);

  const load = () => {
    getClassQuiz(classId, quizIdNum)
      .then(setQuiz)
      .catch((err) => setError(getApiErrorMessage(err, 'Impossible de charger ce quiz.')));
  };

  useEffect(load, [classId, quizIdNum]);

  useEffect(() => {
    if (quiz?.status === 'published') {
      getClassQuizStats(classId, quizIdNum).then(setStats).catch(() => undefined);
    }
  }, [quiz?.status, classId, quizIdNum]);

  const handleQuestionSave = async (
    index: number,
    patch: { prompt: string; options: string[]; correct_index: number },
  ) => {
    const updated = await updateClassQuizQuestion(classId, quizIdNum, index, patch);
    setQuiz(updated);
  };

  const handlePublish = async () => {
    setError(null);
    setPublishing(true);
    try {
      const updated = await publishClassQuiz(classId, quizIdNum);
      setQuiz(updated);
    } catch (err) {
      setError(getApiErrorMessage(err, 'Échec de la publication.'));
    } finally {
      setPublishing(false);
    }
  };

  if (error) return <p className="text-rose-600">{error}</p>;
  if (!quiz) return <p className="text-slate-500">Chargement…</p>;

  const isDraft = quiz.status === 'draft';

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <Link to={`/teacher/classes/${classId}`} className="text-sm text-indigo-600 hover:underline">
            ← Retour à la classe
          </Link>
          <h1 className="text-3xl font-bold text-slate-900 mt-1">{quiz.title}</h1>
          <p className="text-slate-500 text-sm">
            {isDraft
              ? 'Relisez et corrigez les questions avant de publier aux étudiants.'
              : 'Ce quiz est publié : il a été distribué à chaque étudiant inscrit.'}
          </p>
        </div>
        {isDraft ? (
          <button onClick={handlePublish} disabled={publishing} className="btn-primary">
            {publishing ? 'Publication…' : '✅ Publier à la classe'}
          </button>
        ) : (
          <span className="text-xs font-semibold px-3 py-1.5 rounded bg-emerald-100 text-emerald-700 h-fit">
            Publié
          </span>
        )}
      </div>

      {stats && (
        <div className="card space-y-4">
          <h2 className="font-semibold text-slate-900">Résultats de la classe</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div>
              <div className="text-sm text-slate-500">Assignés</div>
              <div className="text-2xl font-bold text-slate-900">{stats.assigned}</div>
            </div>
            <div>
              <div className="text-sm text-slate-500">Passés</div>
              <div className="text-2xl font-bold text-slate-900">{stats.taken}</div>
            </div>
            <div>
              <div className="text-sm text-slate-500">Moyenne classe</div>
              <div className="text-2xl font-bold text-slate-900">
                {stats.average_score !== null ? `${stats.average_score}/10` : '—'}
              </div>
            </div>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-700 mb-2">% de réussite par question</h3>
            <div className="space-y-1">
              {stats.per_question.map((q) => (
                <div key={q.index} className="flex items-center gap-2 text-sm">
                  <span className="w-10 text-slate-500">Q{q.index}</span>
                  <div className="flex-1 bg-slate-100 rounded h-3 overflow-hidden">
                    <div
                      className="bg-indigo-500 h-full"
                      style={{ width: `${q.success_rate ?? 0}%` }}
                      title={q.prompt}
                    />
                  </div>
                  <span className="w-12 text-right text-slate-600">
                    {q.success_rate !== null ? `${q.success_rate}%` : '—'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="space-y-4">
        {quiz.questions.map((q) => (
          <QuestionEditor
            key={q.index}
            question={q}
            disabled={!isDraft}
            onSave={(patch) => handleQuestionSave(q.index, patch)}
          />
        ))}
      </div>
    </div>
  );
}
