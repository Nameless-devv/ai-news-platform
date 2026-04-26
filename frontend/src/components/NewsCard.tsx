"use client";
import Link from "next/link";
import Image from "next/image";
import { formatDistanceToNow } from "date-fns";
import { Bookmark, BookmarkCheck, ExternalLink, Tag, TrendingUp } from "lucide-react";
import clsx from "clsx";
import { NewsItem } from "@/types/news";

const CATEGORY_COLORS: Record<string, string> = {
  politics: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
  economy: "bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300",
  technology: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  sports: "bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-300",
  culture: "bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-300",
  health: "bg-teal-100 text-teal-700 dark:bg-teal-950 dark:text-teal-300",
  world: "bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300",
  society: "bg-pink-100 text-pink-700 dark:bg-pink-950 dark:text-pink-300",
  environment: "bg-lime-100 text-lime-700 dark:bg-lime-950 dark:text-lime-300",
  science: "bg-cyan-100 text-cyan-700 dark:bg-cyan-950 dark:text-cyan-300",
};

const SENTIMENT_DOT: Record<string, string> = {
  positive: "bg-green-500",
  negative: "bg-red-500",
  neutral: "bg-gray-400",
};

interface Props {
  item: NewsItem;
  isBookmarked: boolean;
  onBookmark: (id: number, item: NewsItem) => void;
  featured?: boolean;
}

export function NewsCard({ item, isBookmarked, onBookmark, featured = false }: Props) {
  const headline = item.ai_headlines?.[0] || item.title || "Untitled";
  const timeAgo = item.published_at
    ? formatDistanceToNow(new Date(item.published_at), { addSuffix: true })
    : "";

  return (
    <article
      className={clsx(
        "card group overflow-hidden flex flex-col animate-slide-up",
        featured ? "md:flex-row" : ""
      )}
    >
      {/* Image */}
      {item.image_url && (
        <div className={clsx("relative overflow-hidden bg-gray-100 dark:bg-zinc-800",
          featured ? "md:w-80 md:shrink-0 h-48 md:h-auto" : "h-48"
        )}>
          <Image
            src={item.image_url}
            alt={headline}
            fill
            sizes={featured ? "320px" : "400px"}
            className="object-cover group-hover:scale-105 transition-transform duration-500"
            unoptimized
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent" />
        </div>
      )}

      {/* Content */}
      <div className="flex flex-col flex-1 p-5">
        {/* Meta row */}
        <div className="flex items-center gap-2 flex-wrap mb-3">
          {item.category && (
            <span className={clsx("badge text-xs", CATEGORY_COLORS[item.category] || "bg-gray-100 text-gray-600")}>
              {item.category}
            </span>
          )}
          {item.source_country === "UZ" && (
            <span className="badge bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
              O'zbekiston
            </span>
          )}
          {item.sentiment && (
            <span className={clsx("w-2 h-2 rounded-full", SENTIMENT_DOT[item.sentiment])} title={item.sentiment} />
          )}
          <span className="text-xs text-gray-400 dark:text-zinc-500 ml-auto">{timeAgo}</span>
        </div>

        {/* AI Headline */}
        <Link href={`/news/${item.id}`} className="group/link">
          <h2 className={clsx(
            "font-semibold text-gray-900 dark:text-white mb-2",
            "group-hover/link:text-blue-600 dark:group-hover/link:text-blue-400 transition-colors",
            featured ? "text-xl leading-snug" : "text-base leading-snug line-clamp-2"
          )}>
            {headline}
          </h2>
        </Link>

        {/* AI Summary */}
        {item.summary && (
          <p className="text-sm text-gray-600 dark:text-zinc-400 line-clamp-2 mb-3 flex-1">
            {item.summary}
          </p>
        )}

        {/* Tags */}
        {item.tags?.length > 0 && (
          <div className="flex items-center gap-1.5 flex-wrap mb-3">
            <Tag className="w-3 h-3 text-gray-400" />
            {item.tags.slice(0, 3).map((tag) => (
              <span key={tag} className="text-xs text-gray-500 dark:text-zinc-500">
                #{tag}
              </span>
            ))}
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between pt-3 border-t border-gray-100 dark:border-zinc-800">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-gray-500 dark:text-zinc-500">
              {item.source}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => onBookmark(item.id, item)}
              className={clsx(
                "p-1.5 rounded-lg transition-colors",
                isBookmarked
                  ? "text-blue-600 bg-blue-50 dark:bg-blue-950"
                  : "text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-950"
              )}
              title={isBookmarked ? "Saqlangan" : "Saqlash"}
            >
              {isBookmarked ? <BookmarkCheck className="w-4 h-4" /> : <Bookmark className="w-4 h-4" />}
            </button>
            {item.url && (
              <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="p-1.5 rounded-lg text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-950 transition-colors"
                title="Asl manbaga o'tish"
              >
                <ExternalLink className="w-4 h-4" />
              </a>
            )}
          </div>
        </div>
      </div>
    </article>
  );
}
