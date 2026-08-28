import type { ReactNode } from "react";

import { Sidebar } from "./Sidebar";

interface AppLayoutProps {
  children: ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  return (
    <div className="app-layout">
      <Sidebar />

      <main className="main-content">{children}</main>
    </div>
  );
}
