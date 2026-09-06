import Link from "next/link";

/**
 * The wordmark: "zaad" in a tight geometric setting with a seed dot.
 * One element, no image, scales with font size so it stays crisp anywhere.
 */
export function Logo({ size = 22, href = "/", muted = false }: { size?: number; href?: string | null; muted?: boolean }) {
  const mark = (
    <span className={muted ? "wordmark wordmark-muted" : "wordmark"} style={{ fontSize: size }} aria-label="zaad">
      zaad<span className="wordmark-seed" aria-hidden />
    </span>
  );
  if (href === null) return mark;
  return <Link href={href} className="wordmark-link" aria-label="zaad home">{mark}</Link>;
}
