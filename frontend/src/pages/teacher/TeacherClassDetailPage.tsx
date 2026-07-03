/**
 * Détail d'une classe (espace enseignant) — onglets Étudiants / Documents / Quiz / Difficultés.
 */
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getClass, type Classe } from '@/api/classroom';
import { getApiErrorMessage } from '@/api/errors';
import RosterTab from './RosterTab';
import DocumentsTab from './DocumentsTab';
import QuizzesTab from './QuizzesTab';
import AtRiskTab from './AtRiskTab';

type TabKey = 'students' | 'documents' | 'quizzes' | 'at-risk';

const TABS: { key: TabKey; label: string }[] = [
  { key: 'students', label: 'Étudiants' },
  { key: 'documents', label: 'Supports de cours' },
  { key: 'quizzes', label: 'Quiz' },
  { key: 'at-risk', label: 'Difficultés' },
];

export default function TeacherClassDetailPage() {
  const { id } = useParams<{ id: string }>();
  const classId = Number(id);
  const [classe, setClasse] = useState<Classe | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<TabKey>('students');

  useEffect(() => {
    getClass(classId)
      .then(setClasse)
      .catch((err) => setError(getApiErrorMessage(err, 'Impossible de charger cette classe.')));
  }, [classId]);

  if (error) return <p className="text-rose-600">{error}</p>;
  if (!classe) return <p className="text-slate-500">Chargement…</p>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">{classe.name}</h1>
        <p className="text-slate-500 text-sm">
          Code à partager aux étudiants :{' '}
          <span className="font-mono font-semibold text-indigo-600">{classe.code}</span> ·{' '}
          {classe.students_count} étudiant{classe.students_count > 1 ? 's' : ''}
        </p>
      </div>

      <div className="border-b border-slate-200 flex flex-wrap gap-1">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition ${
              tab === t.key
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'students' && <RosterTab classId={classId} />}
      {tab === 'documents' && <DocumentsTab classId={classId} />}
      {tab === 'quizzes' && <QuizzesTab classId={classId} />}
      {tab === 'at-risk' && <AtRiskTab classId={classId} />}
    </div>
  );
}
