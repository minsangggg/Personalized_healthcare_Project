// src/components/FindIdDialog.tsx
import { useState } from 'react'
import ModalFrame from './ModalFrame'
import { authAPI } from '../api/auth'

export default function FindIdDialog({ onClose }: { onClose: () => void }) {
  const [step, setStep] = useState<'send'|'verify'|'done'>('send')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [code, setCode] = useState('')
  const [foundId, setFoundId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [devCode, setDevCode] = useState<string | undefined>(undefined)

  const send = async () => {
    setError(null); setLoading(true)
    try {
      const res = await authAPI.sendFindIdCode(email.trim(), username.trim() || undefined)
      setDevCode(res.dev_code)
      setStep('verify')
    } catch (e:any) {
      setError(e?.response?.data?.detail || '인증코드 발송에 실패했어요.')
    } finally { setLoading(false) }
  }

  const verify = async () => {
    setError(null); setLoading(true)
    try {
      const res = await authAPI.verifyFindIdCode(email.trim(), code.trim())
      setFoundId(res.user_id)
      setStep('done')
    } catch (e:any) {
      setError(e?.response?.data?.detail || '코드 검증에 실패했어요.')
    } finally { setLoading(false) }
  }

  return (
    <ModalFrame
      title="아이디 찾기"
      desc={step==='send' ? '이메일(필수)과 이름(선택)을 입력해 주세요.' :
            step==='verify' ? '메일로 받은 인증코드를 입력해 주세요.' :
            '아이디를 확인했어요.'}
      onClose={onClose}
    >
      {error && <div className="form-error">{error}</div>}

      {step === 'send' && (
        <>
          <div className="f-row"><span>이름(선택)</span>
            <input value={username} onChange={e=>setUsername(e.target.value)} placeholder="홍길동" />
          </div>
          <div className="f-row"><span>이메일</span>
            <input value={email} onChange={e=>setEmail(e.target.value)} placeholder="you@example.com" />
          </div>

          <div className="dialog-actions">
            <button className="btn ghost" onClick={onClose}>닫기</button>
            <button className="btn primary" disabled={loading || !email.trim()} onClick={send}>
              {loading ? '발송 중…' : '인증코드 받기'}
            </button>
          </div>
          {devCode && <p className="hint">개발코드: {devCode}</p>}
        </>
      )}

      {step === 'verify' && (
        <>
          <div className="f-row"><span>이메일</span>
            <input value={email} onChange={e=>setEmail(e.target.value)} />
          </div>
          <div className="f-row"><span>인증코드</span>
            <input value={code} onChange={e=>setCode(e.target.value)} placeholder="6자리" />
          </div>

          <div className="dialog-actions">
            <button className="btn ghost" onClick={()=>setStep('send')}>뒤로</button>
            <button className="btn primary" disabled={loading || !email.trim() || !code.trim()} onClick={verify}>
              {loading ? '확인 중…' : '확인'}
            </button>
          </div>
        </>
      )}

      {step === 'done' && (
        <>
          <div className="empty">해당 이메일의 아이디는 <b>{foundId}</b> 입니다.</div>
          <div className="dialog-actions">
            <button className="btn primary" onClick={onClose}>확인</button>
          </div>
        </>
      )}
    </ModalFrame>
  )
}
