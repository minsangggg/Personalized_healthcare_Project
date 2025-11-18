// src/api/client.ts

// 1) 우선순위: 환경변수 → 전역(window.__API_BASE_URL__) → 최종 기본값(로컬 개발용)
const FALLBACK_API_BASE_URL = "http://127.0.0.1:8000";

// ✅ CRA(react-scripts) 방식: 빌드 시 REACT_APP_API_BASE_URL이 문자열로 치환됨
const ENV_API = process.env.REACT_APP_API_BASE_URL;

// 런타임 전역(필요하면 index.html에서 <script>로 주입 가능)
declare global {
  interface Window {
    __API_BASE_URL__?: string;
  }
}

const RUNTIME_API =
  (typeof window !== "undefined" && window.__API_BASE_URL__) || undefined;

// 최종 base URL 결정
const apiBaseUrl = (ENV_API || RUNTIME_API || FALLBACK_API_BASE_URL).replace(
  /\/+$/,
  ""
);

export function buildApiUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${apiBaseUrl}${normalized}`;
}

export interface ApiFetchOptions extends RequestInit {
  skipAuthHeader?: boolean;
}

export async function apiFetch<T = any>(
  path: string,
  options: ApiFetchOptions = {}
): Promise<T> {
  const { skipAuthHeader, headers, ...rest } = options;
  const bodyIsFormData =
    typeof FormData !== "undefined" && rest.body instanceof FormData;

  const mergedHeaders: HeadersInit = {
    ...(bodyIsFormData ? {} : { "Content-Type": "application/json" }),
    ...(headers || {}),
  };

  const url = buildApiUrl(path);
  // eslint-disable-next-line no-console
  console.log("[API FETCH]", url, rest.method ?? "GET");

  const response = await fetch(url, {
    headers: mergedHeaders,
    ...rest,
  });

  const rawText = await response.text();
  let data: unknown = null;

  if (rawText) {
    try {
      data = JSON.parse(rawText);
    } catch {
      data = rawText;
    }
  }

  if (!response.ok) {
    let detail: string | undefined;

    if (typeof data === "object" && data !== null && "detail" in data) {
      const extracted = (data as { detail: unknown }).detail;
      if (typeof extracted === "string") {
        detail = extracted;
      } else if (Array.isArray(extracted)) {
        detail = extracted
          .map((item) => {
            if (typeof item === "string") return item;
            if (item && typeof item === "object") {
              if ("msg" in item && typeof (item as { msg: unknown }).msg === "string") {
                return (item as { msg: string }).msg;
              }
              if ("detail" in item && typeof (item as { detail: unknown }).detail === "string") {
                return (item as { detail: string }).detail;
              }
            }
            try {
              return JSON.stringify(item);
            } catch {
              return String(item);
            }
          })
          .join("\n");
      }
    } else if (typeof data === "string" && data.trim()) {
      detail = data;
    }

    const message = detail?.trim() || response.statusText || "요청이 실패했습니다.";
    throw new Error(message);
  }

  return data as T;
}
