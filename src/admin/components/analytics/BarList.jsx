/**
 * Répartition en barres horizontales (une seule couleur : la longueur porte la valeur).
 * Chaque ligne affiche son libellé, sa valeur et sa part : l'information n'est jamais portée par la couleur seule.
 * rows = [{ key, label, value, display, share?, detail? }]
 */
export default function BarList({ rows, label, empty = 'Aucune donnée sur la période.' }) {
  const max = Math.max(0, ...rows.map((r) => r.value));
  if (!rows.length || max <= 0) return <p className="adm-muted adm-barlist__empty">{empty}</p>;
  return (
    <ul className="adm-barlist" aria-label={label}>
      {rows.map((r) => (
        <li key={r.key} className="adm-barlist__row" title={`${r.label} : ${r.display}${r.share != null ? ` (${formatShare(r.share)})` : ''}`}>
          <div className="adm-barlist__text">
            <span className="adm-barlist__label">{r.label}</span>
            <span className="adm-barlist__value">
              {r.display}
              {r.share != null && <small> · {formatShare(r.share)}</small>}
            </span>
          </div>
          <div className="adm-barlist__track" aria-hidden="true">
            <div className="adm-barlist__bar" style={{ width: `${r.value > 0 ? Math.max(2, (r.value / max) * 100) : 0}%` }} />
          </div>
          {r.detail && <span className="adm-barlist__detail">{r.detail}</span>}
        </li>
      ))}
    </ul>
  );
}

export const formatShare = (value) => (value == null ? '—' : `${value.toLocaleString('fr-FR', { maximumFractionDigits: 1 })} %`);
