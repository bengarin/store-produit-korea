import { Quote } from 'lucide-react';
import Reveal from './Reveal.jsx';

/**
 * Témoignages clients (section « testimonials »). Affiche UNIQUEMENT les avis saisis par l'équipe
 * (vrais avis, avec l'accord du client) ; aucun exemple, aucune note inventée. Vide = section masquée.
 */
export default function Testimonials({ section }) {
  const items = (section.items || []).filter((t) => t.quote && t.author);
  if (!items.length) return null;
  const { eyebrow, heading } = section.settings;
  const titleId = `${section.id}-title`;
  return (
    <section className="home-section testimonials" aria-labelledby={titleId}>
      <div className="container">
        <Reveal as="header" className="section-head">
          {eyebrow && <p className="eyebrow">{eyebrow}</p>}
          <h2 className="section-title" id={titleId}>{heading}</h2>
        </Reveal>
        <ul className="testimonials__list">
          {items.map((t, i) => (
            <Reveal as="li" key={i} className="testimonial" delay={i * 80}>
              <Quote size={22} strokeWidth={1.4} className="testimonial__icon" aria-hidden="true" />
              <blockquote className="testimonial__quote"><p>{t.quote}</p></blockquote>
              <p className="testimonial__author">
                <strong>{t.author}</strong>
                {t.detail && <span> · {t.detail}</span>}
              </p>
            </Reveal>
          ))}
        </ul>
      </div>
    </section>
  );
}
