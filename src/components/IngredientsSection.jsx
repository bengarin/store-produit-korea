import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import useReveal from '../hooks/useReveal.js';
import SectionDivider from './SectionDivider.jsx';
import { INGREDIENTS } from '../data/ingredients.js';

function IngredientCard({ ingredient, index }) {
  const [ref, visible] = useReveal();
  const { name, description, image, productIds, id } = ingredient;
  const count = productIds.length;

  return (
    <article
      ref={ref}
      className={`ingredient-card reveal ${visible ? 'is-visible' : ''}`}
      style={{ '--reveal-delay': `${index * 90}ms` }}
    >
      <div className="ingredient-card__media">
        <img
          src={image.src}
          srcSet={`${image.src640} 640w, ${image.src} 1200w`}
          sizes="(min-width: 1000px) 300px, 50vw"
          width="1200"
          height="800"
          alt={image.alt}
          loading="lazy"
          decoding="async"
          style={{ objectPosition: `${image.focus} 50%` }}
        />
      </div>
      <div className="ingredient-card__body">
        <h3 className="ingredient-card__name">{name}</h3>
        <p className="ingredient-card__desc">{description}</p>
        {count > 0 ? (
          <Link
            to={`/produits?ingredient=${id}`}
            className="ingredient-card__link"
            aria-label={`Découvrir les soins ${name} (${count} produit${count > 1 ? 's' : ''})`}
          >
            Découvrir les soins <ArrowRight size={15} aria-hidden="true" />
          </Link>
        ) : (
          <span className="ingredient-card__link is-disabled">Soins bientôt disponibles</span>
        )}
      </div>
    </article>
  );
}

export default function IngredientsSection() {
  return (
    <section className="ingredients" aria-labelledby="ingredients-title">
      <div className="container">
        <SectionDivider />
        <header className="section-head">
          <p className="eyebrow">Les ingrédients à l’honneur</p>
          <h2 className="section-title" id="ingredients-title">La nature au cœur de votre routine</h2>
          <p className="section-intro">Découvrez les ingrédients qui inspirent notre sélection de soins.</p>
        </header>
        <div className="ingredients__grid">
          {INGREDIENTS.map((ing, i) => (
            <IngredientCard key={ing.id} ingredient={ing} index={i} />
          ))}
        </div>
      </div>
    </section>
  );
}
