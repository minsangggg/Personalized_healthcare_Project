import React, { useState } from "react";
import axios from "axios";

const UploadBoard = () => {
  const [files, setFiles] = useState([]);
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [previewUrls, setPreviewUrls] = useState([]);
  const userId = "irisyshin";
  const eventId = 1;

  const handleFileChange = (e) => {
    const selected = Array.from(e.target.files);
    setFiles(selected);
    setPreviewUrls(selected.map((file) => URL.createObjectURL(file)));
  };

  const handleUpload = async () => {
    if (files.length === 0) return alert("이미지를 선택하세요.");
    if (!title.trim()) return alert("제목을 입력하세요.");

    try {
      const fileExts = files.map((f) => f.name.split(".").pop());
      const res = await axios.post(
        "http://localhost:8000/generate-presigned-urls",
        {},
        { params: { event_id: eventId, user_id: userId, file_exts: fileExts } }
      );

      const uploadList = res.data.upload_list;

      await Promise.all(
        files.map((file, idx) =>
          axios.put(uploadList[idx].upload_url, file, {
            headers: { "Content-Type": file.type },
          })
        )
      );

      const imgUrls = uploadList.map((i) => i.file_url);
      await axios.post("http://localhost:8000/save-board", {
        event_id: eventId,
        user_id: userId,
        content_title: title,
        content_text: text,
        img_urls: imgUrls,
      });

      alert("업로드 성공!");
      setFiles([]);
      setPreviewUrls([]);
      setTitle("");
      setText("");
    } catch (err) {
      console.error(err);
      alert("업로드 실패");
    }
  };

  return (
    <div style={{ maxWidth: 600, margin: "2rem auto" }}>
      <h2>📸 새 게시글 업로드</h2>
      <input type="text" placeholder="제목" value={title}
        onChange={(e) => setTitle(e.target.value)} />
      <textarea placeholder="내용" value={text}
        onChange={(e) => setText(e.target.value)} />
      <input type="file" multiple accept="image/*" onChange={handleFileChange} />
      <div style={{ display: "flex", gap: 10 }}>
        {previewUrls.map((url, i) => (
          <img key={i} src={url} alt="preview" width={100} height={100} />
        ))}
      </div>
      <button onClick={handleUpload}>등록</button>
    </div>
  );
};

export default UploadBoard;
