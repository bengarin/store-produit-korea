import { useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import ProductImage from './ProductImage.jsx';
import { useI18n } from '../i18n/I18nContext.jsx';

/**
 * Galerie produit : grande image (flèches, zoom discret au survol), vignettes cliquables.
 * `badge` et `actions` sont posés sur l'image (catégorie, favori…).
 */
export default function ProductGallery({ product, badge = null, actions = null, focusImage = null }) {
  // Image propre à la variante choisie : affichée (ajoutée en tête si elle n'est pas dans la galerie).
  const inGallery = focusImage ? product.galleryImages.findIndex((img) => img.src === focusImage.src) : -1;
  const images = focusImage && inGallery < 0 ? [focusImage, ...product.galleryImages] : product.galleryImages;
  const [active, setActive] = useState(() => (focusImage ? Math.max(inGallery, 0) : 0));
  const [shown, setShown] = useState(focusImage?.src || null);
  if ((focusImage?.src || null) !== shown) {
    // Changement de variante : on montre sa photo (ajustement pendant le rendu, sans effet).
    setShown(focusImage?.src || null);
    setActive(focusImage ? Math.max(inGallery, 0) : 0);
  }
  const [origin, setOrigin] = useState('50% 50%');
  const { t } = useI18n();
  const go = (d) => setActive((i) => (i + d + images.length) % images.length);

  const onMove = (e) => {
    const r = e.currentTarget.getBoundingClientRect();
    setOrigin(`${((e.clientX - r.left) / r.width) * 100}% ${((e.clientY - r.top) / r.height) * 100}%`);
  };

  return (
    <div className="gallery">
      <div className="gallery__stage" onMouseMove={onMove} style={{ '--zoom-origin': origin }}>
        <ProductImage key={images[active].src} image={images[active]} eager className="gallery__main" />
        {badge}
        {actions}
        {images.length > 1 && (
          <>
            <button className="gallery__arrow gallery__arrow--prev" onClick={() => go(-1)} aria-label={t('gallery.prev')}><ChevronLeft size={20} /></button>
            <button className="gallery__arrow gallery__arrow--next" onClick={() => go(1)} aria-label={t('gallery.next')}><ChevronRight size={20} /></button>
          </>
        )}
      </div>
      {images.length > 1 && (
        <div className="gallery__thumbs" role="tablist" aria-label={t('gallery.thumbs')}>
          {images.map((image, i) => (
            <button
              key={image.src}
              role="tab"
              aria-selected={i === active}
              aria-label={t('gallery.thumb', { index: i + 1, alt: image.alt })}
              className={`gallery__thumb ${i === active ? 'is-active' : ''}`}
              onClick={() => setActive(i)}
            >
              <ProductImage image={image} />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
