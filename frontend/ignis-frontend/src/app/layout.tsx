import type { Metadata } from "next";
import "./globals.css";
import { CompareProvider } from "@/context/CompareContext";
import { CompareTray } from "@/components/layout/CompareTray";
import { Footer } from "@/components/layout/Footer";
import { TopNav } from "@/components/layout/TopNav";

export const metadata: Metadata = {
  title: "IGNIS | NASA microgravity fire research discovery",
  description:
    "Find, compare and question NASA microgravity combustion investigations, with every answer traced back to its source.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <CompareProvider>
          <TopNav />
          <main>{children}</main>
          <Footer />
          <CompareTray />
        </CompareProvider>
      </body>
    </html>
  );
}
