const strategyApi = process.env.NEXT_PUBLIC_STRATEGY_API_URL || "http://localhost:8000";
const generationApi = process.env.NEXT_PUBLIC_GENERATION_API_URL || "http://localhost:8001";

async function checkHealth(url) {
  try {
    const res = await fetch(`${url}/health`, { cache: "no-store" });
    if (!res.ok) return "DOWN";
    const data = await res.json();
    return data.status === "ok" ? "UP" : "UNKNOWN";
  } catch {
    return "DOWN";
  }
}

export default async function Home() {
  const [strategyStatus, generationStatus] = await Promise.all([
    checkHealth(strategyApi),
    checkHealth(generationApi),
  ]);

  return (
    <main className="container">
      <h1>Youticle Team Workspace</h1>
      <p>3-service skeleton: strategy backend, generation backend, next frontend</p>

      <section className="grid">
        <article className="card">
          <h2>Strategy Backend</h2>
          <p>URL: {strategyApi}</p>
          <p>Status: {strategyStatus}</p>
          <p>Endpoint: POST /api/v1/strategy/plan</p>
        </article>
        <article className="card">
          <h2>Generation Backend</h2>
          <p>URL: {generationApi}</p>
          <p>Status: {generationStatus}</p>
          <p>Endpoints: /api/v1/generation/text|image|audio|video/jobs</p>
        </article>
      </section>
    </main>
  );
}
