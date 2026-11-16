import { Star } from 'lucide-react';

/** Note en étoiles (lecture seule). `value` peut être décimal (moyenne) : arrondi à la demi-étoile la plus proche. */
export default function Stars({ value, size = 16, label }) {
  const rounded = Math.round(value * 2) / 2;
  return (
    <span className="stars" role="img" aria-label={label}>
      {[1, 2, 3, 4, 5].map((n) => {
        const fill = rounded >= n ? 'full' : rounded >= n - 0.5 ? 'half' : 'empty';
        return (
          <span key={n} className={`stars__star stars__star--${fill}`} aria-hidden="true">
            <Star size={size} strokeWidth={1.5} />
            {fill !== 'empty' && <Star size={size} strokeWidth={1.5} className="stars__fill" />}
          </span>
        );
      })}
    </span>
  );
}
