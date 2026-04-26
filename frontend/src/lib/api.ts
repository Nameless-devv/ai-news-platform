import { NewsItem, NewsListResponse, TrendingTopic, GenerateResponse } from "@/types/news";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const BASE = `${API_URL}/api/v1`;

async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export interface NewsQuery {
  page?: number;
  page_size?: number;
  category?: string;
  country?: string;
  search?: string;
}

export const api = {
  getNews: (q: NewsQuery = {}): Promise<NewsListResponse> => {
    const params = new URLSearchParams();
    if (q.page) params.set("page", String(q.page));
    if (q.page_size) params.set("page_size", String(q.page_size));
    if (q.category) params.set("category", q.category);
    if (q.country) params.set("country", q.country);
    if (q.search) params.set("search", q.search);
    return fetchJSON(`/news?${params}`);
  },

  aiSearch: (q: string, page = 1, page_size = 20, category?: string, country?: string): Promise<NewsListResponse> => {
    const params = new URLSearchParams({ q, page: String(page), page_size: String(page_size) });
    if (category) params.set("category", category);
    if (country) params.set("country", country);
    return fetchJSON(`/news/ai-search?${params}`);
  },

  getNewsById: (id: number): Promise<NewsItem> => fetchJSON(`/news/${id}`),

  getTrending: (): Promise<TrendingTopic[]> => fetchJSON("/news/trending"),

  generate: (text: string, language = "uz"): Promise<GenerateResponse> =>
    fetchJSON("/news/generate", {
      method: "POST",
      body: JSON.stringify({ text, language }),
    }),

  addBookmark: (news_id: number, session_id: string) =>
    fetchJSON("/news/bookmarks", {
      method: "POST",
      body: JSON.stringify({ news_id, session_id }),
    }),

  getBookmarks: (session_id: string): Promise<NewsItem[]> =>
    fetchJSON(`/news/bookmarks/${session_id}`),

  removeBookmark: (session_id: string, news_id: number) =>
    fetchJSON(`/news/bookmarks/${session_id}/${news_id}`, { method: "DELETE" }),
};
