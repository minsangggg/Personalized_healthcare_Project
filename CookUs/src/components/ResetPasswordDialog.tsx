// src/components/ResetPasswordDialog.tsx
import { useEffect, useRef, useState } from 'react'
import ModalFrame from './ModalFrame'
import { authAPI } from '../api/auth'

type Props = {
  onClose: () => void;
  onToLogin?: (prefillId?: string, toast?: string) => void; // ★ 추가
};

export default function ResetPasswordDialog({ onClose, onToLogin }: Props) {
  const [step, setStep] = useState<'send'|'verify'>('send')
  const [id, setId] = useState('')
  const [email, setEmail] = useState('')
  const [code, setCode] = useState('')
  const [pw, setPw] = useState('')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [okMsg, setOkMsg] = useState<string | null>(null)
  const [devCode, setDevCode] = useState<string | undefined>(undefined)

  // 타이머 정리용
  const timerRef = useRef<number | null>(null)
  useEffect(() => () => { if (timerRef.current) window.clearTimeout(timerRef.current) }, [])

  const send = async () => {
    setError(null); setLoading(true)
    try {
      const res = await authAPI.sendFindPwCode(id.trim(), email.trim())
      setDevCode(res.dev_code)
      setStep('verify')
    } catch (e:any) {
      setError(e?.response?.data?.detail || '인증코드 발송에 실패했어요.')
    } finally { setLoading(false) }
  }

  const reset = async () => {
    setError(null); setOkMsg(null); setLoading(true)
    try {
      await authAPI.setNewPassword(id.trim(), email.trim(), code.trim(), pw.trim())
      setOkMsg('비밀번호가 변경되었습니다. 다시 로그인하세요.');
    } catch (e:any) {
      setError(e?.response?.data?.detail || '비밀번호 변경에 실패했어요.')
    } finally { setLoading(false) }
  }

  return (
    <ModalFrame
      title="비밀번호 찾기"
      desc={step==='send' ? '아이디와 이메일을 입력해 인증코드를 받으세요.' : '인증코드와 새 비밀번호를 입력하세요.'}
      onClose={onClose}
    >
      {error && <div className="form-error">{error}</div>}
      {okMsg && <div className="empty">{okMsg}</div>}

      {step==='send' ? (
        <>
          <div className="f-row"><span>아이디</span>
            <input value={id} onChange={e=>setId(e.target.value)} placeholder="devuser123" />
          </div>
          <div className="f-row"><span>이메일</span>
            <input value={email} onChange={e=>setEmail(e.target.value)} placeholder="you@example.com" />
          </div>

          <div className="dialog-actions">
            <button className="btn ghost" onClick={onClose}>닫기</button>
            <button className="btn primary" disabled={loading || !id.trim() || !email.trim()} onClick={send}>
              {loading ? '발송 중…' : '인증코드 받기'}
            </button>
          </div>
          {devCode && <p className="hint"></p>}
        </>
      ) : (
        <>
          <div className="f-row"><span>아이디</span>
            <input value={id} onChange={e=>setId(e.target.value)} />
          </div>
          <div className="f-row"><span>이메일</span>
            <input value={email} onChange={e=>setEmail(e.target.value)} />
          </div>
          <div className="f-row"><span>인증코드</span>
            <input value={code} onChange={e=>setCode(e.target.value)} placeholder="6자리" />
          </div>
          <div className="f-row"><span>새 비밀번호</span>
            <input type="password" value={pw} onChange={e=>setPw(e.target.value)} placeholder="새 비밀번호" />
          </div>

          <div className="dialog-actions">
            {okMsg ? (
              <>
                <button className="btn ghost" onClick={onClose}>닫기</button>
                <button
                  className="btn primary"
                  onClick={() => {
                    onToLogin?.(id.trim(), okMsg || '비밀번호가 변경되었습니다.');
                    onClose();
                  }}
                >
                  로그인하러 가기
                </button>
              </>
            ) : (
              <>
                <button className="btn ghost" onClick={()=>setStep('send')}>뒤로</button>
                <button
                  className="btn primary"
                  disabled={loading || !id.trim() || !email.trim() || !code.trim() || !pw.trim()}
                  onClick={reset}
                >
                  {loading ? '변경 중…' : '변경하기'}
                </button>
              </>
            )}
          </div>

        </>
      )}
    </ModalFrame>
  )
}
