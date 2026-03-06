import { fetchAPI } from "@/lib/api";

export default async function Home() {
  let status = "unknown";
  let dbConnected = false;

  try {
    const data = await fetchAPI("/api/helth");
    status = data.status;
    dbConnected = data.db;
  } catch (error) {
    status = "error";
    console.error(error);
  }
  return (
    <main>
      <h1>Learning Optimizer</h1>
      <p>API Status: {status}</p>
      <p>DB Connected: {dbConnected ? "Yes" : "No"}</p>
    </main>
  );
}
