/**
 * Onglet « Quiz » — génération d'un gabarit de 10 QCM + liste des quiz de la classe (US-27).
 */
import { useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { listClassQuizzes, generateClassQuiz, type TemplateQuiz } from '@/api/classroom';
import { getApiErrorMessage } from '@/api/errors';

export default function QuizzesTab({ classId }: { classId: number }) {
  const [quizzes, setQuizzes] = useState<TemplateQuiz[] | null>(null);
  const [title, setTitle] = useState('');
  const [mode, setMode] = useState<'pdf' | 'text'>('text');
  const [pdf, setPdf] = useState<File | null>(null);
  const [sourceText, setSourceText] = useState('');
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    listClassQuizzes(classId)
      .then(setQuizzes)
      .catch((err) => setError(getApiErrorMessage(err, 'Impossible de charger les quiz.')));
  };

  useEffect(load, [classId]);

  const handleGenerate = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setGenerating(true);
    try {
      await generateClassQuiz(classId, {
        title,
        pdf: mode === 'pdf' ? (pdf ?? undefined) : undefined,
        source_text: mode === 'text' ? sourceText : undefined,
      });
      setTitle('');
      setSourceText('');
      setPdf(null);
      load();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Échec de la génération.'));
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="space-y-6">
      <form onSubmit={handleGenerate} className="card space-y-4">
        <h3 className="font-semibold text-slate-900">Générer un nouveau quiz (brouillon)</h3>
        {error && (
          <div className="p-3 bg-rose-50 border-l-4 border-rose-500 text-sm text-rose-900 rounded">{error}</div>
        )}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Titre du quiz</label>
          <input
            type="text"
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="input"
            placeholder="Ex. Chapitre 3 — Les suites"
          />
        </div>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setMode('text')}
            className={`px-3 py-1 rounded text-sm font-medium ${
              mode === 'text' ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
            }`}
          >
            📝 Texte collé
          </button>
          <button
            type="button"
            onClick={() => setMode('pdf')}
            className={`px-3 py-1 rounded text-sm font-medium ${
              mode === 'pdf' ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
            }`}
          >
            📄 PDF
          </button>
        </div>

        {mode === 'text' ? (
          <textarea
            required
            rows={8}
            minLength={200}
            value={sourceText}
            onChange={(e) => setSourceText(e.target.value)}
            placeholder="Collez le texte du cours (au moins 200 caractères)…"
            className="input"
          />
        ) : (
          <input
            type="file"
            accept=".pdf,application/pdf"
            required
            onChange={(e) => setPdf(e.target.files?.[0] ?? null)}
            className="input"
          />
        )}

        <button type="submit" disabled={generating} className="btn-primary w-full">
          {generating ? '⏳ Génération en cours…' : '🚀 Générer 10 QCM (brouillon)'}
        </button>
      </form>

      {quizzes === null ? (
        <p className="text-slate-500">Chargement…</p>
      ) : quizzes.length === 0 ? (
        <div className="card text-center py-10">
          <div className="text-4xl mb-3">🧩</div>
          <p className="text-slate-600">Aucun quiz pour cette classe pour le moment.</p>
        </div>
      ) : (
        <ul className="card divide-y divide-slate-100">
          {quizzes.map((q) => (
            <li key={q.id} className="py-3 flex items-center justify-between">
              <div>
                <Link
                  to={`/teacher/classes/${classId}/quizzes/${q.id}`}
                  className="font-medium text-slate-900 hover:text-indigo-600"
                >
                  {q.title}
                </Link>
                <p className="text-xs text-slate-500">{q.questions.length} questions</p>
              </div>
              <span
                className={`text-xs font-semibold px-2 py-1 rounded ${
                  q.status === 'published' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
                }`}
              >
                {q.status === 'published' ? 'Publié' : 'Brouillon'}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
