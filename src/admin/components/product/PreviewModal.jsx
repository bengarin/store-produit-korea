import { useState } from 'react';
import { ExternalLink, Monitor, RefreshCw, Smartphone } from 'lucide-react';
import { ButtonLink, Modal } from '../ui.jsx';

/** Aperçu dans un cadre à la largeur réelle (mobile 390 px / ordinateur 1280 px). */
export default function PreviewModal({ productId, onClose }) {
  const [device, setDevice] = useState('mobile');
  const [nonce, setNonce] = useState(Date.now());
  const src = `/admin/preview/products/${productId}?v=${nonce}`;
  return (
    <Modal open size="xl" title="Aperçu de la fiche produit" onClose={onClose}
      footer={(
        <>
          <div className="adm-segmented" role="group" aria-label="Appareil">
            <button type="button" className={device === 'mobile' ? 'is-active' : ''} aria-pressed={device === 'mobile'} onClick={() => setDevice('mobile')}>
              <Smartphone size={15} aria-hidden="true" /> Mobile
            </button>
            <button type="button" className={device === 'desktop' ? 'is-active' : ''} aria-pressed={device === 'desktop'} onClick={() => setDevice('desktop')}>
              <Monitor size={15} aria-hidden="true" /> Ordinateur
            </button>
          </div>
          <button type="button" className="adm-icon-btn" aria-label="Rafraîchir l’aperçu" onClick={() => setNonce(Date.now())}><RefreshCw size={17} /></button>
          <ButtonLink href={src} target="_blank" rel="noopener noreferrer" icon={ExternalLink}>Plein écran</ButtonLink>
        </>
      )}>
      <div className={`adm-preview-frame adm-preview-frame--${device}`}>
        <iframe key={`${device}-${nonce}`} title="Aperçu de la fiche produit" src={src} />
      </div>
    </Modal>
  );
}
