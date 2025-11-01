import { useState } from 'react'
import ModalFrame from './ModalFrame'
import { authAPI, type User } from '../api/auth'
import './EditProfileDialog.css';

export default function EditProfileDialog({
  me, onClose, onSaved
}: {
  me: User
  onClose: () => void
  onSaved: () => void
}) {
  const [user_name, setUserName] = useState(me.user_name ?? '')
  const [email, setEmail] = useState(me.email ?? '')
  
  const normalizeGender = (g: any): 'male' | 'female' => {
    if (g === 'male' || g === 'female') return g;
    if (String(g).trim() === '남' || String(g).toLowerCase().startsWith('m')) return 'male'
    return 'female';
  }

  const [gender, setGender] = useState<'male' | 'female'>(normalizeGender(me.gender))
  
  const [date_of_birth, setDob] = useState(me.date_of_birth ?? '')
  const [goal, setGoal] = useState<number>(typeof me.goal === 'number' ? me.goal! : 0)
  const [cooking_level, setLevel] = useState<(User['cooking_level'])>(me.cooking_level ?? '하')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const save = async () => {
    setError(null); setLoading(true)
    try {
      await authAPI.updateMe({
        user_name, email, gender: gender as any,
        date_of_birth: date_of_birth || null,
        goal, cooking_level: cooking_level as any
      })
      onSaved()
    } catch (e:any) {
      setError(e?.response?.data?.detail || '저장에 실패했어요.')
    } finally { setLoading(false) }
  }

  return (
    <ModalFrame title="프로필 수정" desc="정보를 수정하고 저장하세요." onClose={onClose}>
      {error && <div className="form-error">{error}</div>}

      <div className="f-row"><span>이름</span>
        <input value={user_name} onChange={e=>setUserName(e.target.value)} />
      </div>
      <div className="f-row"><span>이메일</span>
        <input value={email} onChange={e=>setEmail(e.target.value)} />
      </div>

      <div className="f-row two">
        <div className="inline">
          <span>성별</span>
          <div className="pill-group">
            <input id="g-m" className="radio" type="radio" name="gender" checked={gender==='male'} onChange={()=>setGender('male' as any)} />
            <label htmlFor="g-m" className="rbtn">남</label>
            <input id="g-f" className="radio" type="radio" name="gender" checked={gender==='female'} onChange={()=>setGender('female' as any)} />
            <label htmlFor="g-f" className="rbtn">여</label>
          </div>
        </div>
        <div>
          <span>생년월일</span>
          <input placeholder="YYYY-MM-DD" value={date_of_birth ?? ''} onChange={e=>setDob(e.target.value)} />
        </div>
      </div>

      <div className="f-row two">
        <div>
          <span>주간 목표</span>
          <input type="number" min={0} max={21} value={goal ?? 0} onChange={e=>setGoal(Number(e.target.value||0))} />
        </div>
        <div className="inline">
          <span>요리 레벨</span>
          <div className="pill-group">
            <input id="lvl-low" className="radio" type="radio" name="lvl" checked={cooking_level==='하'} onChange={()=>setLevel('하' as any)} />
            <label htmlFor="lvl-low" className="rbtn">하</label>
            <input id="lvl-high" className="radio" type="radio" name="lvl" checked={cooking_level==='상'} onChange={()=>setLevel('상' as any)} />
            <label htmlFor="lvl-high" className="rbtn">상</label>
          </div>
        </div>
      </div>

      <div className="dialog-actions">
        <button className="btn ghost" onClick={onClose}>취소</button>
        <button className="btn primary" disabled={loading} onClick={save}>
          {loading ? '저장 중…' : '저장'}
        </button>
      </div>
    </ModalFrame>
  )
}
