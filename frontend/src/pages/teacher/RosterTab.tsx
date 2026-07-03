/**
 * Onglet « Étudiants » — roster de la classe (US roster + US scores individuels).
 */
import { useEffect, useState } from 'react';
import { getRoster, getStudentDetail, type RosterStudent, type StudentDetail } from '@/api/classroom';
import { getApiErrorMessage } from '@/api/errors';

export default function RosterTab({ classId }: { classId: number }) {
  const [students, setStudents] = useState<RosterStudent[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<StudentDetail | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);

  useEffect(() => {
    getRoster(classId)
      .then((r) => setStudents(r.students))
      .catch((err) => setError(getApiErrorMessage(err, 'Impossible de charger la liste des étudiants.')));
  }, [classId]);

  const openStudent = async (studentId: number) => {
    setDetailError(null);
    setSelected(null);
    try {
      const detail = await getStudentDetail(classId, studentId);
      setSelected(detail);
    } catch (err) {
      setDetailError(getApiErrorMessage(err, "Impossible de charger le détail de l'étudiant."));
    }
  };

  if (error) return <p className="text-rose-600">{error}</p>;
  if (students === null) return <p className="text-slate-500">Chargement…</p>;

  if (students.length === 0) {
    return (
      <div className="card text-center py-10">
        <div className="text-4xl mb-3">🙋</div>
        <p className="text-slate-600">Aucun étudiant n'a encore rejoint cette classe.</p>
      </div>
    );
  }

  return (
    <div className="grid lg:grid-cols-2 gap-4">
      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-500 border-b border-slate-200">
              <th className="py-2 pr-3">Étudiant</th>
              <th className="py-2 pr-3">Quiz passés</th>
              <th className="py-2 pr-3">Moyenne</th>
            </tr>
          </thead>
          <tbody>
            {students.map((s) => (
              <tr
                key={s.id}
                onClick={() => openStudent(s.id)}
                className="border-b border-slate-100 last:border-0 cursor-pointer hover:bg-slate-50"
              >
                <td className="py-2 pr-3 text-slate-900">
                  {s.first_name || s.last_name ? `${s.first_name} ${s.last_name}`.trim() : s.email}
                </td>
                <td className="py-2 pr-3">
                  {s.quizzes_taken} / {s.quizzes_assigned}
                </td>
                <td className="py-2 pr-3 font-medium">
                  {s.average_score !== null ? `${s.average_score}/10` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h3 className="font-semibold text-slate-900 mb-3">Détail étudiant</h3>
        {detailError && <p className="text-rose-600 text-sm">{detailError}</p>}
        {!selected && !detailError && (
          <p className="text-sm text-slate-500">Cliquez sur un étudiant pour voir ses scores.</p>
        )}
        {selected && (
          <div className="space-y-3">
            <div>
              <p className="font-medium text-slate-900">
                {selected.student.first_name || selected.student.last_name
                  ? `${selected.student.first_name} ${selected.student.last_name}`.trim()
                  : selected.student.email}
              </p>
              <p className="text-xs text-slate-500">{selected.student.email}</p>
              <p className="text-sm text-slate-600 mt-1">
                Moyenne : <span className="font-semibold">{selected.average_score ?? '—'}/10</span>
              </p>
            </div>
            <ul className="divide-y divide-slate-100">
              {selected.quizzes.length === 0 && (
                <li className="py-2 text-sm text-slate-500">Aucun quiz assigné.</li>
              )}
              {selected.quizzes.map((q) => (
                <li key={q.quiz_id} className="py-2 flex items-center justify-between text-sm">
                  <span>{q.title}</span>
                  <span className="font-medium">{q.score !== null ? `${q.score}/10` : 'Non passé'}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
