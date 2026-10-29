import { useState } from 'react';
import ProductImage from './ProductImage.jsx';

/** Grande image + vignettes cliquables (packshot, emballage, texture, ambiance…). */
export default function ProductGallery({ product }) {
  const images = product.galleryImages;
  const [active, setActive] = useState(0);

  return (
    <div className="gallery">
      <ProductImage image={images[active]} eager className="gallery__main" />
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
