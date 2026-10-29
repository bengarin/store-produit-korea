/** Séparateur éditorial : deux filets et la feuille du logo. */
export default function SectionDivider() {
  return (
    <div className="section-divider" aria-hidden="true">
      <span />
      <svg viewBox="0 0 40 32"><path d="M20 30 C 12 28 7 22 7 14 C 14 15 19 21 20 30 Z" /><path d="M20 30 C 28 28 33 22 33 14 C 26 15 21 21 20 30 Z" /><path d="M20 22 C 15 18 14 10 20 2 C 26 10 25 18 20 22 Z" /></svg>
      <span />
    </div>
  );
}
