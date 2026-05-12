import {
  CheckCircle2Icon,
  CircleDashedIcon,
  CircleDotIcon,
  NetworkIcon,
} from "lucide-react";

type Coverage = "covered" | "partial" | "uncovered";

interface AspectNode {
  name: string;
  summary: string;
  coverage: Coverage;
  children?: AspectNode[];
}

export interface AspectMap {
  root: string;
  aspects: AspectNode[];
}

const COVERAGE_META: Record<
  Coverage,
  { label: string; icon: typeof CheckCircle2Icon; className: string }
> = {
  covered: {
    label: "カバー済み",
    icon: CheckCircle2Icon,
    className: "text-emerald-600 dark:text-emerald-400",
  },
  partial: {
    label: "部分的",
    icon: CircleDotIcon,
    className: "text-amber-600 dark:text-amber-400",
  },
  uncovered: {
    label: "未カバー",
    icon: CircleDashedIcon,
    className: "text-muted-foreground",
  },
};

function AspectItem({ node, depth }: { node: AspectNode; depth: number }) {
  const meta = COVERAGE_META[node.coverage] ?? COVERAGE_META.uncovered;
  const Icon = meta.icon;
  return (
    <li className="space-y-1">
      <div className="flex items-start gap-2">
        <Icon
          className={`mt-0.5 h-4 w-4 shrink-0 ${meta.className}`}
          aria-label={meta.label}
        />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-baseline gap-x-2">
            <span className="text-sm font-medium text-foreground">
              {node.name}
            </span>
            <span
              className={`text-[10px] uppercase tracking-wider ${meta.className}`}
            >
              {meta.label}
            </span>
          </div>
          {node.summary && (
            <p className="mt-0.5 text-xs leading-5 text-muted-foreground">
              {node.summary}
            </p>
          )}
        </div>
      </div>
      {node.children && node.children.length > 0 && depth < 2 && (
        <ul className="ml-5 space-y-1.5 border-l border-border pl-3">
          {node.children.map((child, idx) => (
            <AspectItem
              key={`${child.name}-${idx}`}
              node={child}
              depth={depth + 1}
            />
          ))}
        </ul>
      )}
    </li>
  );
}

export function NoteAspectMap({ aspectMap }: { aspectMap: AspectMap }) {
  if (!aspectMap.aspects || aspectMap.aspects.length === 0) {
    return null;
  }
  return (
    <section id="aspect-map" className="scroll-mt-8">
      <div className="mb-4 flex items-center gap-2">
        <NetworkIcon className="h-4 w-4 text-muted-foreground" />
        <h2 className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">
          観点マップ
        </h2>
      </div>
      <div className="rounded-lg border bg-card p-4">
        <p className="mb-3 text-xs text-muted-foreground">
          対話で扱われた観点と、関連する未カバー観点の俯瞰図です。
        </p>
        <ul className="space-y-2.5">
          {aspectMap.aspects.map((aspect, idx) => (
            <AspectItem key={`${aspect.name}-${idx}`} node={aspect} depth={0} />
          ))}
        </ul>
      </div>
    </section>
  );
}
