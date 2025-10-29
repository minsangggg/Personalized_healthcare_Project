import { useState } from 'react';
import ModalFrame from './ModalFrame';
import { authAPI } from '../api/auth';
import type { User } from './LoginDialog';

export default function SignupDialog({
  onClose,
  onSuccess,
}: {
  onClose: () => void;
  onSuccess: (u: User) => void;
}) {
  const [id, setId] = useState('');
  const [userName, setUserName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [gender, setGender] = useState<'male'|'female'>('male');
  const [level, setLevel]   = useState<'상'|'하'>('하');
  const [dob, setDob] = useState('');
  const [goal, setGoal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState<string | null>(null);

  const doSignup = async () => {
    setError(null); setLoading(true);
    try {
      await authAPI.signup({
        id: id.trim(),
        user_name: userName.trim() || id.trim(),
        email: email.trim(),
        password: password.trim(),
        gender,
        date_of_birth: (dob.trim() || undefined),
        cooking_level: level,
        goal,
      });
      // 가입 성공 → 자동 로그인
      await authAPI.login(id.trim(), password.trim());
      const me = await authAPI.me();
      onSuccess(me);
      onClose();
    } catch (e: any) {
      setError(e?.response?.data?.detail || '회원가입에 실패했어요.');
    } finally { setLoading(false); }
  };

  return (
    <ModalFrame
      title="회원가입"
      desc="아래 정보를 입력해 CookUS에 가입하세요."
      onClose={onClose}
    >
      {error && <div className="form-error">{error}</div>}

      <div className="login-form">
        <div className="f-row">
          <span>아이디</span>
          <input value={id} onChange={e=>setId(e.target.value)} placeholder="영문/숫자" />
        </div>
        <div className="f-row">
          <span>이름</span>
          <input value={userName} onChange={e=>setUserName(e.target.value)} placeholder="홍길동" />
        </div>
        <div className="f-row">
          <span>이메일</span>
          <input value={email} onChange={e=>setEmail(e.target.value)} placeholder="you@example.com" />
        </div>
        <div className="f-row">
          <span>비밀번호</span>
          <input type="password" value={password} onChange={e=>setPassword(e.target.value)} placeholder="최소 1자" />
        </div>

        <div className="f-row two">
          <div className="inline">
            <span>성별</span>
            <div className="pill-group">
              <input id="gender-m" className="radio" type="radio" name="gender"
                checked={gender==='male'} onChange={()=>setGender('male')} />
              <label htmlFor="gender-m" className="rbtn">남</label>

              <input id="gender-f" className="radio" type="radio" name="gender"
                checked={gender==='female'} onChange={()=>setGender('female')} />
              <label htmlFor="gender-f" className="rbtn">여</label>
            </div>
          </div>

          <div className="inline">
            <span>레벨</span>
            <div className="pill-group">
              <input id="lvl-low" className="radio" type="radio" name="level"
                checked={level==='하'} onChange={()=>setLevel('하')} />
              <label htmlFor="lvl-low" className="rbtn">하</label>

              <input id="lvl-high" className="radio" type="radio" name="level"
                checked={level==='상'} onChange={()=>setLevel('상')} />
              <label htmlFor="lvl-high" className="rbtn">상</label>
            </div>
          </div>
        </div>

        <div className="f-row two">
          <div>
            <span>생년월일</span>
            <input value={dob} onChange={e=>setDob(e.target.value)} placeholder="YYYY-MM-DD" />
          </div>
          <div>
            <span>주간 요리 목표</span>
            <input type="number" min={0} max={21}
              value={goal} onChange={e=>setGoal(Number(e.target.value||0))} />
          </div>
        </div>

        <button className="btn primary" disabled={loading} onClick={doSignup}>
          {loading ? '처리 중…' : '회원가입'}
        </button>
      </div>
    </ModalFrame>
  );
}
