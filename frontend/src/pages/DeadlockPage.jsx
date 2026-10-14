import React, { useState } from 'react';
import { Workflow } from 'lucide-react';
import { SATS, api, usePoll, useAction, PageHeader, Panel, Btn, Select, ErrorNote, Stat } from '../lib/fa2';

const POS = (() => {
  const out = {};
  SATS.forEach((s, i) => {
    const a = -Math.PI / 2 + (i * 2 * Math.PI) / SATS.length;
    out[s] = { x: 260 + 150 * Math.cos(a), y: 200 + 150 * Math.sin(a) };
  });
  return out;
})();

function WaitForGraph({ edges, cycle = [], victim }) {
  const inCycle = (e) => cycle.includes(e.from) && cycle.includes(e.to);
  return (
    <svg viewBox="0 0 520 400" className="w-full max-w-xl mx-auto" role="img" aria-label="Wait-for graph">
      <defs>
        <marker id="wfg-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#64748b" /></marker>
        <marker id="wfg-arrow-red" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#f43f5e" /></marker>
      </defs>
      {edges.map((e, i) => {
        const a = POS[e.from];
        const b = POS[e.to];
        if (!a || !b) return null;
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const len = Math.hypot(dx, dy) || 1;
        const r = 34;
        const red = inCycle(e);
        return <line key={i} x1={a.x + (dx / len) * r} y1={a.y + (dy / len) * r} x2={b.x - (dx / len) * r} y2={b.y - (dy / len) * r}
          stroke={red ? '#f43f5e' : '#64748b'} strokeWidth={red ? 2.5 : 1.5} markerEnd={`url(#${red ? 'wfg-arrow-red' : 'wfg-arrow'})`} />;
      })}
      {SATS.map((s) => (
        <g key={s}>
          <circle cx={POS[s].x} cy={POS[s].y} r="30" fill={s === victim ? 'rgba(244,63,94,0.18)' : '#0f172a'} stroke={s === victim ? '#f43f5e' : '#334155'} strokeWidth="1.5" />
          <text x={POS[s].x} y={POS[s].y + 4} textAnchor="middle" fill="#e2e8f0" fontSize="13" fontFamily="JetBrains Mono, monospace">{s}</text>
          {s === victim && <text x={POS[s].x} y={POS[s].y + 48} textAnchor="middle" fill="#fda4af" fontSize="11">victim</text>}
        </g>
      ))}
    </svg>
  );
}

export default function DeadlockPage() {
  const [mode, setMode] = useState('cycle');
  const [members, setMembers] = useState(['SAT-01', 'SAT-02', 'SAT-03']);
  const [result, setResult] = useState(null);
  const [live] = usePoll('/api/fa2/deadlock/graph', 1000);
  const { busy, error, run } = useAction();

  const toggle = (s) => setMembers((m) => (m.includes(s) ? m.filter((x) => x !== s) : [...m, s].sort()));
  const go = async () => {
    const res = await run('run', () => api('/api/fa2/deadlock/run', { method: 'POST', body: { mode, members } }));
    if (res) setResult(res);
  };
  const liveEdges = live?.edges || [];
  const det = result?.detections?.[0];

  return (
    <div className="space-y-6">
      <PageHeader
        icon={Workflow}
        title="Deadlock Detection (Chandy–Misra–Haas)"
        subtitle="Each satellite keeps its own relay transponder and asks for its neighbour's. A satellite blocked for 1 s sends a PROBE along its wait-for edge; blocked satellites forward it, unblocked ones drop it. A probe that returns to its sender proves a cycle; the youngest request aborts."
      />

      <Panel title="Run a scenario">
        <div className="flex flex-wrap items-end gap-3">
          <Select label="Shape" value={mode} onChange={setMode} options={[{ value: 'cycle', label: 'Cycle (each wants the next, last wants the first)' }, { value: 'chain', label: 'Chain (last one wants nothing: no deadlock)' }]} />
          <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
            <span>Satellites</span>
            {SATS.map((s) => (
              <button key={s} onClick={() => toggle(s)} className={`px-2 py-1 rounded-md border text-xs font-mono ${members.includes(s) ? 'border-cyan-500/60 text-cyan-200 bg-cyan-500/10' : 'border-slate-700 text-slate-400'}`}>{s}</button>
            ))}
          </div>
          <Btn busy={busy === 'run'} disabled={members.length < 2} onClick={go}>Run</Btn>
        </div>
        <p className="text-[11px] text-slate-500">Order of requests: {members.map((m, i) => (mode === 'chain' && i === members.length - 1 ? `${m} (none)` : `${m} → ${members[(i + 1) % members.length]}`)).join(' · ')}</p>
        <ErrorNote error={error} />
      </Panel>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Panel title={result ? `Wait-for graph of the last run (${result.mode})` : 'Wait-for graph (live)'}>
          <WaitForGraph edges={result ? result.wait_for_edges : liveEdges} cycle={det?.cycle || []} victim={result?.victim} />
          <p className="text-[11px] text-slate-500">Arrow A → B: A waits for B. Red = the cycle the probes found.</p>
        </Panel>

        <Panel title="Result">
          {!result ? <div className="text-xs text-slate-400">Run a scenario to see detection and resolution.</div> : (
            <>
              <div className="grid grid-cols-2 gap-3">
                <Stat label="Deadlock" value={result.deadlock_detected ? 'detected' : 'none'} />
                <Stat label="Victim (youngest request)" value={result.victim || '—'} />
                <Stat label="Detection time" value={result.detection_ms != null ? `${result.detection_ms} ms` : '—'} hint="includes the 1 s wait before probing" />
                <Stat label="Probe messages" value={result.probes.messages} hint={`${result.probes.initiated} started · ${result.probes.forwarded} forwarded · ${result.probes.dropped} dropped`} />
              </div>
              <table className="w-full text-xs font-mono">
                <thead className="text-slate-500 text-left"><tr><th className="py-1 pr-3">Satellite</th><th className="pr-3">Wanted</th><th>Outcome</th></tr></thead>
                <tbody className="text-slate-200">
                  {Object.entries(result.outcomes).map(([s, o]) => (
                    <tr key={s} className="border-t border-slate-800"><td className="py-1.5 pr-3">{s}</td><td className="pr-3">{result.requests[s] ? `${result.requests[s]} transponder` : '—'}</td>
                      <td className={o.status === 'COMPLETED' ? 'text-emerald-300' : 'text-rose-300'}>{o.status}</td></tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </Panel>
      </div>

      <Panel title="Knapp's classification of distributed deadlock detection">
        <table className="w-full text-xs">
          <thead className="text-slate-500 text-left"><tr><th className="py-1 pr-3">Class</th><th className="pr-3">Idea</th><th>Example</th></tr></thead>
          <tbody className="text-slate-300">
            <tr className="border-t border-slate-800"><td className="py-1.5 pr-3">Path-pushing</td><td className="pr-3">Sites send parts of the wait-for graph to each other until one sees a cycle</td><td>Obermarck</td></tr>
            <tr className="border-t border-slate-800 bg-cyan-500/5"><td className="py-1.5 pr-3 text-cyan-300">Edge-chasing (used here)</td><td className="pr-3">Probes travel along wait-for edges; a probe returning to its sender means a cycle</td><td>Chandy–Misra–Haas (AND model)</td></tr>
            <tr className="border-t border-slate-800"><td className="py-1.5 pr-3">Diffusing computation</td><td className="pr-3">Queries diffuse through the graph; replies come back if everyone reached is blocked</td><td>Chandy–Misra–Haas (OR model)</td></tr>
            <tr className="border-t border-slate-800"><td className="py-1.5 pr-3">Global state detection</td><td className="pr-3">Take a consistent snapshot and look for a cycle in it</td><td>Bracha–Toueg, Kshemkalyani–Singhal</td></tr>
          </tbody>
        </table>
      </Panel>
    </div>
  );
}
