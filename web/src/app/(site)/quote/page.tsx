import type { Metadata } from "next";
import { QuoteForm } from "@/components/site/QuoteForm";
import { pageMetadata } from "@/lib/seo";

export const metadata: Metadata = pageMetadata({
  title: "Get a company quote",
  description: "ZAAD is priced per company. Tell us what you import and we will reply with a quote and a workspace to run the diagnostic on your own history.",
  path: "/quote",
});

export default function QuotePage() {
  return (
    <div className="formpage">
      <p className="eyebrow">Get a company quote</p>
      <h1 className="h1">Priced for how you actually buy.</h1>
      <p className="lede">
        ZAAD is in pilot and priced per company, because the work depends on how many products, suppliers
        and sites you run. Tell us five things and a person will reply within two working days with a quote
        and a workspace to run the diagnostic on your own history.
      </p>
      <QuoteForm />
    </div>
  );
}
