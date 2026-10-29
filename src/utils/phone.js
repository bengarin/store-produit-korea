/** Téléphone marocain : 05/06/07 + 8 chiffres, ou +212 / 00212 → format +2126XXXXXXXX (null si invalide). */
export function normalizeMoroccanPhone(input) {
  const cleaned = (input || '').replace(/[\s.\-()]/g, '');
  const match = cleaned.match(/^(?:\+212|00212|212|0)([5-7]\d{8})$/);
  return match ? `+212${match[1]}` : null;
}
