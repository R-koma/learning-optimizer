"use client";

import { useRef, useState, type ComponentProps } from "react";
import { CheckIcon, CopyIcon } from "lucide-react";
import { cn } from "@/lib/utils";

const COPIED_RESET_MS = 2000;

export function CodeBlockWithCopy({
  className,
  children,
  ...props
}: ComponentProps<"pre">) {
  const preRef = useRef<HTMLPreElement>(null);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    const text = preRef.current?.textContent ?? "";
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), COPIED_RESET_MS);
    } catch {
      // クリップボード非対応環境では何もしない（コピーは付加的機能のため）
    }
  };

  return (
    <div className="group/code relative">
      <button
        type="button"
        onClick={handleCopy}
        aria-label="コードをコピー"
        className="absolute top-2 right-2 cursor-pointer rounded-md border bg-background/80 p-1.5 text-muted-foreground opacity-0 transition-opacity hover:text-foreground group-hover/code:opacity-100"
      >
        {copied ? (
          <CheckIcon className="h-3.5 w-3.5" />
        ) : (
          <CopyIcon className="h-3.5 w-3.5" />
        )}
      </button>
      <pre
        ref={preRef}
        className={cn(
          "my-3 overflow-x-auto rounded-lg bg-muted p-3 text-sm",
          className,
        )}
        {...props}
      >
        {children}
      </pre>
    </div>
  );
}
