export type Flag = { name: string; delta: number; detail: string };

export type BriefItem = {
  source: string;
  item_id: string;
  title: string;
  text: string;
  url: string;
  author: string;
  published_at: string | null;
  engagement: number;
  rating: number | null;
  trust: number;
  trust_label: "trusted" | "mixed" | "suspicious";
  weighted_score: number;
  flags: Flag[];
  metadata: Record<string, unknown>;
};

export type Brief = {
  topic: string;
  generated_at: string;
  warnings: string[];
  item_count: number;
  items: BriefItem[];
};

export type CompareSnippet = {
  text: string;
  rating: number | null;
  trust: number;
  source: string;
  url: string;
};

export type CompareEntity = {
  topic: string;
  item_count: number;
  avg_rating: number | null;
  avg_trust: number | null;
  suspicious: number;
  suspicious_share: number;
  top_praise: CompareSnippet | null;
  top_complaint: CompareSnippet | null;
};

export type CompareResult = {
  entities: CompareEntity[];
  verdict: string | null;
};

export const SOURCES = ["appstore", "playstore", "reddit", "pantip", "youtube", "x"] as const;
export type Source = (typeof SOURCES)[number];

export const TRUST_COLOR: Record<BriefItem["trust_label"], string> = {
  trusted: "var(--green)",
  mixed: "var(--yellow)",
  suspicious: "var(--red)",
};
