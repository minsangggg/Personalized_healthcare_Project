import { useState } from 'react'
import ModalFrame from './ModalFrame'
import { cooktestAPI } from '../api/cooktest'

type Props = {
  eventId: number
  onClose: () => void
  onCreated: () => void
}

export default function CreateCookTestPostModal({ eventId, onClose, onCreated }: Props) {
  const [title, setTitle] = useState('')
  const [text, setText] = useState('')
  const [imgUrl, setImgUrl] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canSubmit = title.trim().length > 0 && text.trim().length > 0

  const submit = async () => {
    if (!canSubmit || submitting) return
    try {
      setSubmitting(true)
      setError(null)
      await cooktestAPI.createPost(eventId, {
        content_title: title.trim(),
        content_text: text.trim(),
        img_url: imgUrl.trim() ? imgUrl.trim() : null,
      })
      onCreated()
    } catch (e: any) {
      setError(e?.message ?? '등록 실패')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <ModalFrame onClose={onClose} title="대회 참가 게시글 작성">
      <div className="form-vert">
        <label>
          <div className="label">제목</div>
          <input value={title} onChange={e=>setTitle(e.target.value)} placeholder="예) 나의 비법 레시피" />
        </label>
        <label>
          <div className="label">내용</div>
          <textarea value={text} onChange={e=>setText(e.target.value)} rows={6} placeholder="레시피 설명, 팁 등을 작성하세요" />
        </label>
        <label>
          <div className="label">이미지 URL (선택)</div>
          <input value={imgUrl} onChange={e=>setImgUrl(e.target.value)} placeholder="https://..." />
        </label>
        {error && <div className="error" style={{ marginTop:4 }}>{error}</div>}
        <div style={{ display:'flex', justifyContent:'flex-end', gap:8 }}>
          <button className="btn ghost" onClick={onClose} disabled={submitting}>취소</button>
          <button className="btn" onClick={submit} disabled={!canSubmit || submitting}>{submitting ? '등록 중…' : '등록'}</button>
        </div>
      </div>
    </ModalFrame>
  )
}

