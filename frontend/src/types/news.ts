export interface NewsItem {
  id: number;
  raw_id: number;
  summary: string | null;
  ai_headlines: string[];
  category: string | null;
  sentiment: "positive" | "negative" | "neutral" | null;
  tags: string[];
  processed_at: string;
  source: string | null;
  source_country: string | null;
  title: string | null;
  url: string | null;
  image_url: string | null;
  published_at: string | null;
  content?: string | null;
}

export interface NewsListResponse {
  items: NewsItem[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

export interface TrendingTopic {
  topic: string;
  count: number;
  category: string | null;
}

export interface GenerateResponse {
  summary: string;
  headlines: string[];
  category: string;
  sentiment: string;
  tags: string[];
}

export type Category =
  | "politics"
  | "economy"
  | "technology"
  | "sports"
  | "culture"
  | "health"
  | "world"
  | "society"
  | "environment"
  | "science";
