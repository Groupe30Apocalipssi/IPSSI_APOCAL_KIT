/**
 * Espace enseignant — liste des classes gérées + création (US-25).
 */
import { useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { listClasses, createClass, type Classe } from '@/api/classroom';
import { getApiErrorMessage } from '@/api/errors';

export default function TeacherClassesPage() {
  const [classes, setClasses] = useState<Classe[] | null>(null);
  const [name, setName] = useState('');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    listClasses()
      .then(setClasses)
      .catch((err) => setError(getApiErrorMessage(err, 'Impossible de charger vos classes.')));
  };

  useEffect(load, []);

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setCreating(true);
    try {
      await createClass(name);
      setName('');
      load();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Création impossible.'));
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Mes classes</h1>
        <p className="text-slate-500 text-sm">
          Créez une classe, partagez son code aux étudiants, gérez vos supports de cours et vos quiz.
        </p>
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border-l-4 border-rose-500 text-sm text-rose-900 rounded">{error}</div>
      )}

      <form onSubmit={handleCreate} className="card flex gap-3 items-end flex-wrap">
        <div className="flex-1 min-w-[220px]">
          <label className="block text-sm font-medium text-slate-700 mb-1">Nom de la classe</label>
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Ex. Terminale S — Groupe 2"
            className="input"
          />
        </div>
        <button type="submit" disabled={creating} className="btn-primary">
          {creating ? 'Création…' : '+ Créer la classe'}
        </button>
      </form>

      {classes === null ? (
        <p className="text-slate-500">Chargement…</p>
      ) : classes.length === 0 ? (
        <div className="card text-center py-12">
          <div className="text-5xl mb-4">🏫</div>
          <p className="text-slate-600">Vous n'avez pas encore de classe. Créez-en une ci-dessus.</p>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {classes.map((c) => (
            <div key={c.id} className="card hover:shadow-md transition flex flex-col">
              <h2 className="text-lg font-semibold text-slate-900">{c.name}</h2>
              <p className="text-sm text-slate-500 mt-1">
                Code : <span className="font-mono font-semibold text-indigo-600">{c.code}</span>
              </p>
              <p className="text-sm text-slate-500 mt-1">
                {c.students_count} étudiant{c.students_count > 1 ? 's' : ''}
              </p>
              <Link to={`/teacher/classes/${c.id}`} className="btn-primary w-full mt-4">
                Entrer dans la classe →
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
