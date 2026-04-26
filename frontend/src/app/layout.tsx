import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/components/ThemeProvider";
import { Header } from "@/components/Header";

export const metadata: Metadata = {
  title: "AI News Platform — O'zbekiston va Dunyo Yangiliklari",
  description: "Real-time AI-powered news from Uzbekistan and around the world",
  icons: { icon: "/favicon.ico" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="uz" suppressHydrationWarning>
      <body>
        <ThemeProvider>
          <div className="min-h-screen flex flex-col">
            <Header />
            <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-6">
              {children}
            </main>
            <footer className="border-t border-gray-200 dark:border-zinc-800 py-6 mt-12">
              <div className="max-w-7xl mx-auto px-4 text-center text-sm text-gray-500 dark:text-zinc-500">
                © 2026 AI News Platform · Powered by OpenAI · Real-time news from Uzbekistan & World
              </div>
            </footer>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
