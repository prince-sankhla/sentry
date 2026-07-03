export default function Loading() {
  return (
    <main className="min-h-screen bg-[#FAF8F5] px-5 py-8 text-[#333333] sm:px-8">
      <div className="mx-auto w-full max-w-[1600px]">
        <div className="h-4 w-40 rounded bg-[#E8D8B1]" />
        <div className="mt-4 h-10 w-72 rounded bg-[#F0E4C8]" />
        <div className="mt-6 grid gap-4 lg:grid-cols-[1fr_340px]">
          <div className="h-[720px] rounded-[16px] border border-[#E8D8B1] bg-white" />
          <div className="h-[720px] rounded-[16px] border border-[#E8D8B1] bg-white" />
        </div>
      </div>
    </main>
  );
}
