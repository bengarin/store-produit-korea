import { useState } from 'react';
import ProductImage from './ProductImage.jsx';

/** Grande image + vignettes. Chaque photo est déclinée en deux mises en scène. */
export default function ProductGallery({ product }) {
  const views = product.images.flatMap((image) => [
    { image, scene: 'podium' },
    { image, scene: 'tint' },
    { image, scene: 'studio' },
  ]);
  const [active, setActive] = useState(0);
  const current = views[active];

  return (
    <div className="gallery">
      <ProductImage image={current.image} product={product} scene={current.scene} eager className="gallery__main" />
      <div className="gallery__thumbs container" role="tablist" aria-label="Photos du produit">
        {views.map((v, i) => (
          <button
            key={`${v.image.src}-${v.scene}`}
            role="tab"
            aria-selected={i === active}
            aria-label={`Photo ${i + 1}`}
            className={`gallery__thumb ${i === active ? 'is-active' : ''}`}
            onClick={() => setActive(i)}
          >
            <ProductImage image={v.image} product={product} scene={v.scene} />
          </button>
        ))}
      </div>
    </div>
  );
}
