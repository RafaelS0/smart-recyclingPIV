import { getDashboard } from "@/lib/api";
import { Dashboard } from "@/components/dashboard";
export const dynamic = "force-dynamic";
export default async function Page() {
  const data = await getDashboard();
  return <Dashboard initial={data} />;
}
