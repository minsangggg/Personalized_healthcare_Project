import { useState } from 'react';
import ModalFrame from './ModalFrame';
import { authAPI } from '../api/auth';

export type User = { user_id: string; user_name: string };

export default function LoginDialog({
  onClose,
  onSuccess,
}: {
  onClose: () => void;
  onSuccess: (u: User) => void;
}) {
  const [id, setId] = useState('');
  const [pw, setPw] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState<string | null>(null);

  const doLogin = async () => {
    setError(null); setLoading(true);
    try {
      await authAPI.login(id.trim(), pw.trim());
      const me = await authAPI.me();
      onSuccess(me);
      onClose();
    } catch (e: any) {
      setError(e?.response?.data?.detail || '로그인에 실패했어요.');
    } finally { setLoading(false); }
  };

  return (
    <ModalFrame
      title="로그인"
      desc="아이디와 비밀번호를 입력하세요."
      onClose={onClose}
    >
      {error && <div className="form-error">{error}</div>}

      <div className="login-form">
        <div className="f-row">
          <span>아이디</span>
          <input value={id} onChange={e=>setId(e.target.value)} placeholder="예) devuser123" />
        </div>
        <div className="f-row">
          <span>비밀번호</span>
          <input type="password" value={pw} onChange={e=>setPw(e.target.value)} placeholder="••••••" />
        </div>

        <button className="btn primary" disabled={loading} onClick={doLogin}>
          {loading ? '처리 중…' : '로그인'}
        </button>
      </div>
    </ModalFrame>
  );
}
