type HealthResponse = {
  status: string;
  service: string;
  version: string;
};

const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${backendUrl}/health`, {
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error("Failed to fetch backend health");
  }

  return response.json();
}

export default async function Home() {
  const health = await getHealth();

  return (
    <main className="min-h-screen p-8">
      <pre>{JSON.stringify(health, null, 2)}</pre>
    </main>
  );
}
