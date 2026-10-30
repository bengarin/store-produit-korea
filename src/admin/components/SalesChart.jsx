import { useEffect, useMemo, useRef, useState } from 'react';
import { formatInt, formatMoney } from '../format.js';

const HEIGHT = 220;
const PAD = { top: 12, right: 8, bottom: 26, left: 52 };
const dayFmt = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'short', timeZone: 'UTC' });
const longFmt = new Intl.DateTimeFormat('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', timeZone: 'UTC' });
const shortMoney = new Intl.NumberFormat('fr-FR', { notation: 'compact', maximumFractionDigits: 1 });

function niceMax(value) {
  if (value <= 0) return 100;
  const exp = 10 ** Math.floor(Math.log10(value));
  const step = [1, 2, 2.5, 5, 10].find((m) => m * exp >= value / 4) * exp;
  return Math.ceil(value / step) * step;
}

/** Barre à extrémité arrondie (4 px) et base carrée, posée sur la ligne de base. */
function barPath(x, y, w, h) {
  const r = Math.min(4, w / 2, h);
  return `M${x},${y + h} V${y + r} Q${x},${y} ${x + r},${y} H${x + w - r} Q${x + w},${y} ${x + w},${y + r} V${y + h} Z`;
}

/**
 * Ventes par jour (valeur des commandes hors annulées/retournées). Une seule série : pas de légende,
 * le titre de la carte la nomme. Survol/clavier : détail du jour. Tableau disponible.
 */
export default function SalesChart({ series }) {
  const wrapRef = useRef(null);
  const [width, setWidth] = useState(640);
  const [active, setActive] = useState(null);
  const [showTable, setShowTable] = useState(false);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return undefined;
    const ro = new ResizeObserver(([entry]) => setWidth(Math.max(280, entry.contentRect.width)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const { max, ticks } = useMemo(() => {
    const top = niceMax(Math.max(0, ...series.map((d) => d.grossSales)));
    return { max: top, ticks: [0, top / 4, top / 2, (3 * top) / 4, top] };
  }, [series]);

  const plotW = width - PAD.left - PAD.right;
  const plotH = HEIGHT - PAD.top - PAD.bottom;
  const band = plotW / Math.max(series.length, 1);
  const barW = Math.max(2, Math.min(24, band - 2)); // 2 px d'air minimum entre deux barres
  const labelEvery = Math.ceil(series.length / Math.max(2, Math.floor(plotW / 64)));
  const y = (v) => PAD.top + plotH - (v / max) * plotH;
  const hasData = series.some((d) => d.orders > 0);
  const current = active != null ? series[active] : null;

  return (
    <div className="adm-chart">
      <div className="adm-chart__plot" ref={wrapRef} onMouseLeave={() => setActive(null)}>
        <svg width={width} height={HEIGHT} role="img" aria-label="Ventes par jour sur la période">
          {ticks.map((t) => (
            <g key={t}>
              <line x1={PAD.left} x2={width - PAD.right} y1={y(t)} y2={y(t)} className="adm-chart__grid" />
              <text x={PAD.left - 8} y={y(t)} className="adm-chart__axis" textAnchor="end" dominantBaseline="middle">
                {shortMoney.format(t)}
              </text>
            </g>
          ))}
          {series.map((d, i) => {
            const x = PAD.left + i * band;
            const h = Math.max(0, y(0) - y(d.grossSales));
            const date = new Date(`${d.date}T00:00:00Z`);
            return (
              <g key={d.date}>
                {h > 0 && (
                  <path d={barPath(x + (band - barW) / 2, y(d.grossSales), barW, h)}
                    className={`adm-chart__bar ${active === i ? 'is-active' : ''}`} />
                )}
                {i % labelEvery === 0 && (
                  <text x={x + band / 2} y={HEIGHT - 8} className="adm-chart__axis" textAnchor="middle">{dayFmt.format(date)}</text>
                )}
                {/* Zone de survol plus large que la barre */}
                <rect x={x} y={PAD.top} width={band} height={plotH} className="adm-chart__hit" tabIndex={0}
                  aria-label={`${longFmt.format(date)} : ${formatMoney(d.grossSales)}, ${d.orders} commande(s)`}
                  onMouseEnter={() => setActive(i)} onFocus={() => setActive(i)} onBlur={() => setActive(null)} />
              </g>
            );
          })}
        </svg>
        {!hasData && <p className="adm-chart__empty">Aucune commande sur la période.</p>}
        {current && (
          <div className="adm-chart__tip" style={{ left: Math.min(Math.max(PAD.left + active * band + band / 2, 90), width - 90) }}>
            <strong>{longFmt.format(new Date(`${current.date}T00:00:00Z`))}</strong>
            <span>Ventes : {formatMoney(current.grossSales)}</span>
            <span>Commandes : {formatInt(current.orders)}</span>
            <span>Encaissé : {formatMoney(current.revenue)}</span>
          </div>
        )}
      </div>
      <button type="button" className="adm-link-btn" onClick={() => setShowTable((v) => !v)} aria-expanded={showTable}>
        {showTable ? 'Masquer le tableau' : 'Voir les chiffres en tableau'}
      </button>
      {showTable && (
        <div className="adm-table-wrap">
          <table className="adm-table adm-table--compact">
            <thead><tr><th>Jour</th><th className="num">Commandes</th><th className="num">Ventes</th><th className="num">Encaissé</th></tr></thead>
            <tbody>
              {series.filter((d) => d.orders > 0).map((d) => (
                <tr key={d.date}>
                  <td>{longFmt.format(new Date(`${d.date}T00:00:00Z`))}</td>
                  <td className="num">{formatInt(d.orders)}</td>
                  <td className="num">{formatMoney(d.grossSales)}</td>
                  <td className="num">{formatMoney(d.revenue)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
