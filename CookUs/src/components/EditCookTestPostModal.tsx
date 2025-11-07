import { useState } from 'react'
import ModalFrame from './ModalFrame'
import { cooktestAPI, type CookPost } from '../api/cooktest'

type Props = {
  eventId: number
  post: CookPost
  onClose: () => void
  onSaved: () => void
}

export default function EditCookTestPostModal({ eventId, post, onClose, onSaved }: Props) {
  const [title, setTitle] = useState(post.content_title)
  const [text, setText] = useState(post.content_text)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canSave = title.trim().length > 0 && text.trim().length > 0

  const save = async () => {
    if (!canSave || saving) return
    try {
      setSaving(true)
      setError(null)
      await cooktestAPI.updatePost(eventId, post.post_id, {
        content_title: title.trim(),
        content_text: text.trim(),
      })
      onSaved()
    } catch (e: any) {
      setError(e?.message ?? '수정에 실패했어요')
    } finally {
      setSaving(false)
    }
  }

  return (
    <ModalFrame onClose={onClose} title="게시글 수정">
      <div className="form-vert">
        <label>
          <div className="label">제목</div>
          <input value={title} onChange={e => setTitle(e.target.value)} />
        </label>
        <label>
          <div className="label">내용</div>
          <textarea rows={6} value={text} onChange={e => setText(e.target.value)} />
        </label>
        {error && <div className="error">{error}</div>}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <button className="btn ghost" onClick={onClose} disabled={saving}>닫기</button>
          <button className="btn" onClick={save} disabled={!canSave || saving}>
            {saving ? '저장 중…' : '저장'}
          </button>
        </div>
      </div>
    </ModalFrame>
  )
}
