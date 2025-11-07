import { createPortal } from 'react-dom';
import type { ReactNode } from 'react';
import './LoginModal.css';

export default function ModalFrame({
  title,
  desc,
  onClose,
  children,
}: {
  title: string;
  desc?: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const host = document.querySelector('.app-frame') ?? document.body;
  return createPortal(
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal login" onClick={(e) => e.stopPropagation()}>
        <button className="modal-x" onClick={onClose}>×</button>
        <h3 className="modal-title">{title}</h3>
        {desc && <p className="modal-desc">{desc}</p>}
        {children}
      </div>
    </div>,
    host
  );
}