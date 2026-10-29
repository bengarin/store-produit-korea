import podiumImg from '../assets/backgrounds/podium-single.webp';
import duoImg from '../assets/backgrounds/podium-duo.webp';

const SCENES = { podium: podiumImg, duo: duoImg };

/**
 * Packshot produit (object-fit: contain) posé sur un fond.
 * scene = 'plain' (crème uni) | 'podium' | 'duo' (fonds pierre & feuilles)
 */
export default function ProductImage({ image, scene = 'plain', eager = false, className = '' }) {
  const bg = SCENES[scene];
  return (
    <div className={`product-image product-image--${scene} ${className}`} style={bg ? { backgroundImage: `url(${bg})` } : undefined}>
      <img
        src={image.src}
        alt={image.alt}
        loading={eager ? 'eager' : 'lazy'}
        decoding="async"
        width="480"
        height="480"
      />
    </div>
  );
}
