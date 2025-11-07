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
  const [files, setFiles] = useState<File[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canSubmit = title.trim().length > 0 && text.trim().length > 0

  const submit = async () => {
    if (!canSubmit || submitting) return
    try {
      setSubmitting(true)
      setError(null)
      let imageUrls: string[] = []
      if (files.length) {
        if (files.length > 7) throw new Error('이미지는 최대 7장까지 가능합니다')
        const exts = files.map(f => (f.name.split('.').pop() || '').toLowerCase())
        if (exts.some(ext => !['jpg','jpeg','png'].includes(ext))) {
          throw new Error('이미지 확장자는 jpg, jpeg, png만 지원합니다')
        }
        const presigned = await cooktestAPI.presignUploads(eventId, exts)
        const list = presigned?.upload_list || []
        if (list.length !== files.length) throw new Error('업로드 URL 생성 실패')
        for (let i=0;i<files.length;i++) {
          const file = files[i]
          const up = list[i]
          const ext = exts[i]
          const contentType = file.type || (ext === 'png' ? 'image/png' : 'image/jpeg')
          const putRes = await fetch(up.upload_url, {
            method: 'PUT',
            mode: 'cors',
            credentials: 'omit',
            headers: { 'Content-Type': contentType },
            body: file,
          })
          if (!putRes.ok) throw new Error('S3 업로드 실패')
          imageUrls.push(up.file_url)
        }
      }
      await cooktestAPI.createPost(eventId, { content_title: title.trim(), content_text: text.trim(), img_urls: imageUrls })
      onCreated()
    } catch (e: any) {
      setError(e?.message ?? '등록 실패')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <ModalFrame onClose={onClose} title="대회참여 게시글 작성">
      <div className="form-vert">
        <label>
          <div className="label">제목</div>
          <input value={title} onChange={e=>setTitle(e.target.value)} placeholder="나만의 비법 요리 제목" />
        </label>
        <label>
          <div className="label">내용</div>
          <textarea value={text} onChange={e=>setText(e.target.value)} rows={6} placeholder="조리설명, 노하우를 자세히 적어주세요" />
        </label>
        <label>
          <div className="label">사진 업로드 (최대 7장)</div>
          <input multiple type="file" accept="image/png,image/jpeg" onChange={e=>setFiles(Array.from(e.target.files || []))} />
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
