import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import Reveal from './Reveal.jsx';
import { INGREDIENTS } from '../data/ingredients.js';

function Ingredient({ ingredient, index }) {
  const { id, name, tagline, image, productIds } = ingredient;
  const inner = (
    <>
      <span className="ingredient__img">
        <img
          src={image.src640}
          srcSet={`${image.src640} 640w, ${image.src} 1200w`}
          sizes="(min-width: 1000px) 170px, 42vw"
          width="640"
          height="427"
          alt={image.alt}
          loading="lazy"
          decoding="async"
          style={{ objectPosition: `${image.focus} 50%` }}
        />
      </span>
      <span className="ingredient__name">{name}</span>
      <span className="ingredient__tag">{tagline}</span>
    </>
  );
  return (
    <Reveal as="li" className="ingredient" delay={index * 90}>
      {productIds.length ? (
        <Link to={`/produits?ingredient=${id}`} aria-label={`${name} : voir les soins associés`}>{inner}</Link>
      ) : (
        <span className="ingredient__static">{inner}</span>
      )}
    </Reveal>
  );
}

export default function IngredientsSection() {
  return (
    <section className="home-section ingredients" aria-labelledby="ingredients-title">
      <div className="container ingredients__layout">
        <Reveal className="ingredients__intro">
          <p className="eyebrow">Les ingrédients à l’honneur</p>
          <h2 className="section-title" id="ingredients-title">La nature au cœur de votre routine</h2>
          <p className="section-intro">Découvrez les ingrédients qui inspirent notre sélection de soins.</p>
          <Link to="/produits" className="btn btn--primary ingredients__cta">
            Découvrir les soins <ArrowRight size={16} aria-hidden="true" />
          </Link>
        </Reveal>
        <ul className="ingredients__list">
          {INGREDIENTS.map((ing, i) => <Ingredient key={ing.id} ingredient={ing} index={i} />)}
        </ul>
      </div>
    </section>
  );
}
