"use client";

import { useRef, useState } from "react";
import { ArrowUpIcon, ImageIcon, MicIcon, PlusIcon, XIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface AttachedFile {
  file: File;
  preview: string | null; // object URL for images, null otherwise
}

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: (content: string) => void;
  isLoading: boolean;
  placeholder?: string;
}

export function ChatInput({
  value,
  onChange,
  onSend,
  isLoading,
  placeholder = "入力...",
}: ChatInputProps) {
  const [showMenu, setShowMenu] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileClick = () => {
    setShowMenu(false);
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files ?? []);
    const newFiles: AttachedFile[] = selected.map((file) => ({
      file,
      preview: file.type.startsWith("image/")
        ? URL.createObjectURL(file)
        : null,
    }));
    setAttachedFiles((prev) => [...prev, ...newFiles]);
    e.target.value = "";
  };

  const removeFile = (index: number) => {
    setAttachedFiles((prev) => {
      const next = [...prev];
      const removed = next.splice(index, 1)[0];
      if (removed.preview) URL.revokeObjectURL(removed.preview);
      return next;
    });
  };

  const handleSend = async () => {
    if (!value.trim() && attachedFiles.length === 0) return;

    let content = value.trim();

    for (const { file, preview } of attachedFiles) {
      if (file.type.startsWith("image/")) {
        content += `\n\n[画像: ${file.name}]`;
      } else {
        try {
          const text = await file.text();
          content += `\n\n[ファイル: ${file.name}]\n${text}`;
        } catch {
          content += `\n\n[添付: ${file.name}]`;
        }
      }
      if (preview) URL.revokeObjectURL(preview);
    }

    onSend(content);
    setAttachedFiles([]);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      handleSend();
    }
  };

  const hasContent = value.trim() || attachedFiles.length > 0;

  return (
    <div className="rounded-2xl border bg-muted/50 p-3">
      {attachedFiles.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-2">
          {attachedFiles.map(({ file, preview }, i) =>
            preview ? (
              <div key={i} className="relative">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={preview}
                  alt={file.name}
                  className="h-16 w-16 rounded-lg object-cover border"
                />
                <button
                  type="button"
                  onClick={() => removeFile(i)}
                  className="absolute -right-1.5 -top-1.5 flex h-4 w-4 cursor-pointer items-center justify-center rounded-full bg-foreground text-background"
                >
                  <XIcon className="h-2.5 w-2.5" />
                </button>
              </div>
            ) : (
              <div
                key={i}
                className="flex items-center gap-1 rounded-lg border bg-background px-2 py-1 text-xs"
              >
                <span className="max-w-32 truncate">{file.name}</span>
                <button
                  type="button"
                  onClick={() => removeFile(i)}
                  className="cursor-pointer text-muted-foreground hover:text-foreground"
                >
                  <XIcon className="h-3 w-3" />
                </button>
              </div>
            ),
          )}
        </div>
      )}

      <Textarea
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        rows={1}
        className="min-h-10 resize-none border-0 bg-transparent shadow-none focus-visible:ring-0 dark:bg-transparent"
      />

      <div className="flex items-center justify-between pt-1">
        <div className="relative">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-8 w-8 rounded-full cursor-pointer"
            onClick={() => setShowMenu((prev) => !prev)}
          >
            <PlusIcon className="h-4 w-4" />
          </Button>

          {showMenu && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setShowMenu(false)}
              />
              <div className="absolute bottom-full left-0 z-20 mb-2 w-52 rounded-xl border bg-popover shadow-md">
                <button
                  type="button"
                  onClick={handleFileClick}
                  className="flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-sm hover:bg-accent cursor-pointer"
                >
                  <ImageIcon className="h-4 w-4 text-muted-foreground" />
                  Add files or photos
                </button>
              </div>
            </>
          )}

          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            multiple
            accept="image/*,*/*"
            onChange={handleFileChange}
          />
        </div>

        <div className="flex items-center">
          {hasContent ? (
            <Button
              type="button"
              size="icon"
              onClick={handleSend}
              disabled={isLoading}
              className="h-8 w-8 rounded-full cursor-pointer"
            >
              <ArrowUpIcon className="h-4 w-4" />
            </Button>
          ) : (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              disabled
              className="h-8 w-8 rounded-full"
            >
              <MicIcon className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
