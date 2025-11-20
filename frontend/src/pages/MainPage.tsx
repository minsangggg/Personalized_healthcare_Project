import React, {
  useCallback,
  useEffect,
  useMemo,
  useState,
  useRef,
  type ComponentType,
} from "react";
import { Link, useNavigate } from "react-router-dom";
import { FaUserCircle } from "react-icons/fa";

import { useAuth } from "./AuthContext";
import SplashScreen from "./SplashScreen";
import { apiFetch } from "../api/client";
import VideoBackgroundLayout from "../components/VideoBackgroundLayout";
import { parseIngredientList, parseStepList } from "../utils/recipeText";

type IngredientItem = {
  name: string;
  amount: string;
};

type RecommendationItem = {
  recipe_id: string | number;
  recommend_id?: number;
  recipe_nm_ko?: string;
  level_nm?: string;
  cooking_time?: string;
  step_text?: string;
  ingredient_full?: string;
  selected?: boolean;
};

const UserCircleIcon = FaUserCircle as ComponentType<{ className?: string }>;

const TEXT = {
  nav: {
    fridge: "\uB0C9\uC7A5\uACE0",
    calendar: "\uCE98\uB9B0\uB354",
    dashboard: "\uB300\uC2DC\uBCF4\uB4DC",
    logout: "\uB85C\uADF8\uC544\uC6C3",
    login: "\uB85C\uADF8\uC778",
    myPage: "\uB9C8\uC774\uD398\uC774\uC9C0",
  },
  tagline: {
    line1: "\uB0C9\uC7A5\uACE0 \uC18D \uC7AC\uB8CC\uB85C",
    line2: "\uB808\uC2DC\uD53C\uB97C \uCD94\uCC9C\uBC1B\uC544\uC694.",
  },
  fridgeCard: {
    title: "\uB0B4 \uB0C9\uC7A5\uACE0",
    countPrefix: "\uC7AC\uB8CC ",
    toggle: "\uB0B4 \uB0C9\uC7A5\uACE0 \uC7AC\uB8CC \uBCF4\uAE30",
    empty: "\uB4F1\uB85D\uB41C \uC7AC\uB8CC\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4.",
    save: "\uC800\uC7A5",
    delete: "\uC0AD\uC81C",
  },
  buttons: {
    add: "\uC7AC\uB8CC \uCD94\uAC00",
    recommend: "\uB808\uC2DC\uD53C \uCD94\uCC9C \uBC1B\uAE30",
    reset: "\uC7AC\uB8CC \uCD08\uAE30\uD654",
    history: "\uC9C0\uB09C \uCD94\uCC9C \uBCF4\uAE30",
    receiptUpload: "\uC601\uC218\uC99D \uC5C5\uB85C\uB4DC",
  },
  loading: "\uCD94\uCC9C\uC744 \uC900\uBE44\uD558\uACE0 \uC788\uC2B5\uB2C8\uB2E4...",
  footer: {
    title: "2025 \uB808\uC2DC\uD53C \uB9C8\uCF13",
    about: "\uC18C\uAC1C",
    faq: "FAQ",
    company: "\uB808\uC2DC\uD53C \uB9C8\uCF13 | \uB300\uD45C\uC790 \uD64D\uAE38\uB3D9",
    contact: "123-45-6789 (\uC0AC\uC5C5\uC790\uC815\uBCF4\uD655\uC778) | +82-1234-4567",
    email: "parkms@gmail.com",
    policy: "\uC774\uC6A9\uC57D\uAD00 | \uAC1C\uC778\uC815\uBCF4\uCC98\uB9AC\uBC29\uCE68",
  },
  ingredientModal: {
    title: "\uC7AC\uB8CC \uAD00\uB9AC",
    placeholder: "\uC7AC\uB8CC\uBA85\uC744 \uC785\uB825\uD574 \uC8FC\uC138\uC694",
    noResult: "\uAC80\uC0C9 \uACB0\uACFC\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4.",
    save: "\uC800\uC7A5",
    cancel: "\uCDE8\uC18C",
    delete: "\uC0AD\uC81C",
  },
  recommendModal: {
    title: "\uCD94\uCC9C \uB808\uC2DC\uD53C",
    empty: "\uCD94\uCC9C \uACB0\uACFC\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4.",
    detail: "\uC0C1\uC138 \uBCF4\uAE30",
    register: "\uB4F1\uB85D",
    close: "\uB2EB\uAE30",
  },
  detailModal: {
    difficulty: "\uB09C\uC774\uB3C4",
    infoNone: "\uC815\uBCF4 \uC5C6\uC74C",
    cookingTime: "\uC870\uB9AC \uC2DC\uAC04:",
    ingredients: "[\uD544\uC694 \uC7AC\uB8CC]",
    method: "\uC870\uB9AC \uBC29\uBC95:",
    steps: "[\uC870\uB9AC \uC21C\uC11C]",
    methodNone: "\uC870\uB9AC \uBC29\uBC95 \uC815\uBCF4\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4.",
    close: "\uB2EB\uAE30",
    youtube: "\uC601\uC0C1 \uBCF4\uAE30",
    loadingVideo: "\uB3D9\uC601\uC0C1 \uBD88\uB7EC\uC624\uB294 \uC911...",
  },
  alerts: {
    requireLoginSave: "\uB85C\uADF8\uC778 \uD6C4\uC5D0 \uB0C9\uC7A5\uACE0\uB97C \uC800\uC7A5\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4.",
    saveSuccess: "\uB0C9\uC7A5\uACE0\uC5D0 \uC800\uC7A5\uB418\uC5C8\uC2B5\uB2C8\uB2E4.",
    saveFail: "\uB0C9\uC7A5\uACE0 \uC800\uC7A5\uC5D0 \uC2E4\uD328\uD588\uC2B5\uB2C8\uB2E4.",
    requireLoginRecommend: "\uB85C\uADF8\uC778 \uD6C4\uC5D0 \uCD94\uCC9C\uC744 \uBC1B\uC744 \uC218 \uC788\uC2B5\uB2C8\uB2E4.",
    fetchFail: "\uCD94\uCC9C\uC744 \uBD88\uB7EC\uC624\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4.",
    loginFirst: "\uBA3C\uC800 \uB85C\uADF8\uC778\uD574 \uC8FC\uC138\uC694.",
    selectAtLeastOne: "\uCD5C\uC18C \uD55C \uAC1C \uC774\uC0C1\uC758 \uB808\uC2DC\uD53C\uB97C \uC120\uD0DD\uD574 \uC8FC\uC138\uC694.",
    registerSuccess: "\uC120\uD0DD\uD55C \uB808\uC2DC\uD53C\uAC00 \uB4F1\uB85D\uB418\uC5C8\uC2B5\uB2C8\uB2E4.",
    registerFail: "\uB808\uC2DC\uD53C\uB97C \uB4F1\uB85D\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4.",
    confirmReset: "\uB0C9\uC7A5\uACE0 \uC7AC\uB8CC\uB97C \uBAA8\uB450 \uC0AD\uC81C\uD560\uAE4C\uC694?",
    userLevelPrefix: "\uD604\uC7AC \uC694\uB9AC \uB808\uBCA8 ",
    userLevelSuffix: "\uC5D0 \uB9DE\uB294 \uB808\uC2DC\uD53C\uC785\uB2C8\uB2E4.",
    missingRecommendId: "\uCD94\uCC9C \uC815\uBCF4\uB97C \uB2E4\uC2DC \uBC1B\uC544\uC8FC\uC138\uC694.",
    videoFetchFail: "\uB3D9\uC601\uC0C1\uC744 \uBD88\uB7EC\uC624\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4.",
    videoTitleMissing: "\uC601\uC0C1 \uC81C\uBAA9\uC774 \uC5C6\uC2B5\uB2C8\uB2E4.",
  },
};

export default function MainPage() {
  const [ingredients, setIngredients] = useState<IngredientItem[]>([]);
  const [search, setSearch] = useState("");
  const [searchResults, setSearchResults] = useState<string[]>([]);
const STORAGE_LAST_RECOMMEND = "cookus:last-recommended";
const STORAGE_SEEN_RECOMMEND = "cookus:seen-recipes";

type SeenRecipe = {
  id: string;
  signature: string;
  seenAt: number;
};

function buildIngredientSignature(items: IngredientItem[]): string {
  const normalized = items
    .map((item) => {
      const name = item.name.trim().toLowerCase().replace(/\s+/g, "").replace(/_/g, "");
      if (!name) return null;
      const amount = (item.amount || "").toString().trim();
      return `${name}:${amount}`;
    })
    .filter(Boolean) as string[];
  normalized.sort();
  return normalized.join(";");
}
const [recommended, setRecommended] = useState<RecommendationItem[]>([]);
const [lastRecommended, setLastRecommended] = useState<RecommendationItem[]>(() => {
  try {
    const raw = localStorage.getItem(STORAGE_LAST_RECOMMEND);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      return parsed;
    }
  } catch {
    // ignore parse errors
  }
  return [];
});
  const [userLevelMessage, setUserLevelMessage] = useState<string | null>(null);
  const [selectedRecipe, setSelectedRecipe] = useState<RecommendationItem | null>(null);
  const [showFridge, setShowFridge] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [showRecommendModal, setShowRecommendModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showSplash, setShowSplash] = useState(true);
  const [userName, setUserName] = useState<string | null>(null);
const [videoUrl, setVideoUrl] = useState<string | null>(null);
const [videoLoading, setVideoLoading] = useState(false);
const [cleanedSteps, setCleanedSteps] = useState<string[]>([]);
const [saveSuccessMessage, setSaveSuccessMessage] = useState<string | null>(null);
  const [showQuickMenu, setShowQuickMenu] = useState(false);
  const [quickMenuPos, setQuickMenuPos] = useState<{ top: number; left: number }>({ top: 12, left: 12 });
  const quickMenuButtonRef = useRef<HTMLButtonElement | null>(null);

const ingredientList = useMemo(
  () => parseIngredientList(selectedRecipe?.ingredient_full),
  [selectedRecipe?.ingredient_full]
);
const stepList = useMemo(() => parseStepList(selectedRecipe?.step_text), [selectedRecipe?.step_text]);
const stepsToRender = cleanedSteps.length ? cleanedSteps : stepList;

  const { user, logout } = useAuth();
  const userId = useMemo(() => user?.id ?? localStorage.getItem("currentUser"), [user?.id]);
  const navigate = useNavigate();

  useEffect(() => {
    const skipSplash = sessionStorage.getItem("skipSplash");
    if (skipSplash === "true") {
      setShowSplash(false);
    } else {
      const timer = setTimeout(() => {
        setShowSplash(false);
        sessionStorage.setItem("skipSplash", "true");
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, []);

  useEffect(() => {
    if (!userId) {
      setIngredients([]);
      setUserName(null);
      return;
    }

    const storageKey = `ingredients_${userId}`;
    const stored = JSON.parse(localStorage.getItem(storageKey) || "[]");
    setIngredients(stored);

    apiFetch<{ name?: string }>(`/get_user_name/${userId}`)
      .then((data) => {
        if (data.name) {
          setUserName(data.name);
          localStorage.setItem("currentUserName", data.name);
        }
      })
      .catch(() => {
        const cached = localStorage.getItem("currentUserName");
        if (cached) setUserName(cached);
      });
  }, [userId]);

  useEffect(() => {
    if (!selectedRecipe?.step_text) {
      setCleanedSteps([]);
      return;
    }

    let cancelled = false;
    setCleanedSteps([]);
    apiFetch<{ steps?: string[] }>("/clean_recipe_steps", {
      method: "POST",
      body: JSON.stringify({ text: selectedRecipe.step_text }),
    })
      .then((data) => {
        if (cancelled) {
          return;
        }
        const normalized = Array.isArray(data.steps) ? data.steps.filter((item) => typeof item === "string") : [];
        setCleanedSteps(normalized.map((item) => item.trim()).filter(Boolean));
      })
      .catch(() => {
        if (!cancelled) {
          setCleanedSteps([]);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedRecipe?.step_text]);

  const persistIngredients = (items: IngredientItem[]) => {
    const key = userId ? `ingredients_${userId}` : "ingredients";
    localStorage.setItem(key, JSON.stringify(items));
    setIngredients(items);
  };

  const fetchIngredientSuggestions = useCallback(
    async (keyword: string) => {
      const params = new URLSearchParams();
      const trimmed = keyword.trim();
      if (trimmed) {
        params.set("keyword", trimmed);
      }
      params.set("limit", "15");
      const queryString = params.toString();
      const endpoint = queryString ? `/search_ingredient?${queryString}` : "/search_ingredient";

      try {
        const data = await apiFetch<{ results?: string[] }>(endpoint);
        setSearchResults(data.results ?? []);
      } catch (error) {
        console.error("Ingredient search failed:", error);
        setSearchResults([]);
      }
    },
    []
  );

  const handleSearch = (value: string) => {
    setSearch(value);
    void fetchIngredientSuggestions(value);
  };

  const addIngredient = (name: string) => {
    if (ingredients.some((item) => item.name === name)) return;
    const updated = [...ingredients, { name, amount: "1" }];
    persistIngredients(updated);
    setSearch("");
    void fetchIngredientSuggestions("");
  };

  useEffect(() => {
    if (showModal) {
      setSearch("");
      void fetchIngredientSuggestions("");
    } else {
      setSearchResults([]);
    }
  }, [showModal, fetchIngredientSuggestions]);

  useEffect(() => {
    setVideoUrl(null);
    setVideoLoading(false);
  }, [selectedRecipe]);

  const changeAmount = (name: string, delta: number) => {
    const updated = ingredients.map((item) =>
      item.name === name
        ? (() => {
            const parsed = parseFloat(item.amount as string);
            if (Number.isNaN(parsed)) {
              return item; // 숫자가 아닌 경우(예: 50g)는 그대로 둠
            }
            const next = Math.max(1, parsed + delta);
            return { ...item, amount: next.toString() };
          })()
        : item
    );
    persistIngredients(updated);
  };

  const updateAmount = (name: string, value: string) => {
    const updated = ingredients.map((item) =>
      item.name === name ? { ...item, amount: value } : item
    );
    persistIngredients(updated);
  };

  const removeIngredient = (name: string) => {
    persistIngredients(ingredients.filter((item) => item.name !== name));
  };

  const saveFridgeToServer = async () => {
    if (!userId) {
      alert(TEXT.alerts.requireLoginSave);
      return;
    }
    try {
      await Promise.all(
        ingredients.map((item) =>
          apiFetch("/add_ingredient", {
            method: "POST",
            body: JSON.stringify({
              user_id: userId,
              name: item.name,
              amount: item.amount,
            }),
          })
        )
      );
      setSaveSuccessMessage(TEXT.alerts.saveSuccess);
    } catch (error) {
      console.error("Failed to save fridge:", error);
      alert(TEXT.alerts.saveFail);
    }
  };

  const handleRecommend = async () => {
    if (!userId) {
      alert(TEXT.alerts.requireLoginRecommend);
      return;
    }
    setLoading(true);
    try {
      const signature = buildIngredientSignature(ingredients);
      const seenRaw = localStorage.getItem(STORAGE_SEEN_RECOMMEND);
      let seenList: SeenRecipe[] = [];
      if (seenRaw) {
        try {
          const parsed = JSON.parse(seenRaw);
          if (Array.isArray(parsed)) {
            seenList = parsed
              .map((item) => {
                if (typeof item === "string" || typeof item === "number") {
                  return { id: String(item), signature: "", seenAt: 0 } as SeenRecipe;
                }
                return {
                  id: String(item.id),
                  signature: String(item.signature || ""),
                  seenAt: Number(item.seenAt) || 0,
                } as SeenRecipe;
              })
              .filter((item) => item.id);
          }
        } catch {
          seenList = [];
        }
      }

      const currentSeen = seenList.filter((item) => item.signature === signature);
      const excludeIds = currentSeen.map((item) => item.id);

      const data = await apiFetch<{
        recommendations?: RecommendationItem[];
        user_level?: string;
        ingredient_signature?: string;
      }>("/recommend", {
        method: "POST",
        body: JSON.stringify({
          user_id: userId,
          ingredients: ingredients.map((item) => ({
            name: item.name,
            amount: item.amount,
          })),
          exclude_ids: excludeIds,
          exclude_signature: signature,
        }),
      });
      const respSignature = data.ingredient_signature || signature;
      const incoming = (data.recommendations ?? []).map((item) => ({ ...item, selected: false }));

      const filtered = incoming.filter(
        (item) => !seenList.some((seen) => seen.signature === respSignature && seen.id === String(item.recipe_id))
      );
      const list = filtered.length > 0 ? filtered : incoming;

      const nextSeen = seenList
        .filter((item) => item.signature !== respSignature) // 다른 시그니처는 보존
        .concat(
          list.map(
            (item) =>
              ({
                id: String(item.recipe_id),
                signature: respSignature,
                seenAt: Date.now(),
              } as SeenRecipe)
          )
        );

      localStorage.setItem(STORAGE_SEEN_RECOMMEND, JSON.stringify(nextSeen));

      setRecommended(list);
      setLastRecommended(list);
      localStorage.setItem(STORAGE_LAST_RECOMMEND, JSON.stringify(list));
      setShowRecommendModal(true);
      if (data.user_level) {
        setUserLevelMessage(`${TEXT.alerts.userLevelPrefix}${data.user_level}${TEXT.alerts.userLevelSuffix}`);
      } else {
        setUserLevelMessage(null);
      }
    } catch (error) {
      console.error("Failed to load recommendations:", error);
      alert(TEXT.alerts.fetchFail);
    } finally {
      setLoading(false);
    }
  };

  const registerSelectedRecipes = async () => {
    if (!userId) {
      alert(TEXT.alerts.loginFirst);
      return;
    }
    const selected = recommended.filter((recipe) => recipe.selected);
    if (selected.length === 0) {
      alert(TEXT.alerts.selectAtLeastOne);
      return;
    }
    if (selected.some((recipe) => !recipe.recommend_id)) {
      alert(TEXT.alerts.missingRecommendId);
      return;
    }
    try {
      await Promise.all(
        selected.map((recipe) =>
          apiFetch("/save_selected_recipe", {
            method: "POST",
            body: JSON.stringify({
              user_id: userId,
              recommend_id: recipe.recommend_id,
              recipe_id: recipe.recipe_id,
            }),
          })
        )
      );
      alert(TEXT.alerts.registerSuccess);
      setShowRecommendModal(false);
      setUserLevelMessage(null);
      setRecommended([]);
    } catch (error) {
      console.error("Failed to register recipes:", error);
      alert(TEXT.alerts.registerFail);
    }
  };

  const resetIngredients = () => {
    if (window.confirm(TEXT.alerts.confirmReset)) {
      persistIngredients([]);
    }
  };

const RECIPE_SUFFIXES = ["전", "탕", "찌개", "볶음", "조림", "구이", "무침", "덮밥", "볶이", "국", "찜", "죽", "샐러드", "파스타"];

const extractIngredientKeywords = (text?: string): string[] => {
  if (!text) {
    return [];
  }
  try {
    const sanitized = text.replace(/'/g, '"');
    const parsed = JSON.parse(sanitized);
    if (!Array.isArray(parsed)) {
      return [];
    }
    const keywords: string[] = [];
    parsed.forEach((item) => {
      if (typeof item !== "string") return;
      const match = item.match(/[가-힣]+/);
      if (match) {
        const token = match[0];
        if (token && !keywords.includes(token)) {
          keywords.push(token);
        }
      }
    });
    return keywords;
  } catch {
    return [];
  }
};

const buildVideoSearchData = (
  title: string,
  ingredientFull?: string
): { queries: string[]; syllables: string[]; allowed: string[] } => {
  const normalized = title.trim();
  const noSpace = normalized.replace(/\s+/g, "");
  const baseQueries = new Set<string>([normalized, noSpace]);
  const syllableSet = new Set<string>(Array.from(noSpace));
  const allowedWords = new Set<string>();

  const suffix = RECIPE_SUFFIXES.find((word) => noSpace.endsWith(word)) ?? "";
  const ingredients = extractIngredientKeywords(ingredientFull);
  ingredients.forEach((word) => {
    if (word) allowedWords.add(word);
  });
  RECIPE_SUFFIXES.forEach((word) => allowedWords.add(word));

  const titleWords = normalized.match(/[가-힣]+/g) ?? [];
  titleWords.forEach((word) => allowedWords.add(word));

  if (suffix && ingredients.length >= 2) {
    const first = ingredients[0];
    const second = ingredients[1];
    [
      `${first}${second}${suffix}`,
      `${second}${first}${suffix}`,
      `${first} ${second} ${suffix}`,
      `${second} ${first} ${suffix}`,
    ].forEach((query) => baseQueries.add(query.trim()));
    syllableSet.add(first.charAt(0));
    syllableSet.add(second.charAt(0));
    syllableSet.add(suffix.charAt(0));
  }

  const queries = new Set<string>();
  baseQueries.forEach((value) => {
    const trimmed = value.trim();
    if (!trimmed) {
      return;
    }
    queries.add(`${trimmed} 레시피`.trim());
    const compact = trimmed.replace(/\s+/g, "");
    if (compact) {
      queries.add(`${compact}레시피`);
    }
  });

  return {
    queries: Array.from(queries).filter(Boolean),
    syllables: Array.from(syllableSet).filter(Boolean),
    allowed: Array.from(allowedWords).filter(Boolean),
  };
};

const handleWatchVideo = async () => {
    const title = selectedRecipe?.recipe_nm_ko?.trim();
    if (!title) {
      alert(TEXT.alerts.videoTitleMissing);
      return;
    }
    const { queries: candidates, syllables, allowed } = buildVideoSearchData(title, selectedRecipe?.ingredient_full);
    setVideoLoading(true);
    setVideoUrl(null);

    let success = false;
    for (const query of candidates) {
      try {
        const params = new URLSearchParams();
        params.set("q", query);
        if (syllables.length) {
          params.set("syllables", syllables.join(","));
        }
        if (allowed.length) {
          params.set("allowed", allowed.join(","));
        }
        const data = await apiFetch<{ embed_url?: string }>(`/youtube_shorts?${params.toString()}`);
        if (data.embed_url) {
          setVideoUrl(data.embed_url);
          success = true;
          break;
        }
      } catch (error) {
        console.error("Failed to fetch video:", error);
      }
    }

    if (!success) {
      alert(TEXT.alerts.videoFetchFail);
    }
    setVideoLoading(false);
};

  const handleShowLastRecommendations = () => {
    if (lastRecommended.length === 0) {
      return;
    }
    const resetSelections = lastRecommended.map((item) => ({ ...item, selected: false }));
    setRecommended(resetSelections);
    setShowRecommendModal(true);
    setUserLevelMessage(null);
  };

  if (showSplash) {
    return <SplashScreen onFinish={() => setShowSplash(false)} />;
  }

  return (
    <>
      <VideoBackgroundLayout contentClassName="text-[#6B2E00]" showHomeButton={false}>
      <header className="relative pt-6 pb-4 text-center">
        <button
          type="button"
          aria-label="열기"
          ref={quickMenuButtonRef}
          onClick={() => {
            const rect = quickMenuButtonRef.current?.getBoundingClientRect();
            if (rect) {
              setQuickMenuPos({ top: rect.top, left: rect.left });
            }
            setShowQuickMenu(true);
          }}
          className="absolute left-6 top-3 flex h-9 w-9 flex-col items-center justify-center gap-[6px] rounded-full bg-[#6B2E00] text-white shadow hover:bg-[#4c2100]"
        >
          <span className="block h-[2px] w-5 bg-white/80" />
          <span className="block h-[2px] w-5 bg-white/80" />
          <span className="block h-[2px] w-5 bg-white/80" />
        </button>
        <h1 className="text-xl font-extrabold tracking-wide">CookUS</h1>
        <nav className="mt-3 flex items-center justify-center gap-5 text-sm font-semibold">
          <Link to="/" className="hover:text-[#8B4000]">
            {TEXT.nav.fridge}
          </Link>
          <span>|</span>
          <Link to="/calendar" className="hover:text-[#8B4000]">
            {TEXT.nav.calendar}
          </Link>
          <span>|</span>
          <Link to="/dashboard" className="hover:text-[#8B4000]">
            {TEXT.nav.dashboard}
          </Link>
          <span>|</span>
          {user ? (
            <button onClick={logout} className="hover:text-[#8B4000]">
              {TEXT.nav.logout}
            </button>
          ) : (
            <Link to="/login" className="hover:text-[#8B4000]">
              {TEXT.nav.login}
            </Link>
          )}
        </nav>
        <Link
          to="/mypage"
          className="absolute right-6 top-3 flex items-center justify-center hover:text-[#8B4000] transition"
        >
          <UserCircleIcon className={`h-8 w-8 ${user ? "text-[#6B2E00]" : "text-gray-400"}`} />
        </Link>
      </header>

      <main className="flex-1 px-6 pb-8 flex flex-col">
        <div className="mt-3 text-center text-white drop-shadow-[0_4px_8px_rgba(0,0,0,0.35)]">
          <p className="text-2xl font-extrabold tracking-tight">{TEXT.tagline.line1}</p>
          <p className="text-2xl font-extrabold tracking-tight">{TEXT.tagline.line2}</p>
        </div>

        <div className="mt-6 flex justify-center">
          <button
            type="button"
            onClick={() => setShowFridge((prev) => !prev)}
            className="w-full max-w-[240px] rounded-[28px] bg-white/85 px-6 py-4 text-center shadow-[0_12px_25px_rgba(107,46,0,0.2)] backdrop-blur-sm transition hover:bg-white"
          >
            <span className="block text-sm font-medium tracking-wide uppercase">
              {TEXT.fridgeCard.title}
            </span>
            <span className="mt-1 block text-xl font-extrabold">
              {`${TEXT.fridgeCard.countPrefix}${ingredients.length}`}
            </span>
          </button>
        </div>

        {showFridge && (
          <div className="mt-5 rounded-3xl bg-white/85 p-5 text-sm text-[#6B2E00] shadow-inner backdrop-blur">
            {ingredients.length === 0 ? (
              <p className="text-center text-[#6B2E00]/80">{TEXT.fridgeCard.empty}</p>
            ) : (
              <ul className="space-y-2">
                {ingredients.map((item) => (
                  <li key={item.name} className="flex items-center justify-between">
                    <span>{item.name}</span>
                    <div className="flex items-center gap-2 text-xs font-semibold">
                      <button
                        type="button"
                        onClick={() => changeAmount(item.name, -1)}
                        className="h-6 w-6 rounded-full bg-[#F7D98A] text-[#6B2E00]"
                      >
                        -
                      </button>
                      <span className="min-w-[24px] text-center">{item.amount}</span>
                      <button
                        type="button"
                        onClick={() => changeAmount(item.name, 1)}
                        className="h-6 w-6 rounded-full bg-[#F7D98A] text-[#6B2E00]"
                      >
                        +
                      </button>
                      <button
                        type="button"
                        onClick={() => removeIngredient(item.name)}
                        className="ml-2 text-red-500"
                      >
                        {TEXT.fridgeCard.delete}
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
            <div className="mt-4 flex justify-center">
              <button
                type="button"
                onClick={saveFridgeToServer}
                className="rounded-2xl bg-[#6B2E00] px-5 py-2 text-sm font-semibold text-white shadow hover:bg-[#4c2100] transition"
              >
                {TEXT.fridgeCard.save}
              </button>
            </div>
          </div>
        )}

        <div className="mt-auto space-y-6 pb-2">
          <div className="flex justify-center">
            <button
              type="button"
              onClick={handleShowLastRecommendations}
              disabled={lastRecommended.length === 0}
              className="w-full max-w-[420px] rounded-2xl border border-[#E7C9A1] bg-white/80 px-3 py-3 text-sm font-semibold text-[#6B2E00] shadow disabled:opacity-40"
            >
              {TEXT.buttons.history}
            </button>
          </div>
          <div className="grid grid-cols-3 gap-3 text-center text-sm font-semibold">
            <button
              type="button"
              onClick={() => setShowModal(true)}
              className="rounded-2xl bg-[#F7D98A]/90 px-3 py-3 text-[#6B2E00] shadow hover:bg-[#f1d082]"
            >
              {TEXT.buttons.add}
            </button>
            <button
              type="button"
              onClick={handleRecommend}
              className="rounded-2xl bg-[#F2994A] px-3 py-3 text-white shadow hover:bg-[#f08a29]"
            >
              {TEXT.buttons.recommend}
            </button>
            <button
              type="button"
              onClick={resetIngredients}
              className="rounded-2xl bg-[#F7D98A]/90 px-3 py-3 text-[#6B2E00] shadow hover:bg-[#f1d082]"
            >
              {TEXT.buttons.reset}
            </button>
          </div>
          <div className="flex justify-center">
            <Link
              to="/receipt-upload"
              className="w-full max-w-[420px] rounded-2xl bg-[#FFB15E] px-4 py-3 text-center text-base font-bold text-white shadow hover:bg-[#ff9d3d] transition"
            >
              {TEXT.buttons.receiptUpload}
            </Link>
          </div>

          {loading && (
            <div className="text-center text-sm font-semibold text-[#6B2E00]">
              {TEXT.loading}
            </div>
          )}

          <footer className="rounded-3xl bg-[#F6E8C9]/90 px-6 py-6 text-center text-xs text-[#6B2E00] shadow-inner">
            <p className="text-sm font-semibold">{TEXT.footer.title}</p>
            <p className="mt-3 flex justify-center gap-4 font-medium">
              <Link to="/about" className="hover:text-[#8B4000]">
                {TEXT.footer.about}
              </Link>
              <Link to="/faq" className="hover:text-[#8B4000]">
                {TEXT.footer.faq}
              </Link>
            </p>
            <p className="mt-3">{TEXT.footer.company}</p>
            <p>{TEXT.footer.contact}</p>
            <p>{TEXT.footer.email}</p>
            <p className="mt-2">{TEXT.footer.policy}</p>
          </footer>
        </div>
      </main>
    </VideoBackgroundLayout>

      {showQuickMenu && (
        <div className="fixed inset-0 z-50">
          <button
            type="button"
            className="absolute inset-0 bg-black/25"
            aria-label="오버레이 닫기"
            onClick={() => setShowQuickMenu(false)}
          />
          <div
            className="absolute w-[280px] max-w-[85%] rounded-2xl bg-[#FFF2D9] p-6 text-[#6B2E00] shadow-2xl animate-slide-in-left"
            style={{ top: `${quickMenuPos.top}px`, left: `${quickMenuPos.left}px` }}
          >
            <button
              type="button"
              onClick={() => setShowQuickMenu(false)}
              className="absolute right-5 top-4 text-xl font-bold text-[#6B2E00]"
              aria-label="닫기"
            >
              &times;
            </button>
            <h3 className="text-lg font-extrabold">바로가기</h3>
            <p className="mt-1 text-sm text-[#6B2E00]/80">
              이벤트 · 게시판 · 나의 진행을 빠르게 확인하세요.
            </p>

            <div className="mt-5 space-y-3">
              <button
                type="button"
                onClick={() => {
                  setShowQuickMenu(false);
                  navigate("/events");
                }}
                className="w-full rounded-2xl bg-[#F7D98A]/90 px-4 py-3 text-left text-sm font-semibold shadow hover:bg-[#f1d082]"
              >
                이벤트 / 대회
                <span className="mt-1 block text-xs font-medium text-[#6B2E00]/80">
                  일정 · 참가 · 결과 확인 메뉴로 이동
                </span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowQuickMenu(false);
                  navigate("/board");
                }}
                className="w-full rounded-2xl bg-[#FFB15E] px-4 py-3 text-left text-sm font-semibold text-white shadow hover:bg-[#ff9d3d]"
              >
                게시판
                <span className="mt-1 block text-xs font-medium text-white/90">
                  글 작성 · 좋아요 · 인기글 모아보기
                </span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowQuickMenu(false);
                  navigate("/progress");
                }}
                className="w-full rounded-2xl border border-[#E7C9A1] bg-white px-4 py-3 text-left text-sm font-semibold text-[#6B2E00] shadow"
              >
                나의 진행
                <span className="mt-1 block text-xs font-medium text-[#6B2E00]/80">
                  목표 진행도 · 보상 캐시 확인
                </span>
              </button>
            </div>

            <p className="mt-4 text-[11px] text-[#6B2E00]/70">
              상세 화면은 별도 페이지에서 확장 예정입니다.
            </p>
          </div>
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-3">
          <div className="relative w-[360px] rounded-3xl bg-[#FFF2D9] p-6 shadow-2xl">
            <button
              type="button"
              onClick={() => setShowModal(false)}
              className="absolute right-6 top-5 text-lg text-[#6B2E00]"
            >
              &times;
            </button>
            <h2 className="mb-4 text-center text-lg font-bold text-[#6B2E00]">
              {TEXT.ingredientModal.title}
            </h2>
            <input
              type="text"
              value={search}
              onChange={(event) => handleSearch(event.target.value)}
              placeholder={TEXT.ingredientModal.placeholder}
              className="mb-3 w-full rounded-xl border border-[#D7B78A] p-2 text-center"
            />
            {searchResults.length > 0 ? (
              <ul className="mb-3 max-h-36 overflow-y-auto rounded-xl border border-[#D7B78A] bg-white p-2 text-left">
                {searchResults.map((item) => (
                  <li
                    key={item}
                    onClick={() => addIngredient(item)}
                    className="cursor-pointer rounded px-2 py-1 hover:bg-[#F7D98A]"
                  >
                    {item}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mb-3 text-center text-sm text-[#6B2E00]">
                {TEXT.ingredientModal.noResult}
              </p>
            )}

            <div className="space-y-2">
              {ingredients.map((item) => (
                <div
                  key={item.name}
                  className="flex items-center justify-between rounded-xl bg-[#FFEFC3] px-3 py-2"
                >
                  <span className="font-medium">{item.name}</span>
                  <div className="flex items-center gap-1">
                    <button onClick={() => changeAmount(item.name, -1)} className="px-2">
                      -
                    </button>
                    <input
                      type="text"
                      value={item.amount}
                      onChange={(e) => updateAmount(item.name, e.target.value)}
                      className="w-20 rounded border border-[#D7B78A] px-2 py-1 text-center text-xs"
                      placeholder="예: 50g"
                    />
                    <button onClick={() => changeAmount(item.name, 1)} className="px-2">
                      +
                    </button>
                    <button
                      onClick={() => removeIngredient(item.name)}
                      className="ml-2 text-red-500"
                    >
                      {TEXT.ingredientModal.delete}
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-5 flex justify-center gap-4">
              <button
                type="button"
                onClick={() => {
                  setShowModal(false);
                  saveFridgeToServer();
                }}
                className="rounded-xl bg-[#6B2E00] px-4 py-2 text-white"
              >
                {TEXT.ingredientModal.save}
              </button>
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className="rounded-xl bg-white px-4 py-2 text-[#6B2E00]"
              >
                {TEXT.ingredientModal.cancel}
              </button>
            </div>
          </div>
        </div>
      )}

      {showRecommendModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-3">
          <div className="relative w-[400px] max-h-[90vh] overflow-y-auto rounded-3xl bg-[#FFF2D9] p-6 shadow-2xl">
            <button
              type="button"
              onClick={() => {
                setShowRecommendModal(false);
                setUserLevelMessage(null);
                setRecommended([]);
              }}
              className="absolute right-6 top-5 text-lg text-[#6B2E00]"
            >
              &times;
            </button>
            <h2 className="mb-5 text-center text-xl font-extrabold text-[#6B2E00]">
              {TEXT.recommendModal.title}
            </h2>
            {userLevelMessage && (
              <p className="mb-4 rounded-2xl bg-white/70 px-4 py-2 text-center text-sm text-[#6B2E00] shadow-inner">
                {userLevelMessage}
              </p>
            )}
            <div className="grid grid-cols-1 gap-4">
              {recommended.length === 0 && (
                <p className="text-center text-sm text-[#6B2E00]">
                  {TEXT.recommendModal.empty}
                </p>
              )}
              {recommended.map((recipe, index) => (
                <div
                  key={recipe.recipe_id ?? index}
                  className={`cursor-pointer rounded-2xl bg-[#FFF8E1] p-4 shadow-md transition ${
                    recipe.selected ? "border-2 border-[#F2994A]" : "border border-transparent"
                  }`}
                  onClick={() =>
                    setRecommended((prev) =>
                      prev.map((item, idx) =>
                        idx === index ? { ...item, selected: !item.selected } : item
                      )
                    )
                  }
                >
                  <h3 className="mb-2 text-md font-bold text-[#6B2E00]">
                    {recipe.recipe_nm_ko ?? TEXT.recommendModal.title}
                  </h3>
                  <p className="text-xs text-[#6B2E00]/80">
                    {TEXT.detailModal.difficulty} {recipe.level_nm ?? TEXT.detailModal.infoNone} /{" "}
                    {TEXT.detailModal.cookingTime} {recipe.cooking_time ?? TEXT.detailModal.infoNone}
                  </p>
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      setSelectedRecipe(recipe);
                    }}
                    className="mt-3 w-full rounded-xl bg-[#F2994A] py-2 text-sm font-semibold text-white shadow hover:bg-[#f08a29] transition"
                  >
                    {TEXT.recommendModal.detail}
                  </button>
                </div>
              ))}
            </div>

            {recommended.length > 0 && (
              <div className="mt-6 flex justify-center gap-4">
                <button
                  type="button"
                  onClick={registerSelectedRecipes}
                  className="rounded-xl bg-[#F2994A] px-5 py-2 text-white shadow hover:bg-[#f08a29] transition"
                >
                  {TEXT.recommendModal.register}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowRecommendModal(false);
                    setUserLevelMessage(null);
                    setRecommended([]);
                  }}
                  className="rounded-xl bg-white px-5 py-2 text-[#6B2E00] shadow"
                >
                  {TEXT.recommendModal.close}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {selectedRecipe && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-3">
          <div className="relative w-[360px] max-h-[520px] overflow-y-auto rounded-3xl bg-[#FFF6E0] p-6 shadow-xl">
            <button
              type="button"
              onClick={() => setSelectedRecipe(null)}
              className="absolute right-6 top-5 text-lg text-[#6B2E00]"
            >
              &times;
            </button>
            <h2 className="mb-3 text-center text-lg font-extrabold text-[#6B2E00]">
              {selectedRecipe.recipe_nm_ko ?? TEXT.recommendModal.title}
            </h2>
            <div className="mb-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-[#6B2E00]/80">
              <span>
                <b>{TEXT.detailModal.cookingTime}</b>{" "}
                {selectedRecipe.cooking_time ?? TEXT.detailModal.infoNone}
              </span>
              <span>
                <b>{TEXT.detailModal.difficulty}</b>{" "}
                {selectedRecipe.level_nm ?? TEXT.detailModal.infoNone}
              </span>
            </div>
            {ingredientList.length > 0 && (
              <>
                <p className="mt-3 text-sm font-semibold text-[#6B2E00]">{TEXT.detailModal.ingredients}</p>
                <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-[#6B2E00]/80">
                  {ingredientList.map((item, index) => (
                    <li key={`ingredient-${index}`}>{item}</li>
                  ))}
                </ul>
              </>
            )}
            {stepsToRender.length > 0 ? (
              <>
                <p className="mt-4 text-sm font-semibold text-[#6B2E00]">{TEXT.detailModal.steps}</p>
                <ol className="mt-1 list-decimal space-y-1 pl-5 text-sm text-[#6B2E00]/80">
                  {stepsToRender.map((step, index) => (
                    <li key={`step-${index}`}>{step}</li>
                  ))}
                </ol>
              </>
            ) : (
              <p className="text-sm text-[#6B2E00]/80">{TEXT.detailModal.methodNone}</p>
            )}
            <div className="mt-4 flex justify-center gap-3">
              <button
                type="button"
                onClick={() => setSelectedRecipe(null)}
                className="rounded-xl bg-[#F2994A] px-4 py-2 text-white shadow hover:bg-[#f08a29] transition"
              >
                {TEXT.detailModal.close}
              </button>
              <button
                type="button"
                onClick={handleWatchVideo}
                className="rounded-xl bg-[#FF9F43] px-4 py-2 text-white shadow hover:bg-[#ff9127] transition disabled:opacity-60"
                disabled={videoLoading}
              >
                {videoLoading ? TEXT.detailModal.loadingVideo : TEXT.detailModal.youtube}
              </button>
            </div>
            {videoUrl && (
              <div
                className="mt-4 w-full overflow-hidden rounded-2xl bg-black"
                style={{ aspectRatio: "16 / 9" }}
              >
                <iframe
                  src={videoUrl}
                  title="추천 영상"
                  allow="autoplay; encrypted-media"
                  allowFullScreen
                  className="h-full w-full"
                />
              </div>
            )}
          </div>
        </div>
      )}

      {saveSuccessMessage && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-3">
          <div className="w-[320px] rounded-[32px] bg-[#FFF8EC] px-6 py-8 text-center text-[#6B2E00] shadow-[0_20px_45px_rgba(107,46,0,0.35)]">
            <p className="text-xs font-semibold tracking-[0.3em] text-[#B56B1D]">COOKUS</p>
            <p className="mt-3 text-xl font-extrabold">{saveSuccessMessage}</p>
            <button
              type="button"
              onClick={() => setSaveSuccessMessage(null)}
              className="mt-6 rounded-full bg-[#6B2E00] px-6 py-2 text-white shadow hover:bg-[#4c2100]"
            >
              확인
            </button>
          </div>
        </div>
      )}
    </>
  );
}
