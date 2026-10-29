import { useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import ProductImage from './ProductImage.jsx';

/**
 * Galerie produit : grande image (flèches, zoom discret au survol), vignettes cliquables.
 * `badge` et `actions` sont posés sur l'image (catégorie, favori…).
 */
export default function ProductGallery({ product, badge = null, actions = null }) {
  const images = product.galleryImages;
  const [active, setActive] = useState(0);
  const [origin, setOrigin] = useState('50% 50%');
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
            <button className="gallery__arrow gallery__arrow--prev" onClick={() => go(-1)} aria-label="Photo précédente"><ChevronLeft size={20} /></button>
            <button className="gallery__arrow gallery__arrow--next" onClick={() => go(1)} aria-label="Photo suivante"><ChevronRight size={20} /></button>
          </>
        )}
      </div>
      {images.length > 1 && (
        <div className="gallery__thumbs" role="tablist" aria-label="Photos du produit">
          {images.map((image, i) => (
            <button
              key={image.src}
              role="tab"
              aria-selected={i === active}
              aria-label={`Photo ${i + 1} : ${image.alt}`}
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
