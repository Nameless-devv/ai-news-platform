"use client";
import { Bookmark } from "lucide-react";
import { NewsCard } from "@/components/NewsCard";
import { useBookmarks } from "@/hooks/useBookmarks";

export default function BookmarksPage() {
  const { bookmarked, bookmarkedItems, toggle } = useBookmarks();

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <Bookmark className="w-6 h-6 text-blue-600" />
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Saqlangan yangiliklar</h1>
        <span className="badge bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300">
          {bookmarkedItems.length}
        </span>
      </div>

      {bookmarkedItems.length === 0 ? (
        <div className="text-center py-20 text-gray-400 dark:text-zinc-500">
          <Bookmark className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p className="text-lg font-medium">Hali saqlangan yangilik yo'q</p>
          <p className="text-sm mt-1">Yangilik kartasidagi bookmark tugmasini bosing</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {bookmarkedItems.map((item) => (
            <NewsCard
              key={item.id}
              item={item}
              isBookmarked={bookmarked.has(item.id)}
              onBookmark={(id) => toggle(id, item)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
