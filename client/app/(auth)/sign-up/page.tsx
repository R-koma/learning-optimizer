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

const signUpSchema = z
  .object({
    name: z
      .string()
      .min(2, { message: "名前は2文字以上で入力してください。" })
      .max(50, { message: "名前は50文字以内で入力してください。" }),
    email: z.email({ error: "有効なメールアドレスを入力してください。" }),
    password: z
      .string()
      .min(8, { message: "パスワードは8文字以上で入力してください。" }),
    passwordConfirmation: z
      .string()
      .min(1, { message: "確認用パスワードを入力してください。" }),
  })
  .refine((data) => data.password === data.passwordConfirmation, {
    message: "パスワードが一致しません。",
    path: ["passwordConfirmation"],
  });

type SignUpValues = z.infer<typeof signUpSchema>;

export default function SignUpPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [serverError, setServerError] = useState("");

  const form = useForm<SignUpValues>({
    resolver: zodResolver(signUpSchema),
    defaultValues: {
      name: "",
      email: "",
      password: "",
      passwordConfirmation: "",
    },
  });

  const handleSignUp = async (values: SignUpValues) => {
    setIsLoading(true);
    setServerError("");

    await authClient.signUp.email(
      { email: values.email, password: values.password, name: values.name },
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
          <CardTitle className="text-center text-2xl">新規登録</CardTitle>
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
          <form id="sign-up-form" onSubmit={form.handleSubmit(handleSignUp)}>
            <FieldGroup className="gap-4">
              <Controller
                name="name"
                control={form.control}
                render={({ field, fieldState }) => (
                  <Field data-invalid={fieldState.invalid} className="w-full">
                    <Input
                      {...field}
                      id="name"
                      aria-invalid={fieldState.invalid}
                      placeholder="名前"
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
              <Controller
                name="passwordConfirmation"
                control={form.control}
                render={({ field, fieldState }) => (
                  <Field data-invalid={fieldState.invalid} className="w-full">
                    <Input
                      {...field}
                      type="password"
                      id="passwordConfirmation"
                      aria-invalid={fieldState.invalid}
                      placeholder="確認用パスワード"
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
          <Field orientation="horizontal">
            <Button
              type="submit"
              form="sign-up-form"
              disabled={isLoading}
              className="w-full p-6 bg-blue-600 hover:bg-blue-800 text-lg text-white cursor-pointer transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? "Loading..." : "続ける"}
            </Button>
          </Field>
        </CardFooter>
        <p className="text-center text-sm text-muted-foreground pb-6">
          アカウントをお持ちの方はこちら
          <Link
            href="/sign-in"
            className="text-primary underline underline-offset-4 hover:opacity-80"
          >
            ログイン
          </Link>
        </p>
      </Card>
    </div>
  );
}
