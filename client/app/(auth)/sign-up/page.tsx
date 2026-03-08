"use client";

import { authClient } from "@/lib/auth-client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import Form from "next/form";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
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

        <button type="submit">Submit</button>
        {isLoading ? "送信中" : ""}
        {error && <div>エラー発生中</div>}
      </Form>
      <Card className="w-[400px]">
        <CardHeader>
          <CardTitle>ログイン</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* ベース部品の Input と Label を組み合わせる */}
          <div className="space-y-2">
            <Label htmlFor="email">メールアドレス</Label>
            <Input id="email" type="email" placeholder="example@gmail.com" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">パスワード</Label>
            <Input
              id="password"
              type="password"
              onChange={(e) => setPassword(e.target.value)}
              value={password}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="passwordConfirmation">パスワード確認</Label>
            <Input
              id="passwordConfirmation"
              type="passwordConfirmation"
              onChange={(e) => setPasswordConfirmation(e.target.value)}
              value={passwordConfirmation}
            />
          </div>

          {/* 先ほど作ったGoogleボタンを配置 */}
          <div className="pt-4">
            <GoogleLoginButton />
          </div>
        </CardContent>
      </Card>
    </>
  );
}
