export default function Loading() {
  return (
    <main className="min-h-screen bg-[#0B0F14] px-5 py-8 sm:px-8">
      <div className="mx-auto w-full max-w-6xl">
        <div className="h-5 w-32 rounded bg-[#2A3441]" />
        <div className="mt-6 h-9 w-3/4 rounded bg-[#171F2A]" />
        <div className="mt-6 grid gap-5 lg:grid-cols-[1fr_340px]">
          <div className="h-72 rounded-[6px] border border-[#2A3441] bg-[#121821]" />
          <div className="h-56 rounded-[6px] border border-[#2A3441] bg-[#121821]" />
        </div>
      </div>
    </main>
  );
}
