import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import Reveal from './Reveal.jsx';
import { INGREDIENTS } from '../data/ingredients.js';
import bg from '../assets/backgrounds/ingredients-bg.webp';
import bg960 from '../assets/backgrounds/ingredients-bg-960.webp';

function Ingredient({ ingredient, index }) {
  const { id, name, tagline, image, productIds } = ingredient;
  return (
    <Reveal as="li" className="ingredient" delay={index * 90}>
      <div className="ingredient__arch">
        <img
          src={image.src640}
          srcSet={`${image.src640} 640w, ${image.src} 1200w`}
          sizes="(min-width: 1000px) 300px, 46vw"
          width="640"
          height="427"
          alt={image.alt}
          loading="lazy"
          decoding="async"
          style={{ objectPosition: `${image.focus} 50%` }}
        />
      </div>
      <span className="ingredient__dash" aria-hidden="true" />
      <h3 className="ingredient__name">{name}</h3>
      <p className="ingredient__tag">{tagline}</p>
      {productIds.length ? (
        <Link to={`/produits?ingredient=${id}`} className="ingredient__link" aria-label={`Découvrir les soins ${name}`}>
          <span>Découvrir les soins</span> <ArrowRight size={16} aria-hidden="true" />
        </Link>
      ) : (
        <span className="ingredient__link is-disabled">Soins bientôt disponibles</span>
      )}
    </Reveal>
  );
}

export default function IngredientsSection() {
  return (
    <section
      className="home-section ingredients"
      aria-labelledby="ingredients-title"
      style={{ '--ing-bg': `url(${bg})`, '--ing-bg-sm': `url(${bg960})` }}
    >
      <div className="container">
        <Reveal as="header" className="ingredients__head">
          <svg className="ingredients__leaf" viewBox="0 0 40 32" aria-hidden="true">
            <path d="M20 30 C 12 28 7 22 7 14 C 14 15 19 21 20 30 Z" />
            <path d="M20 30 C 28 28 33 22 33 14 C 26 15 21 21 20 30 Z" />
            <path d="M20 22 C 15 18 14 10 20 2 C 26 10 25 18 20 22 Z" />
          </svg>
          <p className="ingredients__eyebrow">Nos ingrédients naturels</p>
          <h2 className="ingredients__title" id="ingredients-title">Des actifs choisis pour votre peau</h2>
          <p className="ingredients__intro">Des ingrédients inspirés par la nature et les traditions de beauté coréennes.</p>
        </Reveal>
        <ul className="ingredients__list">
          {INGREDIENTS.map((ing, i) => <Ingredient key={ing.id} ingredient={ing} index={i} />)}
        </ul>
      </div>
    </section>
  );
}
