import { useState } from 'react';
import ProductImage from './ProductImage.jsx';

/** Grande image + vignettes. Chaque photo est montrée dans plusieurs mises en scène. */
export default function ProductGallery({ product }) {
  const views = product.images.flatMap((image, i) =>
    i === 0
      ? [{ image, scene: 'podium' }, { image, scene: 'plain' }, { image, scene: 'duo' }]
      : [{ image, scene: 'plain' }],
  );
  const [active, setActive] = useState(0);
  const current = views[active];

  return (
    <div className="gallery">
      <ProductImage image={current.image} scene={current.scene} eager className="gallery__main" />
      <div className="gallery__thumbs" role="tablist" aria-label="Photos du produit">
        {views.map((v, i) => (
          <button
            key={`${v.image.src}-${v.scene}`}
            role="tab"
            aria-selected={i === active}
            aria-label={`Photo ${i + 1}`}
            className={`gallery__thumb ${i === active ? 'is-active' : ''}`}
            onClick={() => setActive(i)}
          >
            <ProductImage image={v.image} scene={v.scene} />
          </button>
        ))}
      </div>
    </div>
  );
}
