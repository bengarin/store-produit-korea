import { useEffect, useMemo, useRef, useState } from 'react';
import { formatInt, formatMoney } from '../../format.js';

const HEIGHT = 230;
const PAD = { top: 12, right: 8, bottom: 26, left: 52 };
const UTC = { timeZone: 'UTC' };
const dayFmt = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'short', ...UTC });
const monthFmt = new Intl.DateTimeFormat('fr-FR', { month: 'short', year: 'numeric', ...UTC });
const longFmt = new Intl.DateTimeFormat('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', ...UTC });
const fullFmt = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'long', year: 'numeric', ...UTC });
const compact = new Intl.NumberFormat('fr-FR', { notation: 'compact', maximumFractionDigits: 1 });

/** Indicateurs proposés (une seule série à la fois : jamais deux échelles sur un même graphique). */
export const METRICS = {
  revenue: { label: 'CA encaissé', format: formatMoney, hint: 'Commandes livrées, au jour de livraison' },
  grossSales: { label: 'Ventes commandées', format: formatMoney, hint: 'Commandes valides, au jour de commande' },
  orders: { label: 'Commandes', format: formatInt, hint: 'Toutes les commandes passées, au jour de commande' },
};

const date = (iso) => new Date(`${iso}T00:00:00Z`);

function niceMax(value) {
  if (value <= 0) return 4;
  const exp = 10 ** Math.floor(Math.log10(value));
  const step = [1, 2, 2.5, 5, 10].find((m) => m * exp >= value / 4) * exp;
  return Math.ceil(value / step) * step;
}

/** Barre à extrémité arrondie (4 px) et base carrée, posée sur la ligne de base. */
function barPath(x, y, w, h) {
  const r = Math.min(4, w / 2, h);
  return `M${x},${y + h} V${y + r} Q${x},${y} ${x + r},${y} H${x + w - r} Q${x + w},${y} ${x + w},${y + r} V${y + h} Z`;
}

/** Libellés d'un intervalle selon le découpage (jour, semaine lundi → dimanche, mois). */
export function bucketLabel(b, granularity, long = false) {
  if (granularity === 'day') return long ? longFmt.format(date(b.start)) : dayFmt.format(date(b.start));
  if (granularity === 'month') return long ? `${fullFmt.format(date(b.start))} → ${fullFmt.format(date(b.end))}` : monthFmt.format(date(b.start));
  return long ? `Semaine du ${dayFmt.format(date(b.start))} au ${dayFmt.format(date(b.end))}` : dayFmt.format(date(b.start));
}

/**
 * Évolution sur la période : une série (titre = nom), survol et clavier = détail, tableau disponible.
 */
export default function TimeChart({ series, metric, granularity }) {
  const wrapRef = useRef(null);
  const [width, setWidth] = useState(640);
  const [active, setActive] = useState(null);
  const [showTable, setShowTable] = useState(false);
  const m = METRICS[metric];

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return undefined;
    const ro = new ResizeObserver(([entry]) => setWidth(Math.max(260, entry.contentRect.width)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const { max, ticks } = useMemo(() => {
    const top = niceMax(Math.max(0, ...series.map((d) => d[metric])));
    return { max: top, ticks: [0, top / 4, top / 2, (3 * top) / 4, top] };
  }, [series, metric]);

  const plotW = width - PAD.left - PAD.right;
  const plotH = HEIGHT - PAD.top - PAD.bottom;
  const band = plotW / Math.max(series.length, 1);
  const barW = Math.max(2, Math.min(28, band - 2)); // 2 px d'air minimum entre deux barres
  const labelEvery = Math.ceil(series.length / Math.max(2, Math.floor(plotW / 64)));
  const y = (v) => PAD.top + plotH - (v / max) * plotH;
  const hasData = series.some((d) => d[metric] > 0);
  const current = active != null ? series[active] : null;
  const fmtTick = metric === 'orders' ? (t) => formatInt(t) : (t) => compact.format(t);

  return (
    <div className="adm-chart">
      <div className="adm-chart__plot" ref={wrapRef} onMouseLeave={() => setActive(null)}>
        <svg width={width} height={HEIGHT} role="img" aria-label={`${m.label} sur la période`}>
          {ticks.map((t) => (
            <g key={t}>
              <line x1={PAD.left} x2={width - PAD.right} y1={y(t)} y2={y(t)} className="adm-chart__grid" />
              <text x={PAD.left - 8} y={y(t)} className="adm-chart__axis" textAnchor="end" dominantBaseline="middle">
                {Number.isInteger(t) || metric !== 'orders' ? fmtTick(t) : ''}
              </text>
            </g>
          ))}
          {series.map((d, i) => {
            const x = PAD.left + i * band;
            const h = Math.max(0, y(0) - y(d[metric]));
            return (
              <g key={d.start}>
                {h > 0 && (
                  <path d={barPath(x + (band - barW) / 2, y(d[metric]), barW, h)}
                    className={`adm-chart__bar ${active === i ? 'is-active' : ''}`} />
                )}
                {i % labelEvery === 0 && (
                  <text x={x + band / 2} y={HEIGHT - 8} className="adm-chart__axis" textAnchor="middle">{bucketLabel(d, granularity)}</text>
                )}
                {/* Zone de survol plus large que la barre */}
                <rect x={x} y={PAD.top} width={band} height={plotH} className="adm-chart__hit" tabIndex={0}
                  aria-label={`${bucketLabel(d, granularity, true)} : ${m.format(d[metric])}`}
                  onMouseEnter={() => setActive(i)} onFocus={() => setActive(i)} onBlur={() => setActive(null)} />
              </g>
            );
          })}
        </svg>
        {!hasData && <p className="adm-chart__empty">Aucune donnée sur la période.</p>}
        {current && (
          <div className="adm-chart__tip" style={{ left: Math.min(Math.max(PAD.left + active * band + band / 2, 100), width - 100) }}>
            <strong>{bucketLabel(current, granularity, true)}</strong>
            <span>Encaissé : {formatMoney(current.revenue)}</span>
            <span>Ventes commandées : {formatMoney(current.grossSales)}</span>
            <span>Commandes : {formatInt(current.orders)}</span>
          </div>
        )}
      </div>
      <button type="button" className="adm-link-btn" onClick={() => setShowTable((v) => !v)} aria-expanded={showTable}>
        {showTable ? 'Masquer le tableau' : 'Voir les chiffres en tableau'}
      </button>
      {showTable && (
        <div className="adm-table-wrap">
          <table className="adm-table adm-table--compact">
            <thead><tr><th>Période</th><th className="num">Commandes</th><th className="num">Ventes commandées</th><th className="num">Encaissé</th></tr></thead>
            <tbody>
              {series.map((d) => (
                <tr key={d.start}>
                  <td>{bucketLabel(d, granularity, true)}</td>
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
