import { Suspense } from "react";
import { NewsFeed } from "@/components/NewsFeed";

export default function HomePage() {
  return (
    <Suspense fallback={
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 9 }).map((_, i) => (
          <div key={i} className="card h-64 animate-pulse bg-gray-200 dark:bg-zinc-800" />
        ))}
      </div>
    }>
      <NewsFeed />
    </Suspense>
  );
}
