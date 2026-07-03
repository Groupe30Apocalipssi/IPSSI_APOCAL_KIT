/**
 * Vue étudiant d'une classe rejointe : supports de cours de l'enseignant
 * (US-26 côté consultation) + liste des quiz publiés (les copies personnelles
 * de l'étudiant, elles, sont jouées depuis /history — voir JoinClassView côté
 * backend qui les y ajoute automatiquement).
 */
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { getClass, listDocuments, listClassQuizzes, type Classe, type CourseDocument, type TemplateQuiz } from '@/api/classroom';
import { getApiErrorMessage } from '@/api/errors';
import PdfDocumentList from '@/components/PdfDocumentList';

export default function StudentClassPage() {
  const { id } = useParams<{ id: string }>();
  const classId = Number(id);

  const [classe, setClasse] = useState<Classe | null>(null);
  const [documents, setDocuments] = useState<CourseDocument[] | null>(null);
  const [quizzes, setQuizzes] = useState<TemplateQuiz[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getClass(classId)
      .then(setClasse)
      .catch((err) => setError(getApiErrorMessage(err, 'Impossible de charger cette classe.')));
    listDocuments(classId)
      .then(setDocuments)
      .catch(() => setDocuments([]));
    listClassQuizzes(classId)
      .then(setQuizzes)
      .catch(() => setQuizzes([]));
  }, [classId]);

  if (error) return <p className="text-rose-600">{error}</p>;
  if (!classe) return <p className="text-slate-500">Chargement…</p>;

  return (
    <div className="space-y-6">
      <div>
        <Link to="/join-class" className="text-sm text-indigo-600 hover:underline">
          ← Mes classes
        </Link>
        <h1 className="text-3xl font-bold text-slate-900 mt-1">{classe.name}</h1>
      </div>

      <div className="card">
        <h2 className="font-semibold text-slate-900 mb-3">📄 Supports de cours</h2>
        {documents === null ? (
          <p className="text-sm text-slate-500">Chargement…</p>
        ) : documents.length === 0 ? (
          <p className="text-sm text-slate-500">
            Votre enseignant n'a pas encore ajouté de support de cours.
          </p>
        ) : (
          <PdfDocumentList documents={documents} />
        )}
      </div>

      <div className="card">
        <h2 className="font-semibold text-slate-900 mb-3">🧩 Quiz de la classe</h2>
        {quizzes === null ? (
          <p className="text-sm text-slate-500">Chargement…</p>
        ) : quizzes.length === 0 ? (
          <p className="text-sm text-slate-500">Aucun quiz publié pour le moment.</p>
        ) : (
          <>
            <ul className="divide-y divide-slate-100 mb-3">
              {quizzes.map((q) => (
                <li key={q.id} className="py-2 text-sm text-slate-700">
                  {q.title}
                </li>
              ))}
            </ul>
            <Link to="/history" className="text-sm text-indigo-600 hover:underline">
              Retrouvez-les et passez-les depuis votre historique →
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
