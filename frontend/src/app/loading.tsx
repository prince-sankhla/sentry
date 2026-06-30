export default function Loading() {
  return (
    <main className="min-h-screen bg-[#0B0F14] px-5 py-8 text-[#E6E8EB] sm:px-8">
      <div className="mx-auto w-full max-w-7xl">
        <div className="h-4 w-44 rounded bg-[#2A3441]" />
        <div className="mt-3 h-10 w-80 max-w-full rounded bg-[#171F2A]" />
        <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div className="h-32 rounded-[6px] border border-[#2A3441] bg-[#121821] p-5" key={index}>
              <div className="h-3 w-24 rounded bg-[#2A3441]" />
              <div className="mt-5 h-7 w-28 rounded bg-[#171F2A]" />
            </div>
          ))}
        </div>
        <div className="mt-6 grid gap-5 xl:grid-cols-[1.35fr_1fr]">
          <div className="h-96 rounded-[6px] border border-[#2A3441] bg-[#121821]" />
          <div className="h-96 rounded-[6px] border border-[#2A3441] bg-[#121821]" />
        </div>
      </div>
    </main>
  );
}
