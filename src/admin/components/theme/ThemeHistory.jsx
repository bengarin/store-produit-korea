import { useEffect, useState } from 'react';
import { Eye, FileDown, Rocket } from 'lucide-react';
import { admin } from '../../api.js';
import { formatDate } from '../../format.js';
import { Badge, Button, Modal, Notice } from '../ui.jsx';

/**
 * Historique des publications. Pour chaque version :
 * - Aperçu (lecture seule, rien n'est modifié) ;
 * - Charger dans le brouillon (pour la retravailler, sans publier) — Propriétaire, Admin, Éditeur ;
 * - Republier (retour immédiat à cette version ; une nouvelle version est créée) — Propriétaire, Admin.
 */
export default function ThemeHistory({ server, canEdit, canPublish, unsaved, onClose, onPreview, onDone, onError }) {
  const [items, setItems] = useState(null);
  const [error, setError] = useState('');
  const [confirm, setConfirm] = useState(null); // { action: 'load' | 'restore', number }
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    admin.get('/theme/versions').then((d) => setItems(d.items)).catch((e) => setError(e.message));
  }, []);

  const preview = async (number) => {
    try {
      const v = await admin.get(`/theme/versions/${number}`);
      onPreview({ number, data: v.data, media: v.media });
    } catch (e) {
      setError(e.message);
    }
  };
  const run = async () => {
    setBusy(true);
    const { action, number } = confirm;
    try {
      if (action === 'load') {
        const state = await admin.post(`/theme/versions/${number}/load`, { revision: server.draft.revision });
        onDone(state, `Version ${number} chargée dans le brouillon. Rien n’est publié.`);
      } else {
        const state = await admin.post(`/theme/versions/${number}/restore`);
        onDone(state, `Version ${number} republiée (nouvelle version ${state.publishedNumber}). La boutique l’affiche maintenant.`);
      }
    } catch (e) {
      onError(e);
    } finally {
      setBusy(false);
    }
  };

  if (confirm) {
    const restore = confirm.action === 'restore';
    return (
      <Modal open title={restore ? `Republier la version ${confirm.number} ?` : `Charger la version ${confirm.number} ?`} onClose={() => setConfirm(null)}
        footer={(
          <>
            <Button variant="secondary" onClick={() => setConfirm(null)} disabled={busy}>Annuler</Button>
            <Button loading={busy} onClick={run}>{restore ? 'Republier maintenant' : 'Charger dans le brouillon'}</Button>
          </>
        )}>
        {restore ? (
          <p>La boutique publique affichera immédiatement la version {confirm.number}. Une nouvelle version est ajoutée à l’historique ; votre brouillon n’est pas modifié.</p>
        ) : (
          <p>Le brouillon sera remplacé par la version {confirm.number}. La boutique publique ne change pas.
            {unsaved && <strong> Vos modifications non enregistrées seront perdues.</strong>}</p>
        )}
      </Modal>
    );
  }

  return (
    <Modal open size="lg" title="Historique des publications" onClose={onClose}
      footer={<Button variant="secondary" onClick={onClose}>Fermer</Button>}>
      {error && <Notice tone="danger">{error}</Notice>}
      {!items && !error && <p className="adm-muted">Chargement…</p>}
      {items && items.length === 0 && <p className="adm-muted">Aucune publication pour l’instant : la boutique affiche le thème d’origine.</p>}
      {items && items.length > 0 && (
        <ol className="adm-theme-history">
          {items.map((v) => (
            <li key={v.number} className={v.isCurrent ? 'is-current' : ''}>
              <div>
                <strong>Version {v.number}</strong> {v.isCurrent && <Badge tone="success">En ligne</Badge>}
                <span className="adm-muted">
                  {formatDate(v.publishedAt)} · {v.publishedBy?.name || '—'}
                  {v.source === 'restore' ? ` · restauration de la version ${v.restoredFrom}` : ''}
                </span>
                {v.note && v.source !== 'restore' && <span className="adm-theme-history__note">« {v.note} »</span>}
              </div>
              <div className="adm-theme-history__actions">
                <Button size="sm" variant="ghost" icon={Eye} onClick={() => preview(v.number)}>Aperçu</Button>
                {canEdit && <Button size="sm" variant="ghost" icon={FileDown} onClick={() => setConfirm({ action: 'load', number: v.number })}>Charger</Button>}
                {canPublish && !v.isCurrent && <Button size="sm" variant="secondary" icon={Rocket} onClick={() => setConfirm({ action: 'restore', number: v.number })}>Republier</Button>}
              </div>
            </li>
          ))}
        </ol>
      )}
    </Modal>
  );
}
