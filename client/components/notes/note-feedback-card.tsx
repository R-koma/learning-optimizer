import { AlertCircleIcon, CheckCircleIcon, TrendingUpIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface Feedback {
  id: string;
  understanding_level: string;
  strength: string;
  improvements: string;
  created_at: string;
}

export function NoteFeedbackCard({ feedback }: { feedback: Feedback }) {
  return (
    <article className="rounded-lg border bg-card p-4">
      <Badge variant="secondary" className="gap-1 font-normal">
        <TrendingUpIcon className="h-3.5 w-3.5" />
        理解度: {feedback.understanding_level}
      </Badge>
      <div className="mt-4 space-y-4">
        <div className="border-l-2 border-emerald-500 pl-3">
          <div className="mb-1 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
            <CheckCircleIcon className="h-3.5 w-3.5" />
            強み
          </div>
          <p className="text-sm leading-6 text-foreground/90">
            {feedback.strength}
          </p>
        </div>
        <div className="border-l-2 border-amber-500 pl-3">
          <div className="mb-1 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-amber-600 dark:text-amber-400">
            <AlertCircleIcon className="h-3.5 w-3.5" />
            改善点
          </div>
          <p className="text-sm leading-6 text-foreground/90">
            {feedback.improvements}
          </p>
        </div>
      </div>
    </article>
  );
}

export function NoteFeedbackEmpty() {
  return (
    <div className="rounded-lg border border-dashed bg-card/50 px-4 py-8 text-center text-sm text-muted-foreground">
      フィードバックはまだありません
    </div>
  );
}
