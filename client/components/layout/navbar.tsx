"use client";

import Link from "next/link";
import { authClient } from "@/lib/auth-client";
import { useRouter, usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  LogOutIcon,
  LayoutDashboardIcon,
  PlusCircleIcon,
  BookOpenIcon,
  SunIcon,
  MoonIcon,
} from "lucide-react";
import { useTheme } from "next-themes";

interface NavbarProps {
  user: {
    id: string;
    name: string;
    email: string;
    image?: string | null;
  };
}

const NAV_LINKS = [
  { href: "/dashboard", label: "ダッシュボード", icon: LayoutDashboardIcon },
  { href: "/learn", label: "新規学習", icon: PlusCircleIcon },
  { href: "/notes", label: "学習履歴", icon: BookOpenIcon },
];

export function Navbar({ user }: NavbarProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();

  const handleSignOut = async () => {
    await authClient.signOut({
      fetchOptions: {
        onSuccess: () => {
          router.push("/sign-in");
        },
      },
    });
  };

  return (
    <nav className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur-lg px-6 py-3 flex items-center justify-between">
      <Link
        href="/dashboard"
        className="flex items-center gap-2 font-bold text-lg tracking-tight"
      >
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
          <span className="text-sm font-bold text-primary-foreground">LO</span>
        </div>
        <span className="hidden sm:inline">Learning Optimizer</span>
      </Link>

      <div className="flex items-center gap-2">
        <div className="flex items-center rounded-lg bg-muted/50 p-1">
          {NAV_LINKS.map(({ href, label, icon: Icon }) => {
            const isActive =
              pathname === href || pathname.startsWith(`${href}/`);
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-3 rounded-md mx-3 px-3 py-1.5 text-sm transition-all duration-150 ${
                  isActive
                    ? "bg-background font-medium text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Icon className="h-4 w-4" />
                <span className="hidden md:inline">{label}</span>
              </Link>
            );
          })}
        </div>

        <div className="mx-2 h-6 w-px bg-border" />

        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9 rounded-full"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        >
          <SunIcon className="h-4 w-4 rotate-0 scale-100 transition-transform dark:rotate-90 dark:scale-0" />
          <MoonIcon className="absolute h-4 w-4 rotate-90 scale-0 transition-transform dark:rotate-0 dark:scale-100" />
          <span className="sr-only">テーマ切り替え</span>
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              className="flex items-center gap-2 rounded-full px-2"
            >
              <Avatar className="h-8 w-8">
                <AvatarImage src={user.image ?? undefined} />
                <AvatarFallback className="text-xs">
                  {user.name?.charAt(0).toUpperCase() ?? "U"}
                </AvatarFallback>
              </Avatar>
              <span className="hidden text-sm font-medium sm:inline">
                {user.name}
              </span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-48" align="end">
            <DropdownMenuItem
              disabled
              className="text-xs text-muted-foreground"
            >
              {user.email}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={handleSignOut}>
              <LogOutIcon className="h-4 w-4" />
              ログアウト
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </nav>
  );
}
