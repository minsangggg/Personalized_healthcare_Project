import React, { useCallback, useEffect, useMemo, useState, type ComponentType } from "react";
import { Link, useNavigate } from "react-router-dom";
import { FiX } from "react-icons/fi";

import { useAuth } from "./AuthContext";
import VideoBackgroundLayout from "../components/VideoBackgroundLayout";
import { apiFetch } from "../api/client";

type ReceiptItemRecord = {
  receipt_id: number;
  id: string;
  ingredient_name: string;
  quantity: number;
  price: number;
  total_price: number;
};

const TEXT = {
  title: "영수증 업로드",
  description: "영수증을 업로드하면 품목을 인식해 냉장고 재료에 자동으로 추가합니다.",
  select: "이미지 파일을 선택하세요",
  upload: "영수증 분석하기",
  needLogin: "영수증을 업로드하려면 먼저 로그인하세요.",
  noHistory: "아직 저장된 영수증이 없습니다.",
  historyTitle: "최근 업로드 품목",
  latestResult: "방금 냉장고에 담은 재료",
};

const CloseIcon = FiX as ComponentType<{ className?: string }>;

export default function ReceiptUpload() {
  const { user } = useAuth();
  const userId = useMemo(() => user?.id ?? localStorage.getItem("currentUser") ?? "", [user?.id]);
  const navigate = useNavigate();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [result, setResult] = useState<ReceiptItemRecord[]>([]);
  const [history, setHistory] = useState<ReceiptItemRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState<number | null>(null);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(file);
    setError(null);
    setMessage(null);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setPreviewUrl(file ? URL.createObjectURL(file) : null);
  };

  useEffect(
    () => () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    },
    [previewUrl]
  );

  const loadHistory = useCallback(async () => {
    if (!userId) {
      setHistory([]);
      return;
    }
    try {
      const data = await apiFetch<{ receipt_items?: ReceiptItemRecord[] }>(
        `/receipts?id=${encodeURIComponent(userId)}`
      );
      setHistory(Array.isArray(data.receipt_items) ? data.receipt_items : []);
    } catch (err) {
      console.error("Failed to load receipts:", err);
      setHistory([]);
    }
  }, [userId]);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  const handleDeleteHistory = async (receiptId: number) => {
    if (!userId) {
      setError(TEXT.needLogin);
      return;
    }
    setIsDeleting(receiptId);
    try {
      await apiFetch(`/receipts/${receiptId}?id=${encodeURIComponent(userId)}`, {
        method: "DELETE",
      });
      setHistory((prev) => prev.filter((item) => item.receipt_id !== receiptId));
      setResult((prev) => prev.filter((item) => item.receipt_id !== receiptId));
    } catch (err) {
      console.error("delete failed:", err);
      setError(err instanceof Error ? err.message : "삭제에 실패했습니다.");
    } finally {
      setIsDeleting(null);
    }
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!userId) {
      setError(TEXT.needLogin);
      return;
    }
    if (!selectedFile) {
      setError("이미지 파일을 선택해주세요.");
      return;
    }

    setIsUploading(true);
    setError(null);
    setMessage(null);
    try {
      const formData = new FormData();
      formData.append("id", userId);
      formData.append("file", selectedFile);
      const data = await apiFetch<{ receipt_items?: ReceiptItemRecord[] }>("/receipts/upload", {
        method: "POST",
        body: formData,
      });
      if (data.receipt_items && data.receipt_items.length > 0) {
        setResult(data.receipt_items);
        setMessage("영수증 품목을 냉장고에 담았어요!");
        setSelectedFile(null);
        if (previewUrl) {
          URL.revokeObjectURL(previewUrl);
          setPreviewUrl(null);
        }
        await loadHistory();
      } else {
        setError("응답에서 영수증 품목을 찾지 못했습니다.");
      }
    } catch (err) {
      console.error("Upload failed:", err);
      setError(err instanceof Error ? err.message : "업로드에 실패했습니다.");
    } finally {
      setIsUploading(false);
    }
  };

  const formattedAmount = (amount?: number | null) =>
    typeof amount === "number" ? `₩${amount.toLocaleString("ko-KR")}` : "-";

  return (
    <VideoBackgroundLayout contentClassName="text-[#6B2E00]">
      <header className="relative pt-6 pb-3 text-center">
        <h1 className="text-xl font-extrabold tracking-wide">{TEXT.title}</h1>
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="absolute left-6 top-6 text-sm font-semibold text-[#6B2E00] underline"
        >
          돌아가기
        </button>
      </header>

      <main className="flex-1 px-6 pb-8">
        <p className="mt-1 text-center text-xs text-[#6B2E00]/80">{TEXT.description}</p>

        <section className="mt-4 rounded-3xl bg-white/90 p-6 text-sm text-[#6B2E00] shadow-inner">
          {!userId && (
            <p className="mb-3 rounded-2xl bg-[#FFF0DB] px-4 py-3 text-center text-xs font-semibold text-[#C75B00]">
              {TEXT.needLogin}
            </p>
          )}
          <form className="space-y-4" onSubmit={handleSubmit}>
            <label
              htmlFor="receipt"
              className="block cursor-pointer rounded-2xl border-2 border-dashed border-[#E7C9A1] bg-[#FFF7E6] px-4 py-6 text-center text-sm font-semibold hover:bg-[#FFEFD2]"
            >
              {selectedFile ? selectedFile.name : TEXT.select}
              <input
                id="receipt"
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleFileChange}
                disabled={!userId}
              />
            </label>
            {previewUrl && (
              <div className="overflow-hidden rounded-2xl border border-[#E7C9A1]/70 bg-white/70">
                <img src={previewUrl} alt="영수증 미리보기" className="w-full object-cover" />
              </div>
            )}
            <button
              type="submit"
              disabled={!userId || !selectedFile || isUploading}
              className="w-full rounded-2xl bg-[#F2994A] px-4 py-3 text-base font-bold text-white shadow transition hover:bg-[#f08a29] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isUploading ? "분석 중..." : TEXT.upload}
            </button>
          </form>
          {error && <p className="mt-3 text-center text-xs font-semibold text-red-600">{error}</p>}
          {message && (
            <p className="mt-3 text-center text-xs font-semibold text-[#1B7B3A]">{message}</p>
          )}
        </section>

        {result.length > 0 && (
          <section className="mt-5 rounded-3xl bg-[#FFF2D9] p-5 text-sm shadow-inner">
            <h2 className="text-center text-base font-extrabold text-[#C75B00]">{TEXT.latestResult}</h2>
            <div className="mt-4 rounded-2xl bg-white/80 p-3">
              <p className="text-sm font-semibold text-[#6B2E00]">자동 추가된 재료</p>
              <ul className="mt-2 space-y-1 text-xs text-[#6B2E00]/80">
                {result.map((item) => (
                  <li key={item.receipt_id} className="flex justify-between">
                    <span>{item.ingredient_name}</span>
                    <span>
                      {item.quantity}개 · 단가 {formattedAmount(item.price)} · 합계 {formattedAmount(item.total_price)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </section>
        )}

        <section className="mt-6 rounded-3xl bg-white/80 p-5 text-sm text-[#6B2E00] shadow-inner">
          <h2 className="text-center text-base font-extrabold text-[#6B2E00]">{TEXT.historyTitle}</h2>
          {history.length === 0 ? (
            <p className="mt-3 text-center text-xs text-[#6B2E00]/70">{TEXT.noHistory}</p>
          ) : (
            <ul className="mt-4 space-y-3">
              {history.map((item) => (
                <li
                  key={item.receipt_id}
                  className="rounded-2xl border border-[#E7C9A1]/70 bg-[#FFF7E6] px-4 py-3 shadow-sm flex items-center justify-between gap-2"
                >
                  <div>
                    <p className="text-sm font-semibold">{item.ingredient_name}</p>
                    <p className="text-xs text-[#6B2E00]/70">
                      {item.quantity}개 · 단가 {formattedAmount(item.price)} · 합계 {formattedAmount(item.total_price)}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDeleteHistory(item.receipt_id)}
                    disabled={isDeleting === item.receipt_id}
                    className="text-[#C75B00] rounded-full border border-transparent p-1 hover:bg-[#f6d1b8] disabled:opacity-50"
                    aria-label="삭제"
                  >
                    <CloseIcon className="h-4 w-4" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <div className="mt-6 text-center text-xs text-[#6B2E00]/70">
          <Link to="/" className="font-semibold text-[#8B4000] underline">
            메인으로 돌아가기
          </Link>
        </div>
      </main>
    </VideoBackgroundLayout>
  );
}
