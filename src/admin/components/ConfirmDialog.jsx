import { useState } from 'react';
import { Button, Modal, Notice } from './ui.jsx';

/** Confirmation d'une action (suppression, archivage…). `onConfirm` peut être asynchrone. */
export default function ConfirmDialog({ title, children, confirmLabel = 'Confirmer', danger = false, onConfirm, onClose }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const confirm = async () => {
    setBusy(true);
    setError('');
    try {
      await onConfirm();
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };
  return (
    <Modal open title={title} onClose={busy ? undefined : onClose}
      footer={(
        <>
          <Button variant="secondary" onClick={onClose} disabled={busy}>Annuler</Button>
          <Button variant={danger ? 'danger' : 'primary'} loading={busy} onClick={confirm}>{confirmLabel}</Button>
        </>
      )}>
      {children}
      {error && <Notice tone="danger">{error}</Notice>}
    </Modal>
  );
}
