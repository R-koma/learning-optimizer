"use client";

import { authClient } from "@/lib/auth-client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import * as z from "zod";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Field, FieldError, FieldGroup } from "@/components/ui/field";
import { Input } from "@/components/ui/input";

import GoogleLoginButton from "@/components/auth/google-login-button";
import Link from "next/link";

const signInSchema = z.object({
  email: z.email({ error: "有効なメールアドレスを入力してください。" }),
  password: z
    .string()
    .min(8, { error: "パスワードは8文字以上で入力してください。" }),
});

type SignInValues = z.infer<typeof signInSchema>;

export default function SignInPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [serverError, setServerError] = useState("");

  const form = useForm<SignInValues>({
    resolver: zodResolver(signInSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  const handleSignIn = async (values: SignInValues) => {
    setIsLoading(true);
    setServerError("");

    await authClient.signIn.email(
      { email: values.email, password: values.password, rememberMe: false },
      {
        onRequest: () => {
          setIsLoading(true);
        },
        onSuccess: () => {
          setIsLoading(false);
          router.push("/dashboard");
        },
        onError: (ctx) => {
          setIsLoading(false);
          setServerError(ctx.error.message);
        },
      },
    );
  };

  return (
    <div className="min-h-screen flex items-center justify-center">
      <Card className="w-full max-w-md mx-auto min-h-125 flex flex-col justify-center p-6 ring-0 border-0 shadow-none">
        <CardHeader>
          <CardTitle className="text-center text-2xl">ログイン</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-6 p-0">
          <div className="flex justify-center">
            <GoogleLoginButton />
          </div>
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-card px-2 text-muted-foreground">OR</span>
            </div>
          </div>
          <form id="sign-in-form" onSubmit={form.handleSubmit(handleSignIn)}>
            <FieldGroup className="space-y-4">
              <Controller
                name="email"
                control={form.control}
                render={({ field, fieldState }) => (
                  <Field data-invalid={fieldState.invalid} className="w-full">
                    <Input
                      {...field}
                      id="email"
                      aria-invalid={fieldState.invalid}
                      placeholder="メールアドレス"
                      autoComplete="off"
                      className="p-6 text-base tracking-wide"
                    />
                    {fieldState.invalid && (
                      <FieldError errors={[fieldState.error]} />
                    )}
                  </Field>
                )}
              />
              <Controller
                name="password"
                control={form.control}
                render={({ field, fieldState }) => (
                  <Field data-invalid={fieldState.invalid} className="w-full">
                    <Input
                      {...field}
                      type="password"
                      id="password"
                      aria-invalid={fieldState.invalid}
                      placeholder="パスワード"
                      autoComplete="off"
                      className="p-6 text-base tracking-wide"
                    />
                    {fieldState.invalid && (
                      <FieldError errors={[fieldState.error]} />
                    )}
                  </Field>
                )}
              />
              {serverError && (
                <p className="text-sm text-destructive">{serverError}</p>
              )}
            </FieldGroup>
          </form>
        </CardContent>
        <CardFooter className="p-0 pt-6 border-t-0 bg-transparent">
          <Button
            type="submit"
            form="sign-in-form"
            disabled={isLoading}
            className="w-full p-6 bg-green-600 hover:bg-green-700 text-lg text-white cursor-pointer transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? "Loading..." : "続ける"}
          </Button>
        </CardFooter>
        <p className="text-center text-sm text-muted-foreground pb-6">
          アカウントをお持ちでない方はこちら
          <Link
            href="/sign-up"
            className="text-primary underline underline-offset-4 hover:opacity-80"
          >
            新規登録
          </Link>
        </p>
      </Card>
    </div>
  );
}
