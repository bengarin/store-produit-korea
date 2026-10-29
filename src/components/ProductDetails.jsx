import { useState } from 'react';
import { FileText, Leaf, Hand, Sparkles } from 'lucide-react';
import Accordion from './Accordion.jsx';
import ProductImage from './ProductImage.jsx';

/** Contenu des 4 rubriques, à partir des données produit existantes uniquement. */
function useSections(product) {
  const visual = product.galleryImages.find((g) => g.fit === 'cover') || product.galleryImages[1] || product.mainImage;
  return [
    {
      id: 'description',
      title: 'Description',
      body: (
        <div className="pdp-desc">
          <div className="pdp-desc__text">
            <h3 className="pdp-desc__title">À propos de ce soin</h3>
            <p>{product.summary}</p>
            <p className="pdp-desc__meta"><strong>Type de peau :</strong> {product.skinTypes}</p>
          </div>
          <ProductImage image={visual} className="pdp-desc__visual" />
          <ul className="pdp-tiles pdp-tiles--wide">
            {product.highlights.map(({ icon: Icon, label }) => (
              <li key={label}><Icon size={26} strokeWidth={1.3} aria-hidden="true" /><span>{label}</span></li>
            ))}
          </ul>
        </div>
      ),
    },
    { id: 'ingredients', title: 'Ingrédients', body: <ul className="pdp-list">{product.ingredients.map((x) => <li key={x}>{x}</li>)}</ul> },
    { id: 'usage', title: 'Conseils d’utilisation', body: <ol className="pdp-list">{product.usage.map((x) => <li key={x}>{x}</li>)}</ol> },
    {
      id: 'benefits',
      title: 'Points forts',
      body: (
        <>
          <ul className="pdp-list">{product.benefits.map((x) => <li key={x}>{x}</li>)}</ul>
          <p className="pdp-desc__meta"><strong>Type de peau :</strong> {product.skinTypes}</p>
        </>
      ),
    },
  ];
}

/** Onglets sur ordinateur ; sur mobile, une carte blanche avec les 4 rubriques repliables. */
export default function ProductDetails({ product, desktop }) {
  const sections = useSections(product);
  const [tab, setTab] = useState('description');

  if (!desktop) {
    // Mobile : une seule carte blanche, 4 rubriques repliables (Description ouverte par défaut).
    const icons = { description: FileText, ingredients: Leaf, usage: Hand, benefits: Sparkles };
    const mobileBody = (sec) =>
      sec.id === 'description' ? (
        <>
          <h3 className="pdp-card__subtitle">À propos de ce soin</h3>
          <p>{product.summary}</p>
          <p className="pdp-desc__meta"><strong>Type de peau :</strong> {product.skinTypes}</p>
        </>
      ) : sec.body;
    return (
      <section className="pdp-card" aria-label="Informations produit">
        {sections.map((sec) => (
          <Accordion key={sec.id} title={sec.title} icon={icons[sec.id]} defaultOpen={sec.id === 'description'}>
            {mobileBody(sec)}
          </Accordion>
        ))}
      </section>
    );
  }

  const current = sections.find((s) => s.id === tab);
  return (
    <section className="pdp-tabs" aria-label="Informations produit">
      <div className="pdp-tabs__list" role="tablist">
        {sections.map((s) => (
          <button key={s.id} role="tab" id={`tab-${s.id}`} aria-selected={tab === s.id} aria-controls="pdp-tabpanel" className={`pdp-tabs__tab ${tab === s.id ? 'is-active' : ''}`} onClick={() => setTab(s.id)}>
            {s.title}
          </button>
        ))}
      </div>
      <div className="pdp-tabs__panel" role="tabpanel" id="pdp-tabpanel" aria-labelledby={`tab-${tab}`}>{current.body}</div>
    </section>
  );
}
