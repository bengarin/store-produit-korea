import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { isArabicPath, routerBasename, storedLang, urlFor } from './i18n/langUrl.js';
import App from './App.jsx';
import { ToastProvider } from './context/ToastContext.jsx';
import './styles/global.css';
import './styles/rtl.css';

const { pathname, search } = window.location;
// Visiteur ayant déjà choisi l'arabe (avant les adresses /ar) : on garde son choix en l'envoyant sur /ar/….
// Jamais pour l'administration ni l'aperçu du thème.
const keepArabic = storedLang() === 'ar' && !isArabicPath(pathname) && !pathname.startsWith('/admin') && !search.includes('apercu-theme');

if (keepArabic) {
  window.location.replace(urlFor('ar'));
} else {
  createRoot(document.getElementById('root')).render(
    <StrictMode>
      <BrowserRouter basename={routerBasename(pathname)}>
        <ToastProvider>
          <App />
        </ToastProvider>
      </BrowserRouter>
    </StrictMode>,
  );
}
