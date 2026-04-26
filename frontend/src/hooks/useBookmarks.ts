"use client";
import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { NewsItem } from "@/types/news";

const SESSION_KEY = "ainews_session";

export function getSessionId(): string {
  if (typeof window === "undefined") return "";
  let id = localStorage.getItem(SESSION_KEY);
  if (!id) {
    id = `sess_${Math.random().toString(36).slice(2)}_${Date.now()}`;
    localStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

export function useBookmarks() {
  const [items, setItems] = useState<NewsItem[]>([]);
  const [bookmarked, setBookmarked] = useState<Set<number>>(new Set());
  const sessionId = typeof window !== "undefined" ? getSessionId() : "";

  useEffect(() => {
    if (!sessionId) return;
    api.getBookmarks(sessionId)
      .then((fetched) => {
        setItems(fetched);
        setBookmarked(new Set(fetched.map((i) => i.id)));
      })
      .catch(() => {});
  }, [sessionId]);

  const toggle = useCallback(
    async (newsId: number, item?: NewsItem) => {
      if (!sessionId) return;
      if (bookmarked.has(newsId)) {
        // Optimistically remove
        setBookmarked((prev) => { const s = new Set(prev); s.delete(newsId); return s; });
        setItems((prev) => prev.filter((i) => i.id !== newsId));
        await api.removeBookmark(sessionId, newsId).catch(() => {
          // Revert on error
          setBookmarked((prev) => new Set(prev).add(newsId));
          if (item) setItems((prev) => [item, ...prev]);
        });
      } else {
        // Optimistically add
        setBookmarked((prev) => new Set(prev).add(newsId));
        if (item) setItems((prev) => [item, ...prev]);
        await api.addBookmark(newsId, sessionId).catch(() => {
          // Revert on error
          setBookmarked((prev) => { const s = new Set(prev); s.delete(newsId); return s; });
          setItems((prev) => prev.filter((i) => i.id !== newsId));
        });
      }
    },
    [bookmarked, sessionId]
  );

  return { bookmarked, bookmarkedItems: items, toggle };
}
