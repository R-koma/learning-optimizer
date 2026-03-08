import { fetchAPI } from "@/lib/api";

export default async function Home() {
  let status = "unknown";
  let dbConnected = false;

  try {
    const data = await fetchAPI("/api/health");
    status = data.status;
    dbConnected = data.db;
  } catch (error) {
    status = "error";
    console.error(error);
  }
  return (
    <main>
      <h1>Learning Optimizer</h1>
      <p className="mt-8">API Status: {status}</p>
      <p>DB Connected: {dbConnected ? "Yes" : "No"}</p>
    </main>
  );
}
