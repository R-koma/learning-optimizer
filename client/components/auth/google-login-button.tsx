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
    <Button variant="outline" size="lg" onClick={handleGoogleSignIn}>
      <FcGoogle />
      Googleでログイン
    </Button>
  );
}
