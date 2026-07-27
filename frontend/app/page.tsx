"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";

type Source = { page: number | null; type: string; source: string };
type Message = {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  error?: boolean;
};

const STAGES = [
  { key: "retrieve", label: "Retrieve", hint: "search the source" },
  { key: "grade_documents", label: "Grade", hint: "check relevance" },
  { key: "web_search", label: "Web search", hint: "look beyond the source" },
  { key: "generate", label: "Generate", hint: "write the answer" },
] as const;

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const DOC_NAME = process.env.NEXT_PUBLIC_DOC_NAME || "your-document.pdf";

function safeHostname(url: string) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeSteps, setActiveSteps] = useState<string[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q || loading) return;

    setMessages((m) => [...m, { role: "user", content: q }]);
    setQuestion("");
    setLoading(true);
    setActiveSteps([]);

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      if (!res.ok) throw new Error(`Backend returned ${res.status}`);
      const data = await res.json();
      setActiveSteps(data.steps || []);
      setMessages((m) => [
        ...m,
        { role: "assistant", content: data.answer, sources: data.sources },
      ]);
    } catch {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content:
            "Couldn't reach the backend. Check that the API is running and NEXT_PUBLIC_API_URL is set correctly, then try again.",
          error: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen flex-col md:flex-row">
      {/* Reasoning ledger */}
      <aside className="w-full shrink-0 border-b border-line bg-surface px-6 py-8 md:min-h-screen md:w-72 md:border-b-0 md:border-r">
        <div className="font-mono text-xs uppercase tracking-widest text-muted">Source</div>
        <div className="mt-2 font-display text-xl italic text-parchment">{DOC_NAME}</div>

        <div className="mt-10 font-mono text-xs uppercase tracking-widest text-muted">
          Reasoning
        </div>
        <ol className="mt-4">
          {STAGES.map((stage, i) => {
            const used = loading || activeSteps.includes(stage.key);
            const isLast = i === STAGES.length - 1;
            return (
              <li key={stage.key} className="relative pb-8 pl-6 last:pb-0">
                {!isLast && (
                  <span
                    className="absolute left-[5px] top-3 h-full w-px"
                    style={{ backgroundColor: "var(--color-line)" }}
                  />
                )}
                <span
                  className={`absolute left-0 top-1 h-[11px] w-[11px] rounded-full border ${
                    used ? "border-brass" : "border-line"
                  } ${loading ? "animate-pulse-glow" : ""}`}
                  style={{ backgroundColor: used ? "var(--color-brass)" : "transparent" }}
                />
                <div className={`text-sm ${used ? "text-parchment" : "text-muted"}`}>
                  {stage.label}
                </div>
                <div className="mt-0.5 text-xs text-muted">{stage.hint}</div>
              </li>
            );
          })}
        </ol>
      </aside>

      {/* Chat thread */}
      <section className="flex min-h-screen flex-1 flex-col">
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-10 md:px-12">
          {messages.length === 0 && (
            <div className="max-w-xl">
              <div className="font-mono text-xs uppercase tracking-widest text-brass">Ready</div>
              <p className="mt-3 font-display text-2xl leading-snug text-parchment md:text-3xl">
                Ask something about the source.
              </p>
              <p className="mt-2 text-muted">
                I&apos;ll read, check what I find, and show each step on the left as I work
                through it.
              </p>
            </div>
          )}

          <div className="max-w-2xl space-y-8">
            {messages.map((m, i) => (
              <div key={i}>
                <div
                  className={`mb-2 font-mono text-xs uppercase tracking-widest ${
                    m.role === "user" ? "text-muted" : m.error ? "text-alert" : "text-moss"
                  }`}
                >
                  {m.role === "user" ? "You asked" : m.error ? "Couldn't answer" : "Answer"}
                </div>
                <p
                  className={`leading-relaxed ${
                    m.role === "user"
                      ? "font-medium text-parchment/90"
                      : m.error
                        ? "text-alert"
                        : "text-parchment"
                  }`}
                >
                  {m.content}
                </p>
                {m.sources && m.sources.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {m.sources.map((s, si) => (
                      <span
                        key={si}
                        className="rounded border border-line px-2 py-1 font-mono text-xs text-muted"
                        title={s.source}
                      >
                        {s.type === "web" ? `web · ${safeHostname(s.source)}` : `p.${s.page ?? "?"}`}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div>
                <div className="mb-2 animate-pulse-glow font-mono text-xs uppercase tracking-widest text-brass">
                  Thinking
                </div>
                <p className="text-muted">Working through the source…</p>
              </div>
            )}
          </div>
        </div>

        <form onSubmit={handleSubmit} className="border-t border-line px-6 py-5 md:px-12">
          <div className="flex max-w-2xl items-center gap-3">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask about the document…"
              className="flex-1 rounded-md border border-line bg-surface px-4 py-3 text-parchment placeholder:text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brass"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !question.trim()}
              className="rounded-md bg-brass px-5 py-3 font-mono text-sm font-medium text-ink transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Ask
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}
