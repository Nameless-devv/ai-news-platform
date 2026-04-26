"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { format } from "date-fns";
import {
  ArrowLeft, ExternalLink, Tag, Clock, Globe,
  Bookmark, BookmarkCheck, Share2, TrendingUp
} from "lucide-react";
import clsx from "clsx";
import { api } from "@/lib/api";
import { NewsItem } from "@/types/news";
import { useBookmarks } from "@/hooks/useBookmarks";

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

function decodeHtml(html: string): string {
  return html
    .replace(/&nbsp;/g, " ")
    .replace(/&laquo;/g, "«")
    .replace(/&raquo;/g, "»")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&mdash;/g, "—")
    .replace(/&ndash;/g, "–")
    .replace(/&hellip;/g, "…");
}

function stripAndDecodeHtml(html: string): string {
  const withBreaks = html
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/p>/gi, "\n\n")
    .replace(/<\/div>/gi, "\n")
    .replace(/<\/li>/gi, "\n");
  const stripped = withBreaks.replace(/<[^>]+>/g, "");
  return decodeHtml(stripped).trim();
}

export default function NewsDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = Number(params.id);
  const [item, setItem] = useState<NewsItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [copied, setCopied] = useState(false);
  const { bookmarked, toggle } = useBookmarks();

  useEffect(() => {
    api.getNewsById(id)
      .then(setItem)
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false));
  }, [id]);

  const share = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto animate-pulse space-y-4">
        <div className="h-4 w-24 bg-gray-200 dark:bg-zinc-800 rounded" />
        <div className="h-8 w-3/4 bg-gray-200 dark:bg-zinc-800 rounded" />
        <div className="h-72 bg-gray-200 dark:bg-zinc-800 rounded-2xl" />
        <div className="space-y-2">
          {[1,2,3,4].map(i => <div key={i} className="h-4 bg-gray-200 dark:bg-zinc-800 rounded w-full" />)}
        </div>
      </div>
    );
  }

  if (notFound || !item) {
    return (
      <div className="max-w-3xl mx-auto text-center py-20">
        <p className="text-5xl mb-4">📭</p>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Maqola topilmadi</h1>
        <p className="text-gray-500 dark:text-zinc-500 mb-6">Bu maqola mavjud emas yoki o'chirilgan.</p>
        <button onClick={() => router.push("/")} className="btn-primary">
          <ArrowLeft className="w-4 h-4" /> Bosh sahifaga
        </button>
      </div>
    );
  }

  const headline = item.ai_headlines?.[0] || item.title || "Untitled";
  const otherHeadlines = item.ai_headlines?.slice(1) || [];
  const rawContent = item.content ? stripAndDecodeHtml(item.content) : null;
  // Hide content if it's just metadata (URL/points/comments with no real article text)
  const cleanContent = rawContent && rawContent.length > 100 && !/^(Article URL:|Comments URL:|Points:|# Comments:)/m.test(rawContent)
    ? rawContent : null;
  const cleanSummary = item.summary ? stripAndDecodeHtml(item.summary) : null;

  return (
    <article className="max-w-3xl mx-auto animate-fade-in">
      {/* Back */}
      <button
        onClick={() => router.back()}
        className="inline-flex items-center gap-1.5 text-sm text-gray-500 dark:text-zinc-400
                   hover:text-blue-600 dark:hover:text-blue-400 mb-6 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" /> Orqaga
      </button>

      {/* Category & meta */}
      <div className="flex items-center gap-2 flex-wrap mb-4">
        {item.category && (
          <span className={clsx("badge capitalize", CATEGORY_COLORS[item.category] || "bg-gray-100 text-gray-600")}>
            {item.category}
          </span>
        )}
        {item.source_country === "UZ" && (
          <span className="badge bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
            🇺🇿 O'zbekiston
          </span>
        )}
        {item.sentiment && (
          <span className={clsx("badge capitalize", {
            "bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300": item.sentiment === "positive",
            "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300": item.sentiment === "negative",
            "bg-gray-100 text-gray-600 dark:bg-zinc-800 dark:text-zinc-400": item.sentiment === "neutral",
          })}>
            {item.sentiment}
          </span>
        )}
        <div className="flex items-center gap-1 text-xs text-gray-400 dark:text-zinc-500 ml-auto">
          <Clock className="w-3.5 h-3.5" />
          {item.published_at && format(new Date(item.published_at), "d MMM yyyy, HH:mm")}
        </div>
      </div>

      {/* Main headline */}
      <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white leading-tight mb-2">
        {decodeHtml(headline)}
      </h1>

      {/* Original title if different from AI headline */}
      {item.title && item.ai_headlines?.length > 0 && item.title !== headline && (
        <p className="text-sm text-gray-400 dark:text-zinc-500 mb-4 italic">
          Asl sarlavha: {decodeHtml(item.title)}
        </p>
      )}

      {/* Action bar */}
      <div className="flex items-center gap-2 mb-6">
        <button
          onClick={() => toggle(item.id, item)}
          className={clsx(
            "btn gap-1.5 text-sm",
            bookmarked.has(item.id)
              ? "bg-blue-50 dark:bg-blue-950 text-blue-600 dark:text-blue-400"
              : "btn-ghost"
          )}
        >
          {bookmarked.has(item.id)
            ? <><BookmarkCheck className="w-4 h-4" /> Saqlangan</>
            : <><Bookmark className="w-4 h-4" /> Saqlash</>
          }
        </button>
        <button onClick={share} className="btn-ghost text-sm gap-1.5">
          <Share2 className="w-4 h-4" />
          {copied ? "Nusxalandi!" : "Ulashish"}
        </button>
        {item.url && (
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary text-sm ml-auto"
          >
            Asl manba <ExternalLink className="w-3.5 h-3.5" />
          </a>
        )}
      </div>

      {/* Image */}
      {item.image_url && (
        <div className="relative h-64 sm:h-96 rounded-2xl overflow-hidden mb-6 bg-gray-100 dark:bg-zinc-800">
          <Image
            src={item.image_url}
            alt={headline}
            fill
            className="object-cover"
            unoptimized
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/30 to-transparent" />
        </div>
      )}

      {/* AI Summary */}
      {cleanSummary && (
        <div className="card p-5 mb-6 border-l-4 border-blue-500 rounded-l-none bg-blue-50/50 dark:bg-blue-950/20">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wide">
              AI Xulosa
            </span>
          </div>
          <p className="text-base text-gray-800 dark:text-zinc-200 leading-relaxed font-medium">
            {cleanSummary}
          </p>
        </div>
      )}

      {/* Full content */}
      {cleanContent ? (
        <div className="mb-8">
          <h2 className="text-sm font-semibold text-gray-500 dark:text-zinc-500 uppercase tracking-wide mb-3">
            To'liq maqola
          </h2>
          <div className="prose prose-gray dark:prose-invert max-w-none">
            {cleanContent.split("\n\n").filter(Boolean).map((para, i) => (
              <p key={i} className="text-gray-700 dark:text-zinc-300 leading-relaxed mb-4 text-base">
                {para.trim()}
              </p>
            ))}
          </div>
        </div>
      ) : item.url && (
        <div className="mb-8 p-5 rounded-2xl bg-gray-50 dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 text-center">
          <p className="text-sm text-gray-500 dark:text-zinc-500 mb-3">
            To'liq maqola asl manbada mavjud
          </p>
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary inline-flex"
          >
            Maqolani o'qish <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      )}

      {/* Alternative AI Headlines */}
      {otherHeadlines.length > 0 && (
        <div className="card p-5 mb-6">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="w-4 h-4 text-blue-500" />
            <h3 className="text-sm font-semibold text-gray-600 dark:text-zinc-400 uppercase tracking-wide">
              AI sarlavha variantlari
            </h3>
          </div>
          <ul className="space-y-2">
            {otherHeadlines.map((h, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-700 dark:text-zinc-300
                                     p-2.5 rounded-lg hover:bg-gray-50 dark:hover:bg-zinc-800 transition-colors">
                <span className="text-blue-500 font-bold mt-0.5 shrink-0">{i + 2}.</span>
                {decodeHtml(h)}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Tags */}
      {item.tags?.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap mb-6">
          <Tag className="w-4 h-4 text-gray-400" />
          {item.tags.map((tag) => (
            <Link
              key={tag}
              href={`/?search=${encodeURIComponent(tag)}`}
              className="badge bg-gray-100 dark:bg-zinc-800 text-gray-600 dark:text-zinc-400
                         hover:bg-blue-100 dark:hover:bg-blue-950 hover:text-blue-700 transition-colors"
            >
              #{tag}
            </Link>
          ))}
        </div>
      )}

      {/* Source footer */}
      <div className="flex items-center justify-between pt-6 border-t border-gray-200 dark:border-zinc-800">
        <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-zinc-500">
          <Globe className="w-4 h-4" />
          <span className="font-medium">{item.source}</span>
          {item.source_country && (
            <span className="badge bg-gray-100 dark:bg-zinc-800 text-gray-500 dark:text-zinc-400 text-xs">
              {item.source_country}
            </span>
          )}
        </div>
        {item.url && (
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary text-sm"
          >
            Asl maqolani o'qish <ExternalLink className="w-3.5 h-3.5" />
          </a>
        )}
      </div>
    </article>
  );
}
