import ThemeLink from '../theme/ThemeLink.jsx';
import { useTheme } from '../theme/ThemeContext.jsx';

/** Barre d'annonce (haut de toutes les pages). Couleurs #rrggbb validées ; texte affiché tel quel. */
export default function AnnouncementBar() {
  const { theme } = useTheme();
  const bar = theme.announcement;
  if (!bar || bar.disabled || !bar.settings.text) return null;
  const { text, link, background, color } = bar.settings;
  return (
    <div className="announcement-bar" style={{ background, color }} data-theme-section={bar.id}>
      {link ? <ThemeLink to={link} className="announcement-bar__link">{text}</ThemeLink> : <p>{text}</p>}
    </div>
  );
}
