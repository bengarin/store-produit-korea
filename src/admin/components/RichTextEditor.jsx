import { useEffect, useRef } from 'react';
import { Bold, Heading2, Heading3, Italic, Link2, List, ListOrdered, Pilcrow, RemoveFormatting } from 'lucide-react';
import { sanitizeRichText } from '../../utils/richText.js';

const TOOLS = [
  { cmd: 'bold', icon: Bold, label: 'Gras' },
  { cmd: 'italic', icon: Italic, label: 'Italique' },
  { cmd: 'formatBlock', arg: 'h2', icon: Heading2, label: 'Titre' },
  { cmd: 'formatBlock', arg: 'h3', icon: Heading3, label: 'Sous-titre' },
  { cmd: 'formatBlock', arg: 'p', icon: Pilcrow, label: 'Paragraphe' },
  { cmd: 'insertUnorderedList', icon: List, label: 'Liste à puces' },
  { cmd: 'insertOrderedList', icon: ListOrdered, label: 'Liste numérotée' },
  { cmd: 'link', icon: Link2, label: 'Lien' },
  { cmd: 'removeFormat', icon: RemoveFormatting, label: 'Effacer la mise en forme' },
];

/**
 * Texte mis en forme SANS HTML libre : seuls gras, italique, titres, listes et liens https sont possibles.
 * Ce qui est collé arrive en texte brut. Le contenu est filtré ici puis nettoyé à nouveau par le serveur.
 */
export default function RichTextEditor({ id, value, onChange, disabled, resetKey }) {
  const ref = useRef(null);
  useEffect(() => {
    if (ref.current) ref.current.innerHTML = sanitizeRichText(value || '');
    // eslint-disable-next-line react-hooks/exhaustive-deps -- recharge seulement à l'ouverture / après enregistrement
  }, [resetKey]);

  const emit = () => onChange(sanitizeRichText(ref.current.innerHTML));
  const run = (tool) => {
    ref.current.focus();
    if (tool.cmd === 'link') {
      const url = window.prompt('Adresse du lien (https://…)');
      if (!url) return;
      if (!/^(https:\/\/|mailto:)/i.test(url.trim())) {
        window.alert('Seuls les liens https:// ou mailto: sont autorisés.');
        return;
      }
      document.execCommand('createLink', false, url.trim());
    } else {
      document.execCommand(tool.cmd, false, tool.arg);
    }
    emit();
  };

  return (
    <div className={`adm-rte ${disabled ? 'is-disabled' : ''}`}>
      {!disabled && (
        <div className="adm-rte__toolbar" role="toolbar" aria-label="Mise en forme">
          {TOOLS.map((tool) => (
            <button key={tool.label} type="button" title={tool.label} aria-label={tool.label}
              onMouseDown={(e) => e.preventDefault()} onClick={() => run(tool)}>
              <tool.icon size={16} />
            </button>
          ))}
        </div>
      )}
      <div
        id={id}
        ref={ref}
        className="adm-rte__area"
        role="textbox"
        aria-multiline="true"
        contentEditable={!disabled}
        suppressContentEditableWarning
        onInput={emit}
        onBlur={emit}
        onPaste={(e) => {
          e.preventDefault();
          document.execCommand('insertText', false, e.clipboardData.getData('text/plain'));
        }}
      />
    </div>
  );
}
