import { createContext, useCallback, useContext, useRef, useState } from 'react';
import { CheckCircle2, Info } from 'lucide-react';

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toast, setToast] = useState(null);
  const timer = useRef();

  const showToast = useCallback((message, type = 'success') => {
    clearTimeout(timer.current);
    setToast({ message, type, key: Date.now() });
    timer.current = setTimeout(() => setToast(null), 2600);
  }, []);

  return (
    <ToastContext.Provider value={showToast}>
      {children}
      <div className="toast-region" role="status" aria-live="polite">
        {toast && (
          <div key={toast.key} className={`toast toast--${toast.type}`}>
            {toast.type === 'success' ? <CheckCircle2 size={18} /> : <Info size={18} />}
            <span>{toast.message}</span>
          </div>
        )}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);
