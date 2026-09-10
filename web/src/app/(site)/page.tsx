import type { Metadata } from "next";
import { HomeContent } from "@/components/site/HomeContent";
import { JsonLd } from "@/components/site/JsonLd";
import { HOME_DESCRIPTION, HOME_TITLE, organizationJsonLd, pageMetadata, websiteJsonLd } from "@/lib/seo";

// The homepage title carries the brand once, concisely; the layout template is not applied here.
export const metadata: Metadata = { ...pageMetadata({ title: HOME_TITLE, description: HOME_DESCRIPTION, path: "/" }), title: { absolute: HOME_TITLE } };

export default async function Home({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const sp = await searchParams;
  return (
    <>
      <JsonLd data={[websiteJsonLd(), organizationJsonLd()]} />
      <HomeContent qa={sp?.motion === "off"} />
    </>
  );
}
