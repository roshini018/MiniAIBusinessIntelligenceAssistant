import React from 'react';
import { CheckCircle2 } from 'lucide-react';

interface ToastProps {
  message: string | null;
}

export const Toast: React.FC<ToastProps> = ({ message }) => {
  if (!message) return null;

  return (
    <div className="toast-notice">
      <CheckCircle2 size={15} style={{ color: 'var(--accent-green)' }} />
      <span>{message}</span>
    </div>
  );
};
