/**
 * Description longue : liste FERMÉE de balises (identique au serveur, apps/core/html.py).
 * Le serveur nettoie déjà tout HTML enregistré ; ce filtre est une seconde barrière côté navigateur
 * (et normalise la sortie de l'éditeur : <b> → <strong>, <div> → <p>…).
 */
const ALLOWED = new Set(['P', 'BR', 'H2', 'H3', 'STRONG', 'EM', 'U', 'UL', 'OL', 'LI', 'A', 'BLOCKQUOTE']);
const RENAME = { B: 'strong', I: 'em', DIV: 'p', H1: 'h2', H4: 'h3', H5: 'h3', H6: 'h3' };
const DROP_WITH_CONTENT = new Set(['SCRIPT', 'STYLE', 'IFRAME', 'OBJECT', 'EMBED', 'TEMPLATE', 'NOSCRIPT', 'SVG', 'MATH', 'FORM']);
const SAFE_URL = /^(https?:|mailto:|\/(?!\/))/i;

function clean(node, doc) {
  const out = doc.createDocumentFragment();
  node.childNodes.forEach((child) => {
    if (child.nodeType === Node.TEXT_NODE) {
      out.appendChild(doc.createTextNode(child.textContent));
      return;
    }
    if (child.nodeType !== Node.ELEMENT_NODE || DROP_WITH_CONTENT.has(child.tagName)) return;
    const tag = RENAME[child.tagName] || (ALLOWED.has(child.tagName) ? child.tagName.toLowerCase() : null);
    const inner = clean(child, doc);
    if (!tag) {
      out.appendChild(inner); // balise inconnue : on garde seulement le texte
      return;
    }
    const el = doc.createElement(tag);
    if (tag === 'a') {
      const href = (child.getAttribute('href') || '').trim();
      if (SAFE_URL.test(href)) {
        el.setAttribute('href', href);
        el.setAttribute('rel', 'noopener noreferrer nofollow');
      }
    }
    el.appendChild(inner);
    out.appendChild(el);
  });
  return out;
}

export function sanitizeRichText(html) {
  if (!html || typeof DOMParser === 'undefined') return '';
  const doc = new DOMParser().parseFromString(`<body>${html}</body>`, 'text/html');
  const container = doc.createElement('div');
  container.appendChild(clean(doc.body, doc));
  return container.innerHTML.replace(/<p><\/p>/g, '').trim();
}
