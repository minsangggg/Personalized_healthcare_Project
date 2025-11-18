const cleanText = (value?: string): string | null => {
  if (!value) return null;
  const trimmed = value.replace(/\s+/g, " ").trim();
  return trimmed || null;
};

export const parseIngredientList = (raw?: string): string[] => {
  if (!raw) {
    return [];
  }

  const result: string[] = [];
  const push = (text?: string | null) => {
    const cleaned = cleanText(text ?? undefined);
    if (cleaned) {
      result.push(cleaned);
    }
  };

  const tryObjectParse = (value: unknown): boolean => {
    if (Array.isArray(value)) {
      value.forEach((item) => {
        if (typeof item === "string") {
          push(item);
        } else if (item && typeof item === "object") {
          Object.entries(item).forEach(([key, val]) =>
            push(typeof val === "string" && val ? `${key} ${val}` : key)
          );
        }
      });
      return result.length > 0;
    }

    if (value && typeof value === "object") {
      Object.entries(value as Record<string, unknown>).forEach(([key, val]) =>
        push(typeof val === "string" && val ? `${key} ${val}` : key)
      );
      return result.length > 0;
    }
    return false;
  };

  try {
    const sanitized = raw.replace(/'/g, '"');
    const parsed = JSON.parse(sanitized);
    if (tryObjectParse(parsed)) {
      return result;
    }
  } catch {
    // fall back to text parsing
  }

  raw
    .replace(/\r\n/g, "\n")
    .split(/[\n,·]+/)
    .forEach((item) => push(item));

  return result;
};

export const parseStepList = (raw?: string): string[] => {
  if (!raw) {
    return [];
  }

  const steps: string[] = [];
  const push = (value?: string | null) => {
    const cleaned = cleanText(value ?? undefined);
    if (cleaned) {
      const normalized = cleaned.replace(/^(?:\d+[\.\)]\s*)+/, "").trim();
      if (normalized) {
        steps.push(normalized);
      }
    }
  };

  const trimmed = raw.trim();
  if (trimmed.startsWith("[") && trimmed.endsWith("]")) {
    try {
      const sanitized = raw.replace(/'/g, '"');
      const parsed = JSON.parse(sanitized);
      if (Array.isArray(parsed)) {
        parsed.forEach((item) => {
          if (typeof item === "string") {
            push(item);
          }
        });
        if (steps.length > 0) {
          return steps;
        }
      }
    } catch {
      // ignore and fall through
    }
  }

  raw
    .replace(/\\n/g, "\n")
    .replace(/\r\n/g, "\n")
    .split(/\n+/)
    .forEach((line) => push(line.replace(/^\d+[\.\)]\s*/, "")));

  return steps;
};
