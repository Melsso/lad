import type { ReactNode } from "react";

import { Sidebar } from "./Sidebar";

interface AppLayoutProps {
  children: ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  return (
    <div className="flex h-full w-full">
      <Sidebar />

      <main className="min-w-0 flex-1">{children}</main>
    </div>
  );
}
