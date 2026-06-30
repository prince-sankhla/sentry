export default function Loading() {
  return (
    <main className="min-h-screen bg-[#0B0F14] px-5 py-8 text-[#E6E8EB] sm:px-8">
      <div className="mx-auto w-full max-w-7xl">
        <div className="h-4 w-40 rounded bg-[#2A3441]" />
        <div className="mt-4 h-10 w-72 rounded bg-[#171F2A]" />
        <div className="mt-6 grid gap-4 lg:grid-cols-[1fr_340px]">
          <div className="h-[720px] rounded-[6px] border border-[#2A3441] bg-[#121821]" />
          <div className="h-[720px] rounded-[6px] border border-[#2A3441] bg-[#121821]" />
        </div>
      </div>
    </main>
  );
}
