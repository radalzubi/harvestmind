"use client";

/**
 * SETTINGS → SHORTCUTS. Every command with its binding on this device; change (press the keys),
 * remove, restore, reset all; collisions and reserved combinations refused with the reason.
 * Pinned pages and the phone's quick actions are edited here too. User preferences travel with
 * the workspace; the device only decides how a logical binding is shown and matched.
 */
import { useEffect, useMemo, useState } from "react";
import { Gate } from "@/components/workspace/Gate";
import { Button, Notice, PageHead, Section } from "@/components/workspace/ui";
import { useLocale } from "@/lib/i18n";
import { useCommands } from "@/lib/commands";
import { MAX_PINNED, MAX_QUICK_ACTIONS, visible } from "@/lib/commands/destinations";
import { COMMANDS, bindingProblem, collidesWith, comboOf, commandById, normaliseBinding, CHORD_PREFIX, type Command } from "@/lib/commands/shortcuts";

function Body() {
  const { t } = useLocale();
  const copy = t.commands;
  const cmd = useCommands();
  const [q, setQ] = useState("");
  const [recording, setRecording] = useState<string | null>(null);
  const [pendingPrefix, setPendingPrefix] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const needle = q.trim().toLowerCase();
  const rows = useMemo(() => COMMANDS.filter((c) => !needle || cmd.commandLabel(c).toLowerCase().includes(needle) || c.id.toLowerCase().includes(needle)), [needle, cmd]);
  const groups: Array<{ kind: Command["kind"]; label: string }> = [{ kind: "navigate", label: copy.navigate }, { kind: "search", label: copy.searchGroup }, { kind: "action", label: copy.actionsGroup }];

  // record a binding: a combination in one keydown, or G then a key
  useEffect(() => {
    if (!recording) return;
    const on = (e: KeyboardEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (e.key === "Escape") { setRecording(null); setPendingPrefix(false); setProblem(null); return; }
      const key = e.key.length === 1 ? e.key.toLowerCase() : e.key.toLowerCase();
      if (["meta", "control", "alt", "shift"].includes(key)) return;
      const combo = comboOf(e, cmd.profile.platform);
      if (!combo) return;
      let candidate: string | null = null;
      if (pendingPrefix && !combo.includes("+")) candidate = `${CHORD_PREFIX} ${key}`;
      else if (!combo.includes("+") && key === CHORD_PREFIX) { setPendingPrefix(true); return; }
      else candidate = combo;
      const normal = normaliseBinding(candidate);
      const why = normal ? bindingProblem(normal) : "not_a_binding";
      if (why) { setProblem({ reserved: copy.reserved, bare_key: copy.bareKey, chord_prefix: copy.chordPrefix, not_a_binding: copy.notABinding }[why] ?? copy.notABinding); setPendingPrefix(false); return; }
      const other = collidesWith(cmd.bindings, recording, normal!);
      if (other) { const c = commandById(other); setProblem(`${copy.collision} ${c ? cmd.commandLabel(c) : other}.`); setPendingPrefix(false); return; }
      cmd.setBinding(recording, normal!);
      setRecording(null); setPendingPrefix(false); setProblem(null);
    };
    window.addEventListener("keydown", on, true);
    return () => window.removeEventListener("keydown", on, true);
  }, [recording, pendingPrefix, cmd, copy]);

  const device = cmd.profile.platform === "mac" || cmd.profile.platform === "ios" ? copy.deviceMac : cmd.profile.platform === "windows" ? copy.deviceWindows : cmd.profile.platform === "linux" ? copy.deviceLinux : copy.deviceOther;
  const quickCandidates = visible({ ...cmd.visibility, device: "phone" }).filter((d) => d.quickAction);
  const pinCandidates = visible({ ...cmd.visibility, device: "desktop" }).filter((d) => d.pinnable);

  return (
    <>
      <PageHead title={copy.shortcutsTitle} sub={copy.shortcutsSub} actions={<Button role="secondary" size="sm" onClick={cmd.resetAll}>{copy.resetAll}</Button>} />
      <p className="zhelp">{device}. {cmd.profile.device === "phone" ? copy.phoneHint : cmd.profile.device === "tablet" ? copy.tabletHint : copy.chordPrefix}</p>
      {problem && <Notice tone="warn">{problem}</Notice>}
      <Section title={copy.keyboardShortcuts}>
        <label className="fld-wrap" style={{ marginBottom: 10 }}><span className="sr-only">{copy.search}</span>
          <input className="fld fld--search" placeholder={copy.search} aria-label={copy.search} value={q} onChange={(e) => setQ(e.target.value)} /></label>
        {groups.map((g) => {
          const items = rows.filter((c) => c.kind === g.kind);
          if (!items.length) return null;
          return (
            <div key={g.kind} className="tbl-wrap" style={{ marginBottom: 16 }}>
              <table className="tbl tbl--dense">
                <caption className="sr-only">{g.label}</caption>
                <thead><tr><th scope="col">{g.label}</th><th scope="col">{copy.binding}</th><th scope="col"><span className="sr-only">{copy.change}</span></th></tr></thead>
                <tbody>
                  {items.map((c) => {
                    const bound = cmd.bindings[c.id];
                    const isDefault = bound === c.defaultBinding;
                    return (
                      <tr key={c.id}>
                        <td>{cmd.commandLabel(c)}</td>
                        <td>{recording === c.id ? <span className="cmd-rec" aria-live="polite">{pendingPrefix ? copy.chordArmed : copy.recording} <small>({copy.pressKeys})</small></span>
                              : bound ? <kbd className="cmd-kbd">{cmd.display(c.id)}</kbd> : <span className="na">{copy.none}</span>}</td>
                        <td data-align="end" style={{ whiteSpace: "nowrap" }}>
                          {recording === c.id ? <Button role="tertiary" size="sm" onClick={() => { setRecording(null); setPendingPrefix(false); setProblem(null); }}>{copy.cancel}</Button> : (
                            <>
                              <Button role="tertiary" size="sm" onClick={() => { setRecording(c.id); setProblem(null); setPendingPrefix(false); }}>{copy.change}</Button>
                              {bound && <Button role="tertiary" size="sm" onClick={() => cmd.setBinding(c.id, null)}>{copy.remove}</Button>}
                              {!isDefault && <Button role="tertiary" size="sm" onClick={() => cmd.restoreDefault(c.id)}>{copy.restore}</Button>}
                            </>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          );
        })}
      </Section>
      <Section title={copy.quickActions}>
        <p className="zhelp">{copy.quickActionsHint}</p>
        <div className="chips">
          {quickCandidates.map((d) => { const on = cmd.quickActions.some((x) => x.id === d.id); return (
            <button key={d.id} type="button" className="chip" aria-pressed={on} disabled={!on && cmd.prefs.quickActions.length >= MAX_QUICK_ACTIONS && cmd.prefs.quickActions.length > 0}
                    onClick={() => { const current = cmd.quickActions.map((x) => x.id); cmd.setQuickActions(on ? current.filter((x) => x !== d.id) : [...current, d.id].slice(-MAX_QUICK_ACTIONS)); }}>{cmd.label(d)}</button>
          ); })}
        </div>
      </Section>
      <Section title={copy.pinned}>
        <p className="zhelp">{copy.pinnedHint} ({MAX_PINNED})</p>
        <div className="chips">
          {pinCandidates.map((d) => { const on = cmd.pinned.some((x) => x.id === d.id); return (
            <button key={d.id} type="button" className="chip" aria-pressed={on} onClick={() => cmd.togglePinned(d.id)}>{cmd.label(d)}</button>
          ); })}
        </div>
      </Section>
    </>
  );
}

export default function ShortcutsPage() {
  return <Gate needsWorkspace={false}><Body /></Gate>;
}
