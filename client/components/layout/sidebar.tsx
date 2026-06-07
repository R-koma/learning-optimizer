"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboardIcon,
  PlusCircleIcon,
  BookOpenIcon,
  PanelLeftIcon,
  PanelLeftCloseIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { SidebarCalendar } from "@/components/layout/sidebar-calendar";
import { cn } from "@/lib/utils";
import { useSidebarWidth } from "@/hooks/use-sidebar-width";

const NAV_LINKS = [
  { href: "/dashboard", label: "ダッシュボード", icon: LayoutDashboardIcon },
  { href: "/learn", label: "新規学習", icon: PlusCircleIcon },
  { href: "/notes", label: "学習履歴", icon: BookOpenIcon },
];

export function Sidebar() {
  const [expanded, setExpanded] = useState(false);
  const pathname = usePathname();
  const { width, isResizing, startResize } = useSidebarWidth();

  return (
    <aside
      className={cn(
        "relative flex shrink-0",
        !expanded && "w-14",
        // ドラッグ中は幅アニメーションを切り、ポインタに追従させる
        isResizing ? "" : "transition-[width] duration-200",
      )}
      style={expanded ? { width } : undefined}
    >
      <div className="flex flex-1 flex-col overflow-x-hidden overflow-y-auto border-r bg-background">
        <div className="border-b">
          {expanded ? (
            <div className="flex items-center justify-between px-3 py-3">
              <Link
                href="/dashboard"
                className="flex items-center gap-2 font-bold text-lg tracking-tight min-w-0"
              >
                <div className="flex h-4 w-4 items-center justify-center shrink-0">
                  <span className="text-[10px] font-bold leading-none">LO</span>
                </div>
                <span>Learning Optimizer</span>
              </Link>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 cursor-pointer shrink-0 ml-1"
                onClick={() => setExpanded(false)}
              >
                <PanelLeftCloseIcon className="h-4 w-4" />
              </Button>
            </div>
          ) : (
            <button
              className="group flex w-full items-center justify-center py-3 cursor-pointer"
              onClick={() => setExpanded(true)}
              aria-label="サイドバーを開く"
            >
              <div className="flex h-4 w-4 items-center justify-center group-hover:hidden">
                <span className="text-[10px] font-bold leading-none">LO</span>
              </div>
              <PanelLeftIcon className="hidden h-4 w-4 group-hover:block text-muted-foreground" />
            </button>
          )}
        </div>

        <nav className="flex flex-col gap-1 p-2">
          {NAV_LINKS.map(({ href, label, icon: Icon }) => {
            const isActive =
              pathname === href || pathname.startsWith(`${href}/`);
            return (
              <Link
                key={href}
                href={href}
                className={`group relative flex items-center gap-3 rounded-md px-2 py-2 text-sm transition-all duration-150 ${
                  isActive
                    ? "bg-muted font-medium text-foreground"
                    : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                } ${expanded ? "" : "justify-center"}`}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {expanded ? (
                  <span>{label}</span>
                ) : (
                  <span className="pointer-events-none absolute left-full z-50 ml-2 whitespace-nowrap rounded-md bg-muted px-2 py-1 text-xs text-foreground opacity-0 shadow-md transition-opacity duration-150 group-hover:opacity-100">
                    {label}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {expanded && (
          <div className="mt-4 border-t p-2 pt-4">
            <SidebarCalendar />
          </div>
        )}
      </div>

      {expanded && (
        <div
          role="separator"
          aria-orientation="vertical"
          aria-label="サイドバーの幅を調整"
          onMouseDown={startResize}
          className={cn(
            "absolute top-0 right-0 h-full w-1 cursor-col-resize transition-colors hover:bg-primary/40",
            isResizing && "bg-primary/40",
          )}
        />
      )}
    </aside>
  );
}
