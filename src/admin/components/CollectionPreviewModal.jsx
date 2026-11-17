import { useState } from 'react';
import { ExternalLink, Monitor, RefreshCw, Smartphone } from 'lucide-react';
import { ButtonLink, Modal, Notice } from './ui.jsx';

/**
 * Aperçu de DÉMONSTRATION d'une collection (produits fictifs) dans un cadre à la largeur réelle :
 * mobile 390 px / ordinateur 1280 px, en français ou en arabe (droite à gauche).
 */
export default function CollectionPreviewModal({ collection, onClose }) {
  const [device, setDevice] = useState('desktop');
  const [lang, setLang] = useState('fr');
  const [nonce, setNonce] = useState(Date.now());
  const src = `/admin/preview/collections/${encodeURIComponent(collection.slug)}?${lang === 'ar' ? 'lang=ar&' : ''}v=${nonce}`;
  const segment = (value, current, set, label, Icon) => (
    <button type="button" className={current === value ? 'is-active' : ''} aria-pressed={current === value} onClick={() => set(value)}>
      {Icon && <Icon size={15} aria-hidden="true" />} {label}
    </button>
  );
  return (
    <Modal open size="xl" title={`Aperçu TEST de « ${collection.name} »`} onClose={onClose}
      footer={(
        <>
          <div className="adm-segmented" role="group" aria-label="Appareil">
            {segment('mobile', device, setDevice, 'Mobile', Smartphone)}
            {segment('desktop', device, setDevice, 'Ordinateur', Monitor)}
          </div>
          <div className="adm-segmented" role="group" aria-label="Langue">
            {segment('fr', lang, setLang, 'Français')}
            {segment('ar', lang, setLang, 'العربية')}
          </div>
          <button type="button" className="adm-icon-btn" aria-label="Rafraîchir l’aperçu" onClick={() => setNonce(Date.now())}><RefreshCw size={17} /></button>
          <ButtonLink href={src} target="_blank" rel="noopener noreferrer" icon={ExternalLink}>Plein écran</ButtonLink>
        </>
      )}>
      <div className="adm-demo-modal">
      <Notice tone="warning">
        <strong>TEST — données fictives.</strong> Produits, prix et images inventés pour voir la mise en page. Rien n’est enregistré,
        aucun vrai produit n’est modifié et les clients ne voient pas cet aperçu.
      </Notice>
      <div className={`adm-preview-frame adm-preview-frame--${device}`}>
        <iframe key={`${device}-${lang}-${nonce}`} title={`Aperçu TEST de la collection ${collection.name}`} src={src} />
      </div>
      </div>
    </Modal>
  );
}
