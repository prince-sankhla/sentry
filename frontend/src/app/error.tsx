"use client";

export default function Error({ reset }: { reset: () => void }) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#FAF8F5] px-5 text-[#333333]">
      <div className="w-full max-w-md rounded-[16px] border border-[#E8D8B1] bg-white p-6 text-center shadow-[0_20px_50px_rgba(87,63,14,0.08)]">
        <h1 className="text-xl font-semibold text-[#2F2F2F]">Unable to load tenders</h1>
        <p className="mt-2 text-sm leading-6 text-[#6B7280]">
          The backend API did not return a successful response.
        </p>
        <button
          className="mt-5 rounded-[14px] border border-[#D4A74B] bg-[#FFF5DD] px-4 py-2 text-sm font-semibold text-[#8A6412] hover:bg-[#F9E7B8]"
          onClick={reset}
          type="button"
        >
          Retry
        </button>
      </div>
    </main>
  );
}
