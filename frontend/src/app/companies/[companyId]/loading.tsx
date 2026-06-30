export default function Loading() {
  return (
    <main className="min-h-screen bg-[#0B0F14] px-5 py-8 text-[#E6E8EB] sm:px-8">
      <div className="mx-auto grid w-full max-w-7xl gap-5 xl:grid-cols-[340px_1fr]">
        <aside className="space-y-5">
          <div className="h-72 rounded-[6px] border border-[#2A3441] bg-[#121821]" />
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
            {Array.from({ length: 4 }).map((_, index) => (
              <div className="h-24 rounded-[6px] border border-[#2A3441] bg-[#121821]" key={index} />
            ))}
          </div>
        </aside>
        <div className="space-y-5">
          <div className="h-36 rounded-[6px] border border-[#2A3441] bg-[#121821]" />
          <div className="h-96 rounded-[6px] border border-[#2A3441] bg-[#121821]" />
          <div className="h-72 rounded-[6px] border border-[#2A3441] bg-[#121821]" />
        </div>
      </div>
    </main>
  );
}
