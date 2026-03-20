import SignInPage from "./(auth)/sign-in/page";
import LearnPage from "./(main)/learn/page";

export default async function Home() {
  return (
    <main>
      {/* <SignInPage /> */}
      <LearnPage />
    </main>
  );
}
