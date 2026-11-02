import ThemeLink from '../theme/ThemeLink.jsx';
import { useTheme } from '../theme/ThemeContext.jsx';
import { useI18n } from '../i18n/I18nContext.jsx';

/** Barre d'annonce (haut de toutes les pages). Couleurs #rrggbb validées ; texte affiché tel quel. */
export default function AnnouncementBar() {
  const { theme } = useTheme();
  const { tc } = useI18n();
  const bar = theme.announcement;
  if (!bar || bar.disabled || !bar.settings.text) return null;
  const { link, background, color } = bar.settings;
  const text = tc(bar.settings.text);
  return (
    <div className="announcement-bar" style={{ background, color }} data-theme-section={bar.id}>
      {link ? <ThemeLink to={link} className="announcement-bar__link">{text}</ThemeLink> : <p>{text}</p>}
    </div>
  );
}
