"use client";

import { useState } from "react";
import { CheckIcon, CopyIcon } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { buildNoteMarkdown } from "@/lib/note-markdown";

interface NoteShareButtonProps {
  topic: string;
  summary: string;
  content: string;
}

const COPIED_RESET_MS = 2000;

export function NoteShareButton({
  topic,
  summary,
  content,
}: NoteShareButtonProps) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    const markdown = buildNoteMarkdown({ topic, summary, content });
    try {
      await navigator.clipboard.writeText(markdown);
      setCopied(true);
      toast.success("Markdown をコピーしました");
      setTimeout(() => setCopied(false), COPIED_RESET_MS);
    } catch {
      toast.error("コピーに失敗しました。お使いの環境では利用できません。");
    }
  }

  const label = "Markdown としてコピー";

  return (
    <Button
      type="button"
      variant="outline"
      size="icon-lg"
      onClick={handleCopy}
      title={label}
      aria-label={label}
    >
      {copied ? (
        <CheckIcon className="h-4 w-4" />
      ) : (
        <CopyIcon className="h-4 w-4" />
      )}
    </Button>
  );
}
