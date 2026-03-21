"use client";

import { authClient } from "@/lib/auth-client";
import { useRouter } from "next/navigation";

export default function DashBoard() {
  const router = useRouter();
  const { data: session, isPending } = authClient.useSession();

  if (isPending) return <p>読み込み中...</p>;
  if (!session) return <p>ログインしてください。</p>;

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
    <div>
      <h1>ダッシュボード</h1>
      <p>{session.user.name}</p>
      <button onClick={handleSignOut}>ログアウト</button>
    </div>
  );
}
