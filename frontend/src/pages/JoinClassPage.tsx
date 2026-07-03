/**
 * Un étudiant rejoint une classe via le code communiqué par l'enseignant.
 * Les quiz déjà publiés dans la classe sont automatiquement ajoutés à son
 * historique (voir /history) dès qu'il rejoint.
 */
import { useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { joinClass, listClasses, type Classe } from '@/api/classroom';
import { getApiErrorMessage } from '@/api/errors';

export default function JoinClassPage() {
  const [code, setCode] = useState('');
  const [classes, setClasses] = useState<Classe[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = () => {
    listClasses()
      .then(setClasses)
      .catch(() => undefined);
  };

  useEffect(load, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setLoading(true);
    try {
      const classe = await joinClass(code.trim().toUpperCase());
      setSuccess(`Vous avez rejoint « ${classe.name} ». Retrouvez vos quiz dans l'historique.`);
      setCode('');
      load();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Impossible de rejoindre cette classe.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Rejoindre une classe</h1>
        <p className="text-slate-500 text-sm">
          Saisissez le code communiqué par votre enseignant (6 caractères).
        </p>
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border-l-4 border-rose-500 text-sm text-rose-900 rounded">{error}</div>
      )}
      {success && (
        <div className="p-3 bg-emerald-50 border-l-4 border-emerald-500 text-sm text-emerald-900 rounded">
          {success}
        </div>
      )}

      <form onSubmit={handleSubmit} className="card space-y-4">
        <input
          type="text"
          required
          maxLength={6}
          value={code}
          onChange={(e) => setCode(e.target.value.toUpperCase())}
          placeholder="Ex. AB12CD"
          className="input font-mono tracking-widest text-center text-lg"
        />
        <button type="submit" disabled={loading} className="btn-primary w-full">
          {loading ? 'Connexion…' : 'Rejoindre'}
        </button>
      </form>

      {classes && classes.length > 0 && (
        <div className="card">
          <h2 className="font-semibold text-slate-900 mb-2">Mes classes</h2>
          <ul className="divide-y divide-slate-100">
            {classes.map((c) => (
              <li key={c.id} className="py-2 flex items-center justify-between gap-3">
                <span className="text-sm text-slate-700">{c.name}</span>
                <Link to={`/classes/${c.id}`} className="btn-secondary text-xs py-1.5 px-3 shrink-0">
                  Entrer dans la classe →
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}

      <Link to="/history" className="block text-center text-sm text-indigo-600 hover:underline">
        Voir mon historique de quiz →
      </Link>
    </div>
  );
}
