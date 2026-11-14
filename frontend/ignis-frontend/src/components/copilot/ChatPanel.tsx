"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ExternalLink, Send, Sparkles } from "lucide-react";
import { askAi } from "@/lib/api";
import { EXAMPLE_PROMPTS } from "@/lib/constants";
import type { AiAnswer } from "@/lib/types";

interface Message {
  id: number;
  question: string;
  answer?: AiAnswer;
  error?: string;
}

/**
 * Evidence-grounded Q&A. The browser sends the question to the IGNIS backend only.
 * Every answer shows its sources, limitations and follow-up questions.
 */
export function ChatPanel({
  investigationIds,
  initialPrompt,
}: {
  investigationIds?: string[];
  /** Asked once when the panel first appears (used by the example prompts on Overview). */
  initialPrompt?: string;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const nextId = useRef(1);

  async function ask(question: string) {
    const text = question.trim();
    if (!text || busy) return;
    const id = nextId.current++;
    setMessages((m) => [...m, { id, question: text }]);
    setInput("");
    setBusy(true);
    try {
      const answer = await askAi(text, investigationIds);
      setMessages((m) => m.map((msg) => (msg.id === id ? { ...msg, answer } : msg)));
    } catch (err) {
      const error = err instanceof Error ? err.message : "The assistant is unavailable. Use Explore for keyword search.";
      setMessages((m) => m.map((msg) => (msg.id === id ? { ...msg, error } : msg)));
    } finally {
      setBusy(false);
    }
  }

  // Ask the initial prompt once. The ref guards against React Strict Mode running effects twice.
  const askedInitial = useRef(false);
  useEffect(() => {
    if (initialPrompt && !askedInitial.current) {
      askedInitial.current = true;
      ask(initialPrompt);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialPrompt]);

  return (
    <div className="space-y-6">
      {messages.length === 0 && (
        <div>
          <p className="mb-3 text-sm text-space-300">Try one of these questions:</p>
          <ul className="flex flex-wrap gap-2">
            {EXAMPLE_PROMPTS.map((prompt) => (
              <li key={prompt}>
                <button className="chip hover:border-flame-400 hover:text-space-100" onClick={() => ask(prompt)}>{prompt}</button>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="space-y-6" aria-live="polite">
        {messages.map((msg) => (
          <section key={msg.id} className="space-y-3">
            <p className="ml-auto w-fit max-w-[85%] rounded-lg bg-space-700 px-3 py-2 text-sm">{msg.question}</p>

            {!msg.answer && !msg.error && <p className="text-sm text-space-400">Searching indexed records...</p>}
            {msg.error && <p role="alert" className="rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-200">{msg.error}</p>}

            {msg.answer && (
              <div className="panel space-y-4 p-4">
                <p className="flex gap-2 text-sm leading-relaxed">
                  <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-flame-400" aria-hidden />
                  {msg.answer.answer}
                </p>

                {msg.answer.citations.length > 0 && (
                  <div>
                    <p className="mb-2 text-xs text-space-400">Sources</p>
                    <ul className="grid gap-2 sm:grid-cols-2">
                      {msg.answer.citations.map((c) => (
                        <li key={c.investigation_id} className="rounded-md border border-space-600 p-2 text-sm">
                          <Link href={`/investigations/${c.investigation_id}`} className="hover:text-flame-300">{c.title}</Link>
                          <a href={c.source_url} target="_blank" rel="noreferrer" className="mt-1 flex items-center gap-1 text-xs text-diffuse-300 hover:underline">
                            NASA PSI source <ExternalLink className="h-3 w-3" aria-hidden />
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {msg.answer.limitations.length > 0 && (
                  <div>
                    <p className="mb-1 text-xs text-space-400">Limitations</p>
                    <ul className="list-disc space-y-1 pl-5 text-xs text-space-300">
                      {msg.answer.limitations.map((l) => <li key={l}>{l}</li>)}
                    </ul>
                  </div>
                )}

                {msg.answer.follow_up_questions.length > 0 && (
                  <ul className="flex flex-wrap gap-2">
                    {msg.answer.follow_up_questions.map((q) => (
                      <li key={q}><button className="chip hover:border-flame-400" onClick={() => ask(q)}>{q}</button></li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </section>
        ))}
      </div>

      <form onSubmit={(e) => { e.preventDefault(); ask(input); }} className="flex gap-2">
        <input value={input} onChange={(e) => setInput(e.target.value)} aria-label="Ask a question about the indexed records" placeholder="Ask about the indexed NASA records" className="input" />
        <button type="submit" className="btn-primary" disabled={busy || !input.trim()}>
          <Send className="h-4 w-4" aria-hidden /> Ask
        </button>
      </form>
    </div>
  );
}
