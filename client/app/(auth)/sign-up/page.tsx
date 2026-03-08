"use client";

import { authClient } from "@/lib/auth-client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import Form from "next/form";
import GoogleLoginButton from "@/components/auth/google-login-button";

export default function SignUpPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirmation, setPasswordConfirmation] = useState("");
  const [name, setName] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSignUp = async () => {
    if (password !== passwordConfirmation) {
      setError("パスワードが一致しません");
    }
    await authClient.signUp.email(
      { email, password, name },
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

  return (
    <>
      <Form action={handleSignUp}>
        <input
          type="text"
          name="name"
          placeholder="name"
          onChange={(e) => setName(e.target.value)}
          value={name}
        />
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
        <input
          type="password"
          name="passwordConfirmation"
          placeholder="password confirmation"
          onChange={(e) => setPasswordConfirmation(e.target.value)}
          value={passwordConfirmation}
        />
        <button type="submit">Submit</button>
        {isLoading ? "送信中" : ""}
        {error && <div>エラー発生中</div>}
      </Form>
      <GoogleLoginButton />
    </>
  );
}
