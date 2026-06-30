"use client";

import Link from "next/link";

export default function Error({ reset }: { reset: () => void }) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#0B0F14] px-5 text-[#E6E8EB]">
      <div className="w-full max-w-md rounded-[6px] border border-[#2A3441] bg-[#121821] p-6 text-center">
        <h1 className="text-xl font-semibold text-[#E6E8EB]">Unable to load graph</h1>
        <p className="mt-2 text-sm leading-6 text-[#9AA4AF]">The investigation graph API did not return a successful response.</p>
        <div className="mt-5 flex justify-center gap-3">
          <button className="rounded-[4px] border border-[#C58B2A] bg-[#2A2115] px-4 py-2 text-sm font-semibold text-[#F3D59A] hover:bg-[#332719]" onClick={reset} type="button">
            Retry
          </button>
          <Link className="rounded-[4px] border border-[#2A3441] px-4 py-2 text-sm font-semibold" href="/">
            Dashboard
          </Link>
        </div>
      </div>
    </main>
  );
}
