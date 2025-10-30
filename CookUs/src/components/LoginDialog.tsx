import { useState } from 'react';
import ModalFrame from './ModalFrame';
import { authAPI } from '../api/auth';
import FindIdDialog from './FindIdDialog';
import ResetPasswordDialog from './ResetPasswordDialog';

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

  const [showFindId, setShowFindId] = useState(false);
  const [showResetPw, setShowResetPw] = useState(false);

  const doLogin = async () => {
    setError(null); setLoading(true);
    try {
      await authAPI.login(id.trim(), pw.trim());
      const me = await authAPI.me();
      onSuccess(me);
      onClose();
    } catch (e: any) {
      setError(e?.response?.data?.detail || '아이디 또는 비밀번호가 틀립니다.');
    } finally { setLoading(false); }
  };

  return (
    <>
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

          {/* 하단 링크 영역 */}
            <div style={{display:'flex', justifyContent:'space-between', marginTop:10}}>
              <button className="btn ghost" onClick={()=>setShowFindId(true)}>아이디 찾기</button>
              <button className="btn ghost" onClick={()=>setShowResetPw(true)}>비밀번호 찾기</button>
            </div>
        </div>
      </ModalFrame>
      {/* 하위 모달들 (프레임 내부 포털을 쓰는 구조라면 그 위치를 사용) */}
      {showFindId && <FindIdDialog onClose={()=>setShowFindId(false)} />}
      {showResetPw && (
        <ResetPasswordDialog
          onClose={() => setShowResetPw(false)}
          onToLogin={(prefillId) => {
            setShowResetPw(false);
            if (prefillId) setId(prefillId);
          }}
        />
      )}
    </>
  );
}
