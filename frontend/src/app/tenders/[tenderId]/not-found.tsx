import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#0B0F14] px-5 text-[#E6E8EB]">
      <div className="w-full max-w-md rounded-[6px] border border-[#2A3441] bg-[#121821] p-6 text-center">
        <h1 className="text-xl font-semibold">Tender not found</h1>
        <p className="mt-2 text-sm text-[#9AA4AF]">This tender is not available in the backend database.</p>
        <Link
          className="mt-5 inline-flex rounded-[4px] border border-[#C58B2A] bg-[#2A2115] px-4 py-2 text-sm font-semibold text-[#F3D59A] hover:bg-[#332719]"
          href="/tenders"
        >
          Back to tenders
        </Link>
      </div>
    </main>
  );
}
