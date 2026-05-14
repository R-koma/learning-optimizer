"use client";

import { authClient } from "@/lib/auth-client";
import { Button } from "../ui/button";
import { FcGoogle } from "react-icons/fc";

export default function GoogleLoginButton() {
  const handleGoogleSignIn = async () => {
    await authClient.signIn.social({
      provider: "google",
      callbackURL: "/dashboard",
    });
  };
  return (
    <Button
      variant="outline"
      className="w-full h-11 cursor-pointer"
      onClick={handleGoogleSignIn}
    >
      <FcGoogle />
      <p className="text-sm text-slate-700 dark:text-slate-300">
        Google で続ける
      </p>
    </Button>
  );
}
