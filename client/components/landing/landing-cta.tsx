import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function LandingCta() {
  return (
    <section className="bg-gradient-to-br from-indigo-600 to-indigo-800">
      <div className="mx-auto flex max-w-6xl flex-col items-center gap-6 px-4 py-20 text-center sm:px-6">
        <h2 className="text-3xl font-bold tracking-tight text-slate-100">
          今日から「教えて学ぶ」を始めよう
        </h2>
        <p className="max-w-xl text-indigo-100">
          無料でアカウントを作成して、すぐに学習を開始できます。
        </p>
        <Button
          asChild
          size="lg"
          className="bg-slate-100 px-8 text-indigo-700 hover:bg-white [a]:hover:bg-white"
        >
          <Link href="/sign-up">無料で始める</Link>
        </Button>
      </div>
    </section>
  );
}
