import { AppShell } from "@/components/layout/AppShell";
import { DemoAdStrip } from "@/components/ads/DemoAdStrip";

export default function Home() {
  return (
    <div className="page-root">
      <AppShell />
      <DemoAdStrip />
    </div>
  );
}
