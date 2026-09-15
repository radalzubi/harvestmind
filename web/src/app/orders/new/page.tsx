"use client";

/**
 * CREATE A PURCHASE ORDER — the same document, whichever of the four ways it starts.
 *
 * `?sku=` and `?supplier=` prefill from Inventory. `?decision=` prefills the quantities ZAAD
 * recommended, and records which decision they came from. `?amend=` turns it into a proposed
 * change to an order that already exists, which never touches the imported record.
 *
 * Nothing is stored until the buyer presses the button.
 */
import { Suspense, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Gate } from "@/components/workspace/Gate";
import { Button, ButtonLink, Loading, Notice, PageHead, Section } from "@/components/workspace/ui";
import { SelectField } from "@/components/workspace/Table";
import { EMPTY_HEADER, HeaderFields, LineEditor, type OrderHeader } from "@/components/workspace/OrderForm";
import { useToast } from "@/components/Toast";
import { useWorkspaceData } from "@/lib/zaad/workspace-data";
import {
  AMENDMENT_LABEL, createDraft, fetchImportedOrder, fetchSku,
  type AmendmentAction, type DraftLine,
} from "@/lib/zaad/product";
import { proposalFromDecision } from "@/lib/zaad/bulk";

const AMENDMENTS: AmendmentAction[] = ["DEFER", "EXPEDITE", "REDUCE", "CANCEL", "SPLIT", "KEEP"];

function NewOrderBody() {
  const params = useSearchParams();
  const router = useRouter();
  const toast = useToast();
  const { request, decisions } = useWorkspaceData();

  const amendPo = params.get("amend");
  const decisionId = params.get("decision");
  const prefillSku = params.get("sku");
  const prefillSupplier = params.get("supplier");

  const [header, setHeader] = useState<OrderHeader>({
    ...EMPTY_HEADER,
    supplier_id: prefillSupplier ?? "",
    currency: request?.currency ?? "USD",
  });
  const [lines, setLines] = useState<DraftLine[]>([]);
  const [action, setAction] = useState<AmendmentAction>("DEFER");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(Boolean(amendPo || prefillSku));

  const locations = useMemo(() => (request?.locations ?? []).map((l) => l.id), [request]);
  const decision = useMemo(() => decisions.find((d) => d.id === decisionId) ?? null, [decisions, decisionId]);
  // The quantities ZAAD recommended, through the same rule bulk creation uses; a decision that
  // cannot become lines without guessing says why instead of leaving the form silently empty.
  const fromDecision = useMemo(() => decision ? proposalFromDecision(decision) : null, [decision]);
  const [prefilled, setPrefilled] = useState(false);
  useEffect(() => {
    if (!fromDecision || prefilled || amendPo || prefillSku) return;
    if ("group" in fromDecision) {
      const g = fromDecision.group;
      setLines(g.lines.map((l) => ({ sku: l.sku, quantity: l.quantity, unit_price: l.unit_price, units_per_case: l.units_per_case })));
      setHeader((h) => ({ ...h, supplier_id: g.transfer_origin_id ? "" : (h.supplier_id || g.supplier_id), destination_id: h.destination_id || (g.destination_id ?? "") }));
    }
    setPrefilled(true);
  }, [fromDecision, prefilled, amendPo, prefillSku]);

  // Prefill: an amendment carries the imported order's lines; a product carries one line.
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        if (amendPo) {
          const order = await fetchImportedOrder(amendPo);
          if (!alive) return;
          setLines(order.lines.map((l) => ({
            sku: String(l.sku), quantity: Number(l.qty_ordered ?? 0),
            unit_price: l.unit_cost != null ? Number(l.unit_cost) : null,
          })));
          setHeader((h) => ({
            ...h,
            supplier_id: h.supplier_id || String(order.supplier?.supplier_id ?? ""),
            reference: h.reference || `Change to ${amendPo}`,
          }));
        } else if (prefillSku) {
          const detail = await fetchSku(prefillSku);
          if (!alive) return;
          const pack = detail.overview.units_per_case ?? null;
          setLines([{
            sku: prefillSku,
            quantity: pack ? Number(pack) : Math.max(1, Math.round(detail.overview.weekly_demand ?? 1)),
            unit_price: detail.overview.unit_cost ?? null,
            units_per_case: pack,
          }]);
          setHeader((h) => ({ ...h, supplier_id: h.supplier_id || String(detail.overview.supplier_id ?? "") }));
        }
      } catch (e) {
        if (alive) setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, [amendPo, prefillSku]);

  const origin = amendPo ? "IMPORTED_AMENDMENT" : decisionId ? "ZAAD_RECOMMENDATION" : "MANUAL";
  const transferFrom = fromDecision && "group" in fromDecision ? (fromDecision.group.transfer_origin_id ?? null) : null;

  async function create() {
    setBusy(true);
    setError(null);
    try {
      const draft = await createDraft({
        origin,
        ...header,
        currency: header.currency.toUpperCase(),
        requested_receipt_date: header.requested_receipt_date || null,
        source_po_id: amendPo ?? null,
        source_decision_id: decisionId ?? null,
        transfer_origin_id: transferFrom,
        supplier_id: transferFrom ? null : header.supplier_id,
        amendment_action: amendPo ? action : null,
        lines: lines.filter((l) => l.sku.trim() && Number(l.quantity) > 0),
      });
      toast.push("Proposal created. Nothing has been sent to a supplier.");
      router.push(`/orders/${encodeURIComponent(draft.draft_id)}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setBusy(false);
    }
  }

  if (loading) return <Loading label="Reading what this is based on…" cards={2} />;

  return (
    <>
      <PageHead
        title={amendPo ? `Propose a change to ${amendPo}` : transferFrom ? `Propose a transfer from ${transferFrom}` : "Create a purchase order"}
        sub={amendPo
          ? "The order in your system is not touched. This is a proposal against it, which someone approves and you export."
          : transferFrom
            ? "A proposed move of your own stock between two of your sites. Someone approves it and you export it; ZAAD does not raise the transfer."
            : "A proposed order ZAAD can evaluate, someone approves, and you export in your own format. It is never sent to a supplier."}
        // "Cancel" also sits at the foot of the form, next to the button it cancels. Up here it is
        // navigation, so it is named as navigation — the same label the other order pages use.
        actions={<ButtonLink size="sm" href="/orders">Purchase orders</ButtonLink>}
      />

      {decision && (
        <Notice tone={fromDecision && "reason" in fromDecision ? "warn" : undefined}>
          Starting from ZAAD&rsquo;s recommendation: <strong>{decision.headline}</strong>.{" "}
          <Link href={`/decisions?decision=${encodeURIComponent(decision.id)}`}>See the reasoning</Link>.
          {fromDecision && "reason" in fromDecision
            ? <> The lines could not be filled in from it: {fromDecision.reason} Enter them below.</>
            : " The quantities below are what ZAAD recommended; edit anything before you create it."}
        </Notice>
      )}

      {amendPo && (
        <Section title="What should change">
          <div className="tbar">
            <SelectField value={action} onChange={(v) => setAction(v as AmendmentAction)} label="Change"
              all="" options={AMENDMENTS.map((a) => ({ value: a, label: AMENDMENT_LABEL[a] }))} />
          </div>
          <Notice>
            ZAAD prices a change only where you have declared the contractual right to make it. If no right is
            declared for this order, the proposal is still recorded — ZAAD simply will not tell you what it is worth.
          </Notice>
        </Section>
      )}

      <Section title="The order">
        <HeaderFields value={header} onChange={setHeader} locations={locations} />
      </Section>

      <Section title="Lines">
        <LineEditor lines={lines} onChange={setLines} currency={header.currency || "USD"} />
      </Section>

      <Section title="Notes">
        <textarea className="fld fld--block" rows={3} value={header.notes}
          aria-label="Notes on this proposal" placeholder="Anything the approver should know"
          onChange={(e) => setHeader({ ...header, notes: e.target.value })} />
      </Section>

      {error && <div style={{ marginTop: 14 }}><Notice tone="warn">{error}</Notice></div>}

      <div style={{ marginTop: 20, display: "flex", gap: 8, flexWrap: "wrap" }}>
        <Button role="primary" pending={busy} onClick={create}
          disabled={!lines.some((l) => l.sku.trim() && Number(l.quantity) > 0)}>
          Create the proposal
        </Button>
        <ButtonLink href="/orders">Cancel</ButtonLink>
      </div>
      <p className="zhelp" style={{ marginTop: 10 }}>
        Creating a proposal stores a document in your workspace. It does not place an order, email a supplier or
        touch your ERP.
      </p>
    </>
  );
}

export default function NewOrderPage() {
  return (
    <Gate loadingLabel="Opening your workspace…" needsPlan={false} needsWorkspace={false}>
      <Suspense fallback={<Loading label="Opening the editor…" cards={2} />}>
        <NewOrderBody />
      </Suspense>
    </Gate>
  );
}
