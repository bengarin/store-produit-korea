import podiumImg from '../assets/backgrounds/podium-single.webp';

/**
 * Photo produit posée sur un fond.
 * scene = 'tint' (fond coloré doux) | 'podium' (fond pierre & feuilles) | 'studio' (crème uni)
 */
export default function ProductImage({ image, product, scene = 'tint', eager = false, className = '' }) {
  const style =
    scene === 'podium'
      ? { backgroundImage: `url(${podiumImg})` }
      : scene === 'tint'
        ? { '--tint': product.tint }
        : undefined;
  return (
    <div className={`product-image product-image--${scene} ${className}`} style={style}>
      <img
        src={image.src}
        alt={image.alt}
        loading={eager ? 'eager' : 'lazy'}
        decoding="async"
        width="400"
        height="400"
      />
    </div>
  );
}
