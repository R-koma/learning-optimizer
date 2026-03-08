"use client";

import { authClient } from "@/lib/auth-client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import Form from "next/form";

export default function SignInPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSignIn = async () => {
    await authClient.signIn.email(
      { email, password, callbackURL: "/dashboard", rememberMe: false },
      {
        onRequest: () => {
          setIsLoading(true);
          setError("");
        },
        onSuccess: () => {
          setIsLoading(false);
          router.push("/dashboard");
        },
        onError: (ctx) => {
          setIsLoading(false);
          setError(ctx.error.message);
        },
      },
    );
  };

  const handleGoogleSignIn = async () => {
    await authClient.signIn.social({
      provider: "google",
      callbackURL: "/dashboard",
    });
  };

  return (
    <>
      <Form action={handleSignIn}>
        <input
          type="text"
          name="email"
          placeholder="email"
          onChange={(e) => setEmail(e.target.value)}
          value={email}
        />
        <input
          type="password"
          name="password"
          placeholder="password"
          onChange={(e) => setPassword(e.target.value)}
          value={password}
        />
        <button type="submit">Submit</button>
        {isLoading ? "ログイン中" : ""}
        {error && <div>エラー発生中</div>}
      </Form>
      <button onClick={handleGoogleSignIn}>Googleでログイン</button>
    </>
  );
}
