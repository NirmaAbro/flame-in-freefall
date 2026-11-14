"use client";

/** AI Copilot: grounded Q&A over the indexed records. `?prompt=` is asked once on load. */
import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { ChatPanel } from "@/components/copilot/ChatPanel";
import { PageHeader } from "@/components/ui/PageHeader";
import { LoadingBlock } from "@/components/ui/States";

function CopilotContent() {
  const prompt = useSearchParams().get("prompt") ?? undefined;
  return (
    <div className="page max-w-3xl">
      <PageHeader
        title="AI Copilot"
        description="Ask questions about the indexed NASA records. Answers cite their sources, say when the evidence is missing, and never predict fire risk or declare a material safe."
      />
      <ChatPanel initialPrompt={prompt} />
    </div>
  );
}

export default function CopilotPage() {
  return (
    <Suspense fallback={<LoadingBlock />}>
      <CopilotContent />
    </Suspense>
  );
}
