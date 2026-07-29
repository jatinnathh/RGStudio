"use client";

import dynamic from "next/dynamic";

const ArtCanvas = dynamic(() => import("./components/ArtCanvas"), {
  ssr: false,
  loading: () => (
    <div className="fixed inset-0 bg-[#1d0a1b] flex items-center justify-center text-white">
      <div className="w-8 h-8 rounded-full border-2 border-orange-500 border-t-transparent animate-spin" />
    </div>
  ),
});

export default function Home() {
  return (
    <main className="w-full min-h-screen bg-[#1d0a1b] text-white">
      <ArtCanvas />
    </main>
  );
}