interface NoteMarkdownInput {
  topic: string;
  summary: string;
  content: string;
}

export function buildNoteMarkdown({
  topic,
  summary,
  content,
}: NoteMarkdownInput): string {
  const sections = [`# ${topic.trim()}`];

  const trimmedSummary = summary.trim();
  if (trimmedSummary) {
    sections.push(`## 要約\n\n${trimmedSummary}`);
  }

  sections.push(`## 内容\n\n${content.trim()}`);

  return `${sections.join("\n\n")}\n`;
}
