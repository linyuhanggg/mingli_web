import { redirect } from "next/navigation";


export default async function LegacyReadingPage({
  params,
}: {
  params: Promise<{ readingId: string }>;
}) {
  const { readingId } = await params;
  redirect(`/account/history/${readingId}`);
}
