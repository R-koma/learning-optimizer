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

const NAV_LINKS = [
  { href: "/dashboard", label: "ダッシュボード", icon: LayoutDashboardIcon },
  { href: "/learn", label: "新規学習", icon: PlusCircleIcon },
  { href: "/notes", label: "学習履歴", icon: BookOpenIcon },
];

export function Sidebar() {
  const [expanded, setExpanded] = useState(false);
  const pathname = usePathname();

  return (
    <aside
      className={`flex flex-col border-r bg-background transition-all duration-200 shrink-0 ${
        expanded ? "w-64" : "w-14"
      }`}
    >
      {/* Header: collapsed = LO icon (hover → sidebar icon), expanded = logo + close button */}
      <div className="border-b">
        {expanded ? (
          <div className="flex items-center justify-between px-3 py-3">
            <Link
              href="/dashboard"
              className="flex items-center gap-2 font-bold text-lg tracking-tight min-w-0"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary shrink-0">
                <span className="text-sm font-bold text-primary-foreground">
                  LO
                </span>
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
            {/* LO icon: shown by default, hidden on hover */}
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary group-hover:hidden">
              <span className="text-sm font-bold text-primary-foreground">
                LO
              </span>
            </div>
            {/* Sidebar open icon: hidden by default, shown on hover */}
            <PanelLeftIcon className="hidden h-4 w-4 group-hover:block text-muted-foreground" />
          </button>
        )}
      </div>

      <nav className="flex flex-col gap-1 p-2">
        {NAV_LINKS.map(({ href, label, icon: Icon }) => {
          const isActive = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 rounded-md px-2 py-2 text-sm transition-all duration-150 ${
                isActive
                  ? "bg-muted font-medium text-foreground"
                  : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
              } ${expanded ? "" : "justify-center"}`}
              title={!expanded ? label : undefined}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {expanded && <span>{label}</span>}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
