"use client";

/**
 * Shortcut help: every bound command, grouped NAVIGATE / SEARCH / ACTIONS, with the keys as this
 * platform shows them. Opened with `?` or from the palette; closed with Escape; focus goes back.
 */
import { useEffect, useRef } from "react";
import Link from "next/link";
import { useLocale } from "@/lib/i18n";
import { useCommands } from "@/lib/commands";
import { COMMANDS } from "@/lib/commands/shortcuts";
import { byId } from "@/lib/commands/destinations";

export function ShortcutHelp({ onClose }: { onClose: () => void }) {
  const { t } = useLocale();
  const copy = t.commands;
  const cmd = useCommands();
  const closer = useRef<HTMLButtonElement>(null);
  const opener = useRef<HTMLElement | null>(null);
  useEffect(() => {
    opener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    closer.current?.focus();
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") { e.preventDefault(); onClose(); } };
    document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("keydown", esc); opener.current?.isConnected && opener.current.focus(); };
  }, [onClose]);
  const groups: Array<{ label: string; kind: "navigate" | "search" | "action" }> = [{ label: copy.navigate, kind: "navigate" }, { label: copy.searchGroup, kind: "search" }, { label: copy.actionsGroup, kind: "action" }];
  const device = cmd.profile.platform === "mac" || cmd.profile.platform === "ios" ? copy.deviceMac : cmd.profile.platform === "windows" ? copy.deviceWindows : cmd.profile.platform === "linux" ? copy.deviceLinux : copy.deviceOther;
  return (
    <div role="dialog" aria-modal="true" aria-label={copy.keyboardShortcuts} data-owns-keyboard="true" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
         style={{ position: "fixed", inset: 0, zIndex: 80, background: "rgba(24,24,27,.3)", display: "flex", alignItems: "flex-start", justifyContent: "center", padding: "8vh 16px 16px" }}>
      <div className="cmd cmd--help">
        <div className="cmd-help-h">
          <h2>{copy.keyboardShortcuts}</h2>
          <button ref={closer} type="button" className="zb zb--tertiary zb--sm" onClick={onClose}>{copy.close}</button>
        </div>
        <p className="zhelp" style={{ padding: "0 16px" }}>{device}. {copy.chordPrefix}</p>
        <div className="cmd-help-body">
          {groups.map((g) => {
            const items = COMMANDS.filter((c) => c.kind === g.kind && cmd.bindings[c.id] && (!c.destination || cmd.visibility.can(byId(c.destination)?.capability ?? "view")));
            if (!items.length) return null;
            return (
              <section key={g.kind}>
                <h3>{g.label}</h3>
                <dl>
                  {items.map((c) => <div key={c.id}><dt>{cmd.commandLabel(c)}</dt><dd><kbd>{cmd.display(c.id)}</kbd></dd></div>)}
                </dl>
              </section>
            );
          })}
        </div>
        <div className="cmd-foot"><Link href="/settings/shortcuts" onClick={onClose}>{copy.shortcutsTitle} →</Link></div>
      </div>
    </div>
  );
}
