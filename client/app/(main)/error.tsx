"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function MainError({ error, reset }: ErrorProps) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] items-center justify-center px-6 py-8">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>問題が発生しました</CardTitle>
          <CardDescription>
            ページの読み込み中にエラーが発生しました。時間をおいて再試行してください。
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          解決しない場合は、しばらくしてから再度お試しください。
        </CardContent>
        <CardFooter className="justify-end">
          <Button onClick={() => reset()}>再試行</Button>
        </CardFooter>
      </Card>
    </div>
  );
}
