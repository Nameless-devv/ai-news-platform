"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { TrendingUp, Flame } from "lucide-react";
import { api } from "@/lib/api";
import { TrendingTopic } from "@/types/news";

const ICONS = ["🔥", "⚡", "📈", "🌟", "💡", "🎯", "🚀", "🌍", "🏆", "🔬"];

export function TrendingSidebar() {
  const [topics, setTopics] = useState<TrendingTopic[]>([]);

  useEffect(() => {
    api.getTrending().then(setTopics).catch(() => {});
    const id = setInterval(() => {
      api.getTrending().then(setTopics).catch(() => {});
    }, 60_000);
    return () => clearInterval(id);
  }, []);

  if (topics.length === 0) return null;

  return (
    <div className="card p-5 sticky top-24">
      <div className="flex items-center gap-2 mb-4">
        <Flame className="w-5 h-5 text-orange-500" />
        <h2 className="font-semibold text-gray-900 dark:text-white">Trend mavzular</h2>
      </div>
      <div className="space-y-2">
        {topics.map((topic, i) => (
          <Link
            key={topic.topic}
            href={topic.category ? `/?category=${topic.category}` : "/"}
            className="flex items-center justify-between p-2.5 rounded-xl
                       hover:bg-gray-50 dark:hover:bg-zinc-800 transition-colors group"
          >
            <div className="flex items-center gap-2.5">
              <span className="text-lg leading-none">{ICONS[i] || "📰"}</span>
              <div>
                <p className="text-sm font-medium text-gray-800 dark:text-zinc-200 capitalize group-hover:text-blue-600 dark:group-hover:text-blue-400">
                  {topic.topic}
                </p>
                <p className="text-xs text-gray-400 dark:text-zinc-500">{topic.count} maqola</p>
              </div>
            </div>
            <TrendingUp className="w-3.5 h-3.5 text-gray-300 dark:text-zinc-600 group-hover:text-blue-500" />
          </Link>
        ))}
      </div>
    </div>
  );
}
