"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { Moon, Sun, Search, Zap, Menu, X, Sparkles } from "lucide-react";
import { useTheme } from "./ThemeProvider";

export function Header() {
  const { theme, toggle } = useTheme();
  const router = useRouter();
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const [query, setQuery] = useState("");
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      router.push(`/?ai_search=${encodeURIComponent(query.trim())}`);
    }
  };

  const isActive = (href: string) => {
    if (href === "/bookmarks") {
      return pathname === href;
    }
    if (href === "/") {
      return pathname === "/" && !searchParams.get("country") && !searchParams.get("category") && !searchParams.get("search") && !searchParams.get("ai_search");
    }
    const url = new URL(href, "http://x");
    for (const [key, val] of url.searchParams.entries()) {
      if (searchParams.get(key) !== val) return false;
    }
    return pathname === "/";
  };

  return (
    <header className="sticky top-0 z-50 bg-white/80 dark:bg-zinc-950/80 backdrop-blur-xl border-b border-gray-200 dark:border-zinc-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 gap-4">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2.5 shrink-0">
            <div className="w-8 h-8 bg-blue-600 rounded-xl flex items-center justify-center">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-gray-900 dark:text-white text-lg leading-none">
              AI<span className="text-blue-600">News</span>
            </span>
          </Link>

          {/* Desktop nav */}
          <nav className="hidden md:flex items-center gap-1">
            {[
              { href: "/", label: "Barchasi" },
              { href: "/?country=UZ", label: "🇺🇿 O'zbekiston" },
              { href: "/?country=GLOBAL", label: "🌍 Dunyo" },
              { href: "/?category=technology", label: "💻 Tech" },
              { href: "/?category=sports", label: "⚽ Sport" },
              { href: "/bookmarks", label: "Saqlangan" },
            ].map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive(item.href)
                    ? "bg-blue-600 text-white"
                    : "text-gray-600 dark:text-zinc-400 hover:bg-gray-100 dark:hover:bg-zinc-800 hover:text-gray-900 dark:hover:text-white"
                }`}
              >
                {item.label}
              </Link>
            ))}
          </nav>

          {/* Search + controls */}
          <div className="flex items-center gap-2">
            <form onSubmit={handleSearch} className="hidden sm:flex items-center">
              <div className="relative flex items-center">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="AI qidiruv..."
                  className="pl-9 pr-20 py-1.5 text-sm rounded-xl bg-gray-100 dark:bg-zinc-800
                             border-0 outline-none focus:ring-2 focus:ring-blue-500
                             text-gray-900 dark:text-white placeholder-gray-400 w-48 lg:w-64"
                />
                <button
                  type="submit"
                  className="absolute right-1.5 top-1/2 -translate-y-1/2 flex items-center gap-1
                             px-2 py-1 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium
                             transition-colors"
                >
                  <Sparkles className="w-3 h-3" /> AI
                </button>
              </div>
            </form>

            <button
              onClick={toggle}
              className="btn-ghost p-2 rounded-xl"
              aria-label="Toggle theme"
            >
              {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>

            <button
              className="md:hidden btn-ghost p-2 rounded-xl"
              onClick={() => setMobileOpen(!mobileOpen)}
            >
              {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        {mobileOpen && (
          <div className="md:hidden border-t border-gray-200 dark:border-zinc-800 py-3 space-y-1 animate-fade-in">
            <form onSubmit={handleSearch} className="flex items-center mb-3">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Qidirish..."
                  className="w-full pl-9 pr-4 py-2 text-sm rounded-xl bg-gray-100 dark:bg-zinc-800
                             border-0 outline-none focus:ring-2 focus:ring-blue-500
                             text-gray-900 dark:text-white placeholder-gray-400"
                />
              </div>
            </form>
            {[
              { href: "/", label: "Barchasi" },
              { href: "/?country=UZ", label: "🇺🇿 O'zbekiston" },
              { href: "/?country=GLOBAL", label: "🌍 Dunyo" },
              { href: "/?category=technology", label: "💻 Tech" },
              { href: "/?category=sports", label: "⚽ Sport" },
              { href: "/bookmarks", label: "Saqlangan" },
            ].map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className={`block px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive(item.href)
                    ? "bg-blue-600 text-white"
                    : "text-gray-700 dark:text-zinc-300 hover:bg-gray-100 dark:hover:bg-zinc-800"
                }`}
              >
                {item.label}
              </Link>
            ))}
          </div>
        )}
      </div>
    </header>
  );
}
