"use client";
import { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { RefreshCw, Wifi, WifiOff, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { NewsItem } from "@/types/news";
import { NewsCard } from "./NewsCard";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useBookmarks } from "@/hooks/useBookmarks";
import { TrendingSidebar } from "./TrendingSidebar";

const POLL_INTERVAL = 10_000;

export function NewsFeed() {
  const searchParams = useSearchParams();
  const [items, setItems] = useState<NewsItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasNext, setHasNext] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [newCount, setNewCount] = useState(0);
  const [backendDown, setBackendDown] = useState(false);
  const { bookmarked, toggle } = useBookmarks();
  // Wrap toggle so NewsCard's (id, item) signature matches hook's (id, item?)
  const handleBookmark = (id: number, item: import("@/types/news").NewsItem) => toggle(id, item);

  const category = searchParams.get("category") || undefined;
  const country = searchParams.get("country") || undefined;
  const search = searchParams.get("search") || undefined;
  const aiSearch = searchParams.get("ai_search") || undefined;

  const loadNews = useCallback(
    async (p = 1, append = false) => {
      try {
        const data = aiSearch
          ? await api.aiSearch(aiSearch, p, 20, category, country)
          : await api.getNews({ page: p, page_size: 20, category, country, search });
        setItems((prev) => (append ? [...prev, ...data.items] : data.items));
        setTotal(data.total);
        setHasNext(data.has_next);
        setPage(p);
        setBackendDown(false);
      } catch {
        setBackendDown(true);
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [category, country, search, aiSearch]
  );

  // Initial load
  useEffect(() => {
    setLoading(true);
    setNewCount(0);
    loadNews(1, false);
  }, [loadNews]);

  // Polling fallback every 10s
  useEffect(() => {
    const id = setInterval(() => {
      setNewCount((c) => c + 1);
    }, POLL_INTERVAL);
    return () => clearInterval(id);
  }, []);

  // WebSocket for real-time push
  useWebSocket(useCallback((event) => {
    if (event === "connected") setWsConnected(true);
    if (event === "pong") setWsConnected(true);
    if (event === "new_articles") setNewCount((c) => c + 1);
  }, []));

  const refresh = () => {
    setLoading(true);
    setNewCount(0);
    loadNews(1, false);
  };

  const loadMore = () => {
    setLoadingMore(true);
    loadNews(page + 1, true);
  };

  if (loading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 9 }).map((_, i) => (
          <div key={i} className="card h-64 animate-pulse bg-gray-200 dark:bg-zinc-800" />
        ))}
      </div>
    );
  }

  return (
    <div className="flex gap-6">
      {/* Main feed */}
      <div className="flex-1 min-w-0">
        {/* Header bar */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-gray-900 dark:text-white capitalize flex items-center gap-2">
              {aiSearch ? (
                <><Sparkles className="w-5 h-5 text-blue-500 shrink-0" /> AI: &ldquo;{aiSearch}&rdquo;</>
              ) : search ? `"${search}" natijalari`
                : country === "UZ" ? "🇺🇿 O'zbekiston yangiliklari"
                : country === "GLOBAL" ? "🌍 Dunyo yangiliklari"
                : category === "sports" ? "⚽ Sport yangiliklari"
                : category === "technology" ? "💻 Texnologiya yangiliklari"
                : category === "politics" ? "🏛️ Siyosat"
                : category === "economy" ? "📈 Iqtisodiyot"
                : category === "health" ? "🏥 Salomatlik"
                : category === "science" ? "🔬 Fan"
                : category === "culture" ? "🎭 Madaniyat"
                : category ? category
                : "Barcha yangiliklar"}
            </h1>
            <span className="text-sm text-gray-400 dark:text-zinc-500">{total.toLocaleString()} ta</span>
          </div>
          <div className="flex items-center gap-2">
            {wsConnected
              ? <Wifi className="w-4 h-4 text-green-500 animate-pulse-dot" />
              : <WifiOff className="w-4 h-4 text-gray-400" />
            }
            <button onClick={refresh} className="btn-ghost gap-1.5 text-sm">
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
              Yangilash
            </button>
          </div>
        </div>

        {/* New articles banner */}
        {newCount > 0 && (
          <button
            onClick={refresh}
            className="w-full mb-4 py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium
                       rounded-xl transition-colors animate-fade-in flex items-center justify-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Yangi maqolalar mavjud — bosing!
          </button>
        )}

        {backendDown ? (
          <div className="text-center py-24">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-red-100 dark:bg-red-950 rounded-2xl mb-4">
              <WifiOff className="w-8 h-8 text-red-500" />
            </div>
            <p className="text-lg font-semibold text-gray-800 dark:text-white mb-1">Backend ulanmagan</p>
            <p className="text-sm text-gray-500 dark:text-zinc-500 mb-6">
              API serveri ishlamayapti (<code className="bg-gray-100 dark:bg-zinc-800 px-1.5 py-0.5 rounded text-xs">localhost:8000</code>)
            </p>
            <div className="inline-block text-left bg-gray-50 dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 rounded-xl p-4 text-sm font-mono text-gray-700 dark:text-zinc-300 space-y-1">
              <p className="text-gray-400 dark:text-zinc-500 text-xs mb-2"># Backendni ishga tushirish:</p>
              <p>cd ai-news-platform</p>
              <p>cp .env.example .env</p>
              <p className="text-yellow-600 dark:text-yellow-400"># .env ga OPENAI_API_KEY qo'shing</p>
              <p>docker compose up -d</p>
            </div>
            <button onClick={refresh} className="btn-primary mt-6">
              <RefreshCw className="w-4 h-4" /> Qayta urinish
            </button>
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-20 text-gray-400 dark:text-zinc-500">
            <p className="text-lg font-medium">Yangilik topilmadi</p>
            <p className="text-sm mt-1">Boshqa qidiruv so'zini sinab ko'ring</p>
          </div>
        ) : (
          <>
            {/* Featured first item */}
            {items[0] && (
              <div className="mb-4">
                <NewsCard
                  item={items[0]}
                  isBookmarked={bookmarked.has(items[0].id)}
                  onBookmark={handleBookmark}
                  featured
                />
              </div>
            )}
            {/* Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {items.slice(1).map((item) => (
                <NewsCard
                  key={item.id}
                  item={item}
                  isBookmarked={bookmarked.has(item.id)}
                  onBookmark={handleBookmark}
                />
              ))}
            </div>

            {hasNext && (
              <div className="mt-8 text-center">
                <button
                  onClick={loadMore}
                  disabled={loadingMore}
                  className="btn-primary px-8 py-3"
                >
                  {loadingMore ? (
                    <><RefreshCw className="w-4 h-4 animate-spin" /> Yuklanmoqda...</>
                  ) : "Ko'proq ko'rsatish"}
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Sidebar */}
      <aside className="hidden lg:block w-72 shrink-0">
        <TrendingSidebar />
      </aside>
    </div>
  );
}
