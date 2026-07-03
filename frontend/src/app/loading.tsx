export default function Loading() {
  return (
    <main className="min-h-screen bg-[#FAF8F5] px-5 py-8 text-[#333333] sm:px-8">
      <div className="mx-auto w-full max-w-[1600px]">
        <div className="h-4 w-44 rounded bg-[#E8D8B1]" />
        <div className="mt-3 h-10 w-80 max-w-full rounded bg-[#F0E4C8]" />
        <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div className="h-32 rounded-[16px] border border-[#E8D8B1] bg-white p-5" key={index}>
              <div className="h-3 w-24 rounded bg-[#F0E4C8]" />
              <div className="mt-5 h-7 w-28 rounded bg-[#F8F2E4]" />
            </div>
          ))}
        </div>
        <div className="mt-6 grid gap-5 xl:grid-cols-[1.35fr_1fr]">
          <div className="h-96 rounded-[16px] border border-[#E8D8B1] bg-white" />
          <div className="h-96 rounded-[16px] border border-[#E8D8B1] bg-white" />
        </div>
      </div>
    </main>
  );
}
