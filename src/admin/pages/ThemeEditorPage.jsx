import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle, ArrowDown, ArrowLeft, ArrowUp, CheckCircle2, Eye, EyeOff, GripVertical, History, LayoutTemplate, Monitor, Palette, PanelBottom, PanelTop,
  Plus, RefreshCw, Rocket, Save, Smartphone, Trash2,
} from 'lucide-react';
import { admin } from '../api.js';
import { useAuth } from '../auth.jsx';
import { can, homePath } from '../permissions.js';
import { SCHEMA, newItem, newSection, validateTheme } from '../../theme/validate.js';
import { PREVIEW_MESSAGE } from '../../theme/ThemeContext.jsx';
import { Badge, Button, ErrorState, Modal, Notice, PageLoader } from '../components/ui.jsx';
import ConfirmDialog from '../components/ConfirmDialog.jsx';
import { FieldList, ItemsEditor } from '../components/theme/Fields.jsx';
import MediaPicker from '../components/theme/MediaPicker.jsx';
import ThemeHistory from '../components/theme/ThemeHistory.jsx';
import { useTitle } from '../hooks.js';
import { formatDate } from '../format.js';

const PREVIEW_URL = '/?apercu-theme=1';
const DESKTOP_WIDTH = 1280;
const AREA_KEYS = ['announcement', 'header', 'footer'];
const SETTINGS_GROUPS = [...new Set(SCHEMA.settings.map((f) => f.group))];

/** Libellé d'une section dans la liste : son type + son titre s'il y en a un. */
function sectionLabel(section) {
  const def = SCHEMA.sections[section.type];
  const title = section.settings?.heading || section.settings?.text;
  return { name: def?.name || section.type, detail: title && title !== def?.name ? title : '' };
}

function uniqueId(type, theme) {
  const used = new Set([...theme.home.map((s) => s.id), ...AREA_KEYS]);
  const base = type.replace(/_/g, '-').slice(0, 30);
  for (let i = 1; ; i += 1) if (!used.has(`${base}-${i}`)) return `${base}-${i}`;
}

/** Erreurs { chemin: message } : validation locale (immédiate) puis réponse du serveur. */
const toErrorMap = (list) => Object.fromEntries(list.map((e) => [e.path, e.message]));

export default function ThemeEditorPage() {
  useTitle('Thème');
  const { user } = useAuth();
  const canEdit = can(user, 'editTheme');
  const canPublish = can(user, 'publishTheme');
  const [server, setServer] = useState(null); // dernier état connu du serveur
  const [theme, setTheme] = useState(null); // copie de travail
  const [media, setMedia] = useState({});
  const [loadError, setLoadError] = useState(null);
  const [selected, setSelected] = useState('settings');
  // Petit écran : l'aperçu démarre en mode mobile.
  const [device, setDevice] = useState(() => (window.innerWidth < 700 ? 'mobile' : 'desktop'));
  const [panel, setPanel] = useState('preview'); // affichage mobile de l'éditeur : sections | preview | settings
  const [busy, setBusy] = useState('');
  const [serverErrors, setServerErrors] = useState({});
  const [notice, setNotice] = useState(null);
  const [dialog, setDialog] = useState(null); // add | delete | publish | history | media
  const [note, setNote] = useState('');
  const [previewVersion, setPreviewVersion] = useState(null); // { number, data, media } : aperçu d'une ancienne version
  const [ctxData, setCtxData] = useState({ products: [], categories: [] });
  const pickRef = useRef(null);
  const frameRef = useRef(null);
  const stageRef = useRef(null);
  const [stageWidth, setStageWidth] = useState(800);
  const dragFrom = useRef(null);

  const applyServer = useCallback((state) => {
    setServer(state);
    setTheme(state.draft.data);
    setMedia(state.media || {});
    setServerErrors({});
  }, []);

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      applyServer(await admin.get('/theme'));
    } catch (e) {
      setLoadError(e);
    }
  }, [applyServer]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    // Produits et catégories : listes de choix des champs « produit » et « catégorie ».
    Promise.all([admin.get('/products', { page_size: 100, ordering: 'position' }), admin.get('/categories')])
      .then(([p, c]) => setCtxData({
        products: p.items.map((x) => ({ slug: x.slug, name: x.displayName, status: x.status })),
        categories: (c.items || c).map((x) => ({ slug: x.slug, name: x.name })),
      }))
      .catch(() => {});
  }, []);

  const local = useMemo(() => (theme ? validateTheme(theme) : { ok: true, errors: [] }), [theme]);
  const errors = useMemo(() => ({ ...serverErrors, ...toErrorMap(local.errors) }), [serverErrors, local]);
  const unsaved = Boolean(server && theme && JSON.stringify(theme) !== JSON.stringify(server.draft.data));

  // Quitter la page avec des modifications non enregistrées : avertissement du navigateur.
  useEffect(() => {
    if (!unsaved) return undefined;
    const warn = (e) => { e.preventDefault(); e.returnValue = ''; };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [unsaved]);

  // --- Aperçu : la VRAIE boutique dans une iframe (même origine), brouillon envoyé par postMessage ---
  const shown = previewVersion ? previewVersion.data : theme;
  const shownMedia = previewVersion ? previewVersion.media : media;
  const post = useCallback(() => {
    const win = frameRef.current?.contentWindow;
    if (win && shown) win.postMessage({ type: PREVIEW_MESSAGE, theme: shown, media: shownMedia }, window.location.origin);
  }, [shown, shownMedia]);
  useEffect(() => {
    const t = setTimeout(post, 120);
    return () => clearTimeout(t);
  }, [post]);
  useEffect(() => {
    const onMessage = (e) => {
      if (e.origin !== window.location.origin || e.source !== frameRef.current?.contentWindow) return;
      if (e.data?.type === `${PREVIEW_MESSAGE}:ready`) post();
      if (e.data?.type === `${PREVIEW_MESSAGE}:select` && typeof e.data.id === 'string') {
        setSelected(e.data.id);
        setPanel('settings');
      }
    };
    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, [post]);
  useEffect(() => {
    const el = stageRef.current;
    if (!el) return undefined;
    const ro = new ResizeObserver(([entry]) => setStageWidth(entry.contentRect.width));
    ro.observe(el);
    return () => ro.disconnect();
  }, [server]);

  if (loadError) return <div className="adm-center"><ErrorState error={loadError} onRetry={load} /></div>;
  if (!theme) return <PageLoader label="Chargement du thème…" />;

  // --- Modifications de la copie de travail ---
  const update = (fn) => { setTheme((t) => fn(structuredClone(t))); setNotice(null); };
  const findSection = (t, id) => (AREA_KEYS.includes(id) ? t[id] : t.home.find((s) => s.id === id));
  const setSection = (id, next) => update((t) => {
    if (AREA_KEYS.includes(id)) t[id] = next;
    else t.home = t.home.map((s) => (s.id === id ? next : s));
    return t;
  });
  const moveHome = (from, to) => update((t) => {
    if (to < 0 || to >= t.home.length) return t;
    const [s] = t.home.splice(from, 1);
    t.home.splice(to, 0, s);
    return t;
  });
  const toggle = (id) => update((t) => {
    const s = findSection(t, id);
    s.disabled = !s.disabled;
    return t;
  });
  const addSection = (type) => {
    const id = uniqueId(type, theme);
    update((t) => { t.home.push(newSection(type, id)); return t; });
    setSelected(id);
    setDialog(null);
    setPanel('settings');
  };
  const deleteSection = (id) => {
    update((t) => { t.home = t.home.filter((s) => s.id !== id); return t; });
    setSelected('settings');
    setDialog(null);
  };

  // --- Serveur : enregistrer, publier, charger/restaurer une version ---
  const handleError = (e) => {
    if (e.status === 409) setNotice({ tone: 'danger', text: e.message, reload: e.code === 'draft_conflict' });
    else if (e.status === 400 && e.fields) {
      setServerErrors(Object.fromEntries(Object.entries(e.fields).map(([k, v]) => [k, v[0]])));
      setNotice({ tone: 'danger', text: 'Certaines valeurs sont refusées : corrigez les champs signalés.' });
    } else setNotice({ tone: 'danger', text: e.message });
  };
  const save = async () => {
    if (!local.ok) {
      setNotice({ tone: 'danger', text: `${local.errors.length} valeur(s) à corriger avant d’enregistrer.` });
      return false;
    }
    setBusy('save');
    try {
      applyServer(await admin.put('/theme/draft', { data: theme, revision: server.draft.revision }));
      setNotice({ tone: 'success', text: 'Brouillon enregistré. La boutique publique n’a pas changé.' });
      return true;
    } catch (e) {
      handleError(e);
      return false;
    } finally {
      setBusy('');
    }
  };
  const publish = async () => {
    setBusy('publish');
    try {
      const r = await admin.post('/theme/publish', { revision: server.draft.revision, note });
      applyServer(r);
      setDialog(null);
      setNote('');
      setNotice({ tone: 'success', text: `Version ${r.publishedNumber} publiée : la boutique affiche maintenant ce thème.` });
    } catch (e) {
      setDialog(null);
      handleError(e);
    } finally {
      setBusy('');
    }
  };
  const afterHistory = (state, text) => {
    applyServer(state);
    setPreviewVersion(null);
    setDialog(null);
    setNotice({ tone: 'success', text });
  };

  const selectedSection = selected === 'settings' ? null : findSection(theme, selected);
  const def = selectedSection ? SCHEMA.sections[selectedSection.type] : null;
  const prefix = selectedSection ? (AREA_KEYS.includes(selected) ? selected : `home.${theme.home.indexOf(selectedSection)}`) : 'settings';
  const readOnly = !canEdit || Boolean(previewVersion);
  const counts = theme.home.reduce((acc, s) => ({ ...acc, [s.type]: (acc[s.type] || 0) + 1 }), {});
  const addable = Object.entries(SCHEMA.sections).filter(([, d]) => d.area === 'home');
  const links = [
    { value: '/', label: 'Accueil', kind: 'internal' },
    { value: '/produits', label: 'Tous les produits', kind: 'internal' },
    { value: '/produits?favoris=1', label: 'Favoris', kind: 'internal' },
    { value: '/panier', label: 'Panier', kind: 'internal' },
    ...ctxData.categories.map((c) => ({ value: `/produits?categorie=${c.slug}`, label: `Catégorie : ${c.name}`, kind: 'internal' })),
    ...theme.home.filter((s) => s.type === 'product_collection').map((s) => ({ value: `#${s.id}`, label: `Ancre : ${s.settings.heading}`, kind: 'anchor' })),
  ];
  const ctx = {
    ...ctxData, media, links,
    pickImage: (cb) => { pickRef.current = cb; setDialog('media'); },
  };
  const errorCount = Object.keys(errors).length;
  const status = previewVersion
    ? <Badge tone="info">Aperçu de la version {previewVersion.number}</Badge>
    : unsaved ? <Badge tone="warning">Modifications non enregistrées</Badge>
      : server.dirty ? <Badge tone="neutral">Brouillon enregistré · non publié</Badge>
        : <Badge tone="success">{server.published ? `Publié · version ${server.published.number}` : 'Thème d’origine'}</Badge>;
  const scale = device === 'desktop' ? Math.min(1, (stageWidth - 24) / DESKTOP_WIDTH) : 1;

  const sectionRow = (id, icon, extra) => {
    const s = findSection(theme, id);
    const { name, detail } = sectionLabel(s);
    const Icon = icon;
    return (
      <div className={`adm-theme-row ${selected === id ? 'is-selected' : ''} ${s.disabled ? 'is-hidden' : ''}`} {...extra}>
        {extra?.draggable ? <span className="adm-theme-row__grip" aria-hidden="true"><GripVertical size={15} /></span> : <span className="adm-theme-row__grip" aria-hidden="true"><Icon size={15} /></span>}
        <button type="button" className="adm-theme-row__main" onClick={() => { setSelected(id); setPanel('settings'); }} aria-current={selected === id}>
          <strong>{name}</strong>{detail && <span>{detail}</span>}
        </button>
        {id !== 'header' && id !== 'footer' && (
          <button type="button" className="adm-icon-btn" disabled={readOnly} onClick={() => toggle(id)}
            aria-label={s.disabled ? `Afficher : ${name}` : `Masquer : ${name}`} title={s.disabled ? 'Afficher' : 'Masquer'}>
            {s.disabled ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        )}
      </div>
    );
  };

  return (
    <div className={`adm-theme adm-theme--${panel}`}>
      <header className="adm-theme__bar">
        <Link to={homePath(user)} className="adm-theme__back" onClick={(e) => { if (unsaved && !window.confirm('Quitter sans enregistrer vos modifications ?')) e.preventDefault(); }}>
          <ArrowLeft size={16} aria-hidden="true" /> Quitter
        </Link>
        <div className="adm-theme__title">
          <strong>Thème de la boutique</strong>
          {status}
        </div>
        <div className="adm-segmented adm-segmented--sm" role="group" aria-label="Appareil de l’aperçu">
          <button type="button" className={device === 'desktop' ? 'is-active' : ''} aria-pressed={device === 'desktop'} onClick={() => setDevice('desktop')}><Monitor size={14} aria-hidden="true" /> Ordinateur</button>
          <button type="button" className={device === 'mobile' ? 'is-active' : ''} aria-pressed={device === 'mobile'} onClick={() => setDevice('mobile')}><Smartphone size={14} aria-hidden="true" /> Mobile</button>
        </div>
        <div className="adm-theme__actions">
          <Button size="sm" variant="ghost" icon={History} onClick={() => setDialog('history')}>Historique</Button>
          {canEdit && <Button size="sm" variant="secondary" icon={Save} loading={busy === 'save'} disabled={!unsaved || Boolean(previewVersion)} onClick={save}>Enregistrer</Button>}
          {canPublish && (
            <Button size="sm" icon={Rocket} disabled={unsaved || !server.dirty || Boolean(previewVersion) || errorCount > 0}
              title={unsaved ? 'Enregistrez d’abord le brouillon' : !server.dirty ? 'Rien de nouveau à publier' : undefined}
              onClick={() => setDialog('publish')}>Publier</Button>
          )}
        </div>
      </header>

      <div className="adm-theme__tabs" role="tablist" aria-label="Panneaux">
        {[['sections', 'Sections'], ['preview', 'Aperçu'], ['settings', 'Réglages']].map(([id, label]) => (
          <button key={id} type="button" role="tab" aria-selected={panel === id} className={panel === id ? 'is-active' : ''} onClick={() => setPanel(id)}>{label}</button>
        ))}
      </div>

      {(notice || previewVersion || !canEdit) && (
        <div className="adm-theme__notices">
          {!canEdit && <Notice tone="info">Lecture seule : votre rôle permet de consulter le thème, pas de le modifier.</Notice>}
          {previewVersion && (
            <Notice tone="info" action={<Button size="sm" variant="secondary" onClick={() => setPreviewVersion(null)}>Revenir au brouillon</Button>}>
              Aperçu de la version {previewVersion.number} (lecture seule). Rien n’est modifié.
            </Notice>
          )}
          {notice && (
            <Notice tone={notice.tone} icon={notice.tone === 'success' ? CheckCircle2 : AlertTriangle} action={notice.reload && <Button size="sm" variant="secondary" icon={RefreshCw} onClick={load}>Recharger le brouillon</Button>}>
              {notice.text}
            </Notice>
          )}
        </div>
      )}

      <div className="adm-theme__body">
        {/* Gauche : sections */}
        <aside className="adm-theme__sections" aria-label="Sections">
          <button type="button" className={`adm-theme-row adm-theme-row--global ${selected === 'settings' ? 'is-selected' : ''}`} onClick={() => { setSelected('settings'); setPanel('settings'); }}>
            <Palette size={16} aria-hidden="true" /> <strong>Réglages du thème</strong>
            <span>Couleurs, polices, boutons, mise en page</span>
          </button>
          <p className="adm-theme__group">En-tête (toutes les pages)</p>
          {sectionRow('announcement', PanelTop)}
          {sectionRow('header', PanelTop)}
          <p className="adm-theme__group">Page d’accueil</p>
          <ol className="adm-theme__list">
            {theme.home.map((s, i) => (
              <li key={s.id}
                onDragOver={(e) => { if (dragFrom.current != null) e.preventDefault(); }}
                onDrop={(e) => { e.preventDefault(); if (dragFrom.current != null) moveHome(dragFrom.current, i); dragFrom.current = null; }}>
                {sectionRow(s.id, LayoutTemplate, readOnly ? {} : {
                  draggable: true,
                  onDragStart: (e) => { dragFrom.current = i; e.dataTransfer.effectAllowed = 'move'; e.dataTransfer.setData('text/plain', s.id); },
                  onDragEnd: () => { dragFrom.current = null; },
                })}
                {!readOnly && (
                  <div className="adm-theme-row__order">
                    <button type="button" aria-label={`Monter : ${sectionLabel(s).name}`} disabled={i === 0} onClick={() => moveHome(i, i - 1)}><ArrowUp size={13} /></button>
                    <button type="button" aria-label={`Descendre : ${sectionLabel(s).name}`} disabled={i === theme.home.length - 1} onClick={() => moveHome(i, i + 1)}><ArrowDown size={13} /></button>
                  </div>
                )}
              </li>
            ))}
          </ol>
          {!readOnly && <Button size="sm" variant="secondary" icon={Plus} onClick={() => setDialog('add')} disabled={theme.home.length >= SCHEMA.limits.maxHomeSections}>Ajouter une section</Button>}
          <p className="adm-theme__group">Pied de page (toutes les pages)</p>
          {sectionRow('footer', PanelBottom)}
          {server.draft.updatedBy && (
            <p className="adm-footnote adm-mt">Brouillon enregistré le {formatDate(server.draft.updatedAt)} par {server.draft.updatedBy.name}.</p>
          )}
        </aside>

        {/* Centre : aperçu */}
        <section className="adm-theme__stage" ref={stageRef} aria-label="Aperçu de la boutique">
          <div className={`adm-theme__frame adm-theme__frame--${device}`}
            style={device === 'desktop' ? {
              width: DESKTOP_WIDTH, height: `${100 / scale}%`, transform: `scale(${scale})`,
              marginLeft: Math.max(0, (stageWidth - 24 - DESKTOP_WIDTH * scale) / 2),
            } : undefined}>
            <iframe ref={frameRef} title="Aperçu du thème" src={PREVIEW_URL} onLoad={post} />
          </div>
        </section>

        {/* Droite : réglages de la sélection */}
        <aside className="adm-theme__panel" aria-label="Réglages">
          {selected === 'settings' || !selectedSection ? (
            <>
              <h2 className="adm-theme__panel-title">Réglages du thème</h2>
              <p className="adm-muted adm-theme__panel-desc">S’appliquent à toute la boutique. Les valeurs d’origine gardent l’identité actuelle (crème, vert forêt, Cormorant Garamond).</p>
              {SETTINGS_GROUPS.map((group) => (
                <fieldset key={group} className="adm-theme__fieldset">
                  <legend>{group}</legend>
                  <FieldList fields={SCHEMA.settings.filter((f) => f.group === group)} values={(previewVersion ? shown : theme).settings} errors={errors}
                    prefix="settings" disabled={readOnly} ctx={ctx} onChange={(v) => update((t) => { t.settings = v; return t; })} />
                </fieldset>
              ))}
            </>
          ) : (
            <>
              <h2 className="adm-theme__panel-title">{def.name}</h2>
              <p className="adm-muted adm-theme__panel-desc">{def.description}</p>
              {selectedSection.type === 'testimonials' && (
                <Notice tone="warning">Uniquement de vrais avis de clientes et clients, recopiés tels quels, avec leur accord. N’inventez jamais d’avis.</Notice>
              )}
              {selectedSection.type === 'newsletter' && (
                <Notice tone="info">Les inscriptions sont enregistrées (Réglages → Newsletter). Aucun e-mail n’est envoyé par le site : exportez la liste vers votre outil d’e-mailing.</Notice>
              )}
              <FieldList fields={def.settings} values={selectedSection.settings} errors={errors} prefix={`${prefix}.settings`} disabled={readOnly} ctx={ctx}
                onChange={(v) => setSection(selected, { ...selectedSection, settings: v })} />
              {def.items && (
                <ItemsEditor def={def.items} items={selectedSection.items || []} errors={errors} prefix={`${prefix}.items`} disabled={readOnly} ctx={ctx}
                  newItem={() => newItem(selectedSection.type)} onChange={(items) => setSection(selected, { ...selectedSection, items })} />
              )}
              {!readOnly && !AREA_KEYS.includes(selected) && (
                <Button variant="danger-ghost" icon={Trash2} className="adm-mt" onClick={() => setDialog('delete')}>Supprimer la section</Button>
              )}
            </>
          )}
        </aside>
      </div>

      {dialog === 'add' && (
        <Modal open size="lg" title="Ajouter une section" onClose={() => setDialog(null)}>
          <ul className="adm-theme-add">
            {addable.map(([type, d]) => {
              const full = d.max && (counts[type] || 0) >= d.max;
              return (
                <li key={type}>
                  <button type="button" disabled={full} onClick={() => addSection(type)}>
                    <strong>{d.name}</strong>
                    <span>{full ? `Déjà présente (${d.max} maximum)` : d.description}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </Modal>
      )}
      {dialog === 'delete' && selectedSection && (
        <ConfirmDialog title="Supprimer cette section ?" confirmLabel="Supprimer" danger onClose={() => setDialog(null)} onConfirm={() => deleteSection(selected)}>
          <p><strong>{sectionLabel(selectedSection).name}</strong> sera retirée du brouillon. La boutique publique ne change qu’à la prochaine publication ; vous pouvez aussi simplement la masquer (icône œil).</p>
        </ConfirmDialog>
      )}
      {dialog === 'publish' && (
        <ConfirmDialog title="Publier le thème ?" confirmLabel="Publier maintenant" onClose={() => setDialog(null)} onConfirm={publish}>
          <p>Le brouillon enregistré (révision {server.draft.revision}) remplacera le thème visible par les clients{server.published ? ` (version ${server.published.number})` : ''}. La version actuelle reste dans l’historique et pourra être restaurée.</p>
          <label className="adm-field adm-mt">
            <span className="adm-field__label">Note de version (facultatif)</span>
            <input className="adm-input" maxLength={200} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Ex. Bannière de la fête des mères" />
          </label>
        </ConfirmDialog>
      )}
      {dialog === 'history' && (
        <ThemeHistory server={server} canEdit={canEdit} canPublish={canPublish} unsaved={unsaved}
          onClose={() => setDialog(null)}
          onPreview={(v) => { setPreviewVersion(v); setDialog(null); setPanel('preview'); }}
          onDone={afterHistory} onError={(e) => { setDialog(null); handleError(e); }} />
      )}
      {dialog === 'media' && (
        <MediaPicker canUpload={canEdit} onClose={() => setDialog(null)}
          onPick={(m) => {
            setMedia((prev) => ({ ...prev, [m.id]: { src: m.url, src640: m.url640, width: m.width, height: m.height, alt: m.alt } }));
            pickRef.current?.(m);
            setDialog(null);
          }} />
      )}
    </div>
  );
}
