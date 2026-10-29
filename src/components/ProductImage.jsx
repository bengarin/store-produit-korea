/**
 * Affiche une photo produit avec le bon traitement :
 *  - fit 'contain' : packshot entier sur fond crème (le blanc de la photo se fond dans le crème)
 *  - fit 'cover'   : photo d'ambiance qui remplit le cadre
 */
export default function ProductImage({ image, eager = false, className = '', position }) {
  const fit = image.fit === 'cover' ? 'cover' : 'contain';
  return (
    <div className={`product-image product-image--${fit} ${className}`}>
      <img
        src={image.src}
        alt={image.alt}
        loading={eager ? 'eager' : 'lazy'}
        decoding="async"
        width="900"
        height="900"
        style={position ? { objectPosition: position } : undefined}
      />
    </div>
  );
}
