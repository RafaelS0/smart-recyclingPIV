import "server-only";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { BASE, DashboardData } from "./types";
export async function getDashboard(): Promise<DashboardData> {
  const token = (await cookies()).get("sr_session")?.value;
  if (!token) redirect(BASE + "/login");
  const headers = { Cookie: `sr_session=${token}` };
  const origin = process.env.API_INTERNAL_URL || "http://127.0.0.1:18080";
  const responses = await Promise.all(
    ["/api/overview", "/api/readings?limit=200", "/api/v1/devices", "/api/lixeiras"].map(
      (path) =>
        fetch(origin + path, {
          headers,
          cache: "no-store",
          signal: AbortSignal.timeout(10000),
        }),
    ),
  );
  if (responses.some((r) => r.status === 401)) redirect(BASE + "/login");
  if (responses.some((r) => !r.ok))
    throw new Error("A central de dados está temporariamente indisponível.");
  const [summary, readings, devices, bins] = await Promise.all(
    responses.map((r) => r.json()),
  );
  return { summary, readings, devices, bins: bins.items };
}
