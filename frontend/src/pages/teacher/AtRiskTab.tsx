/**
 * Onglet « Difficultés » — étudiants en difficulté (moyenne basse / aucun quiz passé).
 */
import { useEffect, useState } from 'react';
import { getAtRiskStudents, type AtRiskStudent } from '@/api/classroom';
import { getApiErrorMessage } from '@/api/errors';

export default function AtRiskTab({ classId }: { classId: number }) {
  const [threshold, setThreshold] = useState(5);
  const [students, setStudents] = useState<AtRiskStudent[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = (t: number) => {
    getAtRiskStudents(classId, t)
      .then((r) => setStudents(r.students))
      .catch((err) => setError(getApiErrorMessage(err, 'Impossible de charger les étudiants en difficulté.')));
  };

  useEffect(() => load(threshold), [classId]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="space-y-4">
      <div className="card flex items-center gap-3 flex-wrap">
        <label className="text-sm text-slate-700">
          Seuil de difficulté :
          <input
            type="number"
            min={0}
            max={10}
            step={0.5}
            value={threshold}
            onChange={(e) => setThreshold(Number(e.target.value))}
            className="input inline-block w-20 mx-2"
          />
          / 10
        </label>
        <button className="btn-secondary" onClick={() => load(threshold)}>
          Actualiser
        </button>
      </div>

      {error && <p className="text-rose-600">{error}</p>}

      {students === null ? (
        <p className="text-slate-500">Chargement…</p>
      ) : students.length === 0 ? (
        <div className="card text-center py-10">
          <div className="text-4xl mb-3">✅</div>
          <p className="text-slate-600">Aucun étudiant en difficulté pour ce seuil.</p>
        </div>
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-200">
                <th className="py-2 pr-3">Étudiant</th>
                <th className="py-2 pr-3">Moyenne</th>
                <th className="py-2 pr-3">Quiz passés</th>
                <th className="py-2 pr-3">Motif</th>
              </tr>
            </thead>
            <tbody>
              {students.map((s) => (
                <tr key={s.id} className="border-b border-slate-100 last:border-0">
                  <td className="py-2 pr-3 text-slate-900">
                    {s.first_name || s.last_name ? `${s.first_name} ${s.last_name}`.trim() : s.email}
                  </td>
                  <td className="py-2 pr-3 font-medium text-rose-600">
                    {s.average_score !== null ? `${s.average_score}/10` : '—'}
                  </td>
                  <td className="py-2 pr-3">{s.quizzes_taken}</td>
                  <td className="py-2 pr-3 text-slate-500">{s.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
