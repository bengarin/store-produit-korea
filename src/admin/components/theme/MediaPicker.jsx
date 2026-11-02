import { useEffect, useRef, useState } from 'react';
import { Upload } from 'lucide-react';
import { admin } from '../../api.js';
import { Button, Modal, Notice, Pagination } from '../ui.jsx';

const ACCEPT = ['image/jpeg', 'image/png', 'image/webp'];
const MAX_MB = 10;
const PAGE = 24;

/**
 * Choisir une image : médiathèque existante ou import (même route sécurisée que les produits :
 * contenu vérifié, converti en WebP, métadonnées supprimées). `onPick(media)` reçoit l'image choisie.
 */
export default function MediaPicker({ onPick, onClose, canUpload }) {
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [alt, setAlt] = useState('');
  const input = useRef(null);

  useEffect(() => {
    let alive = true;
    admin.get('/media', { page, page_size: PAGE }).then((d) => alive && setData(d)).catch((e) => alive && setError(e.message));
    return () => { alive = false; };
  }, [page]);

  const upload = async (file) => {
    if (!file) return;
    setError('');
    if (!ACCEPT.includes(file.type)) return setError('Format refusé (JPEG, PNG ou WebP).');
    if (file.size > MAX_MB * 1024 * 1024) return setError(`Fichier trop lourd (${MAX_MB} Mo max.).`);
    setBusy(true);
    try {
      const form = new FormData();
      form.append('file', file);
      if (alt.trim()) form.append('alt', alt.trim());
      onPick(await admin.upload('/media', form));
    } catch (e) {
      setError(e.fieldMessage?.('file') || e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal open size="lg" title="Choisir une image" onClose={onClose}
      footer={<Button variant="secondary" onClick={onClose}>Fermer</Button>}>
      {canUpload && (
        <div className="adm-mediapicker__upload">
          <input className="adm-input" placeholder="Texte alternatif de la nouvelle image (facultatif)" maxLength={255} value={alt} onChange={(e) => setAlt(e.target.value)}
            aria-label="Texte alternatif de la nouvelle image" />
          <input ref={input} type="file" accept={ACCEPT.join(',')} hidden aria-label="Importer une image" onChange={(e) => upload(e.target.files?.[0])} />
          <Button icon={Upload} loading={busy} onClick={() => input.current?.click()}>Importer une image</Button>
          <p className="adm-muted">JPEG, PNG ou WebP · {MAX_MB} Mo max. · convertie en WebP, métadonnées supprimées.</p>
        </div>
      )}
      {error && <Notice tone="danger">{error}</Notice>}
      {!data && !error && <p className="adm-muted">Chargement…</p>}
      {data && data.items.length === 0 && <p className="adm-muted">La médiathèque est vide.</p>}
      {data && data.items.length > 0 && (
        <ul className="adm-mediapicker__grid" aria-label="Médiathèque">
          {data.items.map((m) => (
            <li key={m.id}>
              <button type="button" onClick={() => onPick(m)} title={m.alt || m.originalFilename} aria-label={`Choisir l’image ${m.alt || m.originalFilename || m.id}`}>
                <img src={m.url640 || m.url} alt="" loading="lazy" />
                <span>{m.width}×{m.height}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {data && data.total > PAGE && <Pagination page={page} pageSize={PAGE} total={data.total} onChange={setPage} />}
    </Modal>
  );
}
