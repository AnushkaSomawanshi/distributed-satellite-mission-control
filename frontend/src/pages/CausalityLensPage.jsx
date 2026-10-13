import React, { useMemo, useState } from 'react';
import { GitBranch, Shuffle, Clock3, RotateCcw, Eraser } from 'lucide-react';
import {
  SATS, api, usePoll, useAction, PageHeader, Panel, Btn, Select, NumberInput, ErrorNote, Stat,
  compareVectors, fmtVector,
} from '../lib/fa2';

const ORDERINGS = [
  { value: 'phys_ts', label: 'Physical time (each satellite’s own clock)' },
  { value: 'true_ts', label: 'True time (shared host clock, ground truth)' },
  { value: 'lamport', label: 'Lamport timestamp' },
  { value: 'vector', label: 'Vector clock (causal depth)' },
];

const FILTERS = [
  { value: 'all', label: 'All algorithms' },
  { value: 'lens', label: 'Cross-links only' },
  { value: 'bully,ring', label: 'Elections' },
  { value: 'ricart_agrawala,lodha_kshemkalyani,centralised,token_ring', label: 'Mutual exclusion' },
  { value: 'berkeley,cristian', label: 'Clock sync' },
];

const W = 1000;
const LEFT = 96;
const RIGHT = 980;
const LANE = 74;
const TOP = 36;

const keyOf = (e, ordering) => {
  if (ordering === 'vector') return Object.values(e.vector || {}).reduce((a, b) => a + b, 0);
  return e[ordering] ?? 0;
};

function relationText(rel, a, b) {
  const an = `${a.node} #${a.seq}`;
  const bn = `${b.node} #${b.seq}`;
  if (rel === 'BEFORE') return `${an} → ${bn}: happened-before (b knows about a)`;
  if (rel === 'AFTER') return `${bn} → ${an}: happened-before (a knows about b)`;
  if (rel === 'EQUAL') return 'Same event';
  return `${an} ∥ ${bn}: concurrent — neither could have influenced the other`;
}

export default function CausalityLensPage() {
  const [ordering, setOrdering] = useState('phys_ts');
  const [filter, setFilter] = useState('lens');
  const [windowSize, setWindowSize] = useState(60);
  const [clearedAt, setClearedAt] = useState(0);
  const [selected, setSelected] = useState([]);
  const [driftTarget, setDriftTarget] = useState('SAT-02');
  const [driftMs, setDriftMs] = useState(-800);
  const [events] = usePoll('/api/fa2/events?limit=1500', 1500);
  const { busy, error, run } = useAction();

  const shown = useMemo(() => {
    const all = (events?.events || []).filter((e) => ['SEND', 'RECV', 'LOCAL'].includes(e.kind) && e.true_ts > clearedAt);
    const filtered = all.filter((e) => {
      if (filter === 'all') return e.algo !== 'beacon' || e.kind === 'LOCAL';
      return filter.split(',').includes(e.algo);
    });
    return filtered.slice(-Number(windowSize || 60));
  }, [events, filter, windowSize, clearedAt]);

  const layout = useMemo(() => {
    if (!shown.length) return { points: [], lines: [], backwards: 0, failed: 0 };
    const keys = shown.map((e) => keyOf(e, ordering));
    let xOf;
    if (ordering === 'lamport' || ordering === 'vector') {
      const distinct = [...new Set(keys)].sort((a, b) => a - b);
      const rank = new Map(distinct.map((v, i) => [v, i]));
      const n = Math.max(1, distinct.length - 1);
      xOf = (e) => LEFT + 20 + (rank.get(keyOf(e, ordering)) / n) * (RIGHT - LEFT - 40);
    } else {
      const lo = Math.min(...keys);
      const hi = Math.max(...keys);
      const span = hi - lo || 1;
      xOf = (e) => LEFT + 20 + ((keyOf(e, ordering) - lo) / span) * (RIGHT - LEFT - 40);
    }
    const yOf = (e) => TOP + SATS.indexOf(e.node) * LANE + 20;
    const points = shown.map((e) => ({ e, x: xOf(e), y: yOf(e) }));
    const byMsg = {};
    points.forEach((p) => {
      if (p.e.msg_id) {
        byMsg[p.e.msg_id] = byMsg[p.e.msg_id] || {};
        byMsg[p.e.msg_id][p.e.kind] = p;
      }
    });
    const lines = [];
    let backwards = 0;
    Object.values(byMsg).forEach((m) => {
      if (m.SEND && m.RECV) {
        const back = m.RECV.x < m.SEND.x - 0.5;
        if (back) backwards += 1;
        lines.push({ from: m.SEND, to: m.RECV, back });
      }
    });
    const failed = points.filter((p) => p.e.kind === 'SEND' && p.e.delivered === false).length;
    return { points, lines, backwards, failed };
  }, [shown, ordering]);

  const toggle = (e) => {
    setSelected((prev) => {
      if (prev.find((x) => x.event_id === e.event_id)) return prev.filter((x) => x.event_id !== e.event_id);
      return [...prev, e].slice(-2);
    });
  };

  const relation = selected.length === 2 ? compareVectors(selected[0].vector, selected[1].vector) : null;
  const height = TOP + SATS.length * LANE + 10;

  return (
    <div className="space-y-6">
      <PageHeader
        icon={GitBranch}
        title="Causality Lens"
        subtitle="Real messages between the five satellite processes, drawn as a space-time diagram. Switch the ordering to see how physical clocks can put a receive before its send, while Lamport and vector clocks never do."
      />

      <Panel title="Controls" icon={Clock3}>
        <div className="flex flex-wrap items-end gap-3">
          <Select label="Order by" value={ordering} onChange={setOrdering} options={ORDERINGS} />
          <Select label="Show" value={filter} onChange={setFilter} options={FILTERS} />
          <NumberInput label="Last" value={windowSize} onChange={setWindowSize} width="w-16" />
          <span className="text-[11px] text-slate-500">events</span>
          <Btn tone="ghost" onClick={() => { setClearedAt(Date.now() / 1000); setSelected([]); }}>
            <span className="inline-flex items-center gap-1"><Eraser className="w-3.5 h-3.5" />Clear view</span>
          </Btn>
        </div>
        <div className="flex flex-wrap items-end gap-3 pt-2 border-t border-slate-800">
          <Btn busy={busy === 'traffic'} onClick={() => run('traffic', () => api('/api/fa2/lens/traffic', { method: 'POST', body: { messages: 10 } }))}>
            <span className="inline-flex items-center gap-1"><Shuffle className="w-3.5 h-3.5" />Send 10 cross-links</span>
          </Btn>
          <Select value={driftTarget} onChange={setDriftTarget} options={SATS} label="Drift" />
          <NumberInput value={driftMs} onChange={setDriftMs} label="jump (ms)" width="w-24" />
          <Btn tone="ghost" busy={busy === 'drift'} onClick={() => run('drift', () => api('/api/fa2/faults/clock-drift', { method: 'POST', body: { target: driftTarget, offset_ms: Number(driftMs) } }))}>
            Inject CLOCK_DRIFT
          </Btn>
          <Btn tone="ghost" busy={busy === 'reset'} onClick={() => run('reset', () => api('/api/fa2/faults/clock-reset', { method: 'POST', body: {} }))}>
            <span className="inline-flex items-center gap-1"><RotateCcw className="w-3.5 h-3.5" />Reset all clocks</span>
          </Btn>
        </div>
        <ErrorNote error={error} />
      </Panel>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Events shown" value={shown.length} />
        <Stat label="Messages drawn" value={layout.lines.length} />
        <Stat label="Drawn backwards" value={layout.backwards} hint={ordering === 'phys_ts' ? 'receive before its send on this clock' : 'impossible for logical clocks'} />
        <Stat label="Failed sends" value={layout.failed} hint="partition or crashed peer" />
      </div>

      <Panel title="Space-time diagram" right={<span className="text-[11px] text-slate-500">Click two events to compare their vector clocks</span>}>
        {shown.length === 0 ? (
          <div className="text-xs text-slate-400 py-10 text-center">No events yet. Send some cross-links or run an algorithm.</div>
        ) : (
          <svg viewBox={`0 0 ${W} ${height}`} className="w-full" role="img" aria-label="Space-time diagram of satellite messages">
            <defs>
              <marker id="lens-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M0 0L10 5L0 10z" fill="#64748b" />
              </marker>
              <marker id="lens-arrow-back" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M0 0L10 5L0 10z" fill="#f43f5e" />
              </marker>
            </defs>
            {SATS.map((s, i) => (
              <g key={s}>
                <line x1={LEFT} x2={RIGHT} y1={TOP + i * LANE + 20} y2={TOP + i * LANE + 20} stroke="#1e293b" strokeWidth="2" />
                <text x={12} y={TOP + i * LANE + 24} fill="#94a3b8" fontSize="13" fontFamily="JetBrains Mono, monospace">{s}</text>
              </g>
            ))}
            <text x={RIGHT} y={18} textAnchor="end" fill="#64748b" fontSize="11">{ORDERINGS.find((o) => o.value === ordering).label} →</text>
            {layout.lines.map((l, i) => (
              <line key={i} x1={l.from.x} y1={l.from.y} x2={l.to.x} y2={l.to.y}
                stroke={l.back ? '#f43f5e' : '#475569'} strokeWidth={l.back ? 2 : 1.25}
                markerEnd={`url(#${l.back ? 'lens-arrow-back' : 'lens-arrow'})`} />
            ))}
            {layout.points.map(({ e, x, y }) => {
              const isSel = selected.find((s) => s.event_id === e.event_id);
              const fill = e.kind === 'LOCAL' ? '#f59e0b' : e.kind === 'SEND' ? (e.delivered === false ? '#f43f5e' : '#38bdf8') : '#34d399';
              return (
                <g key={e.event_id} onClick={() => toggle(e)} style={{ cursor: 'pointer' }}>
                  {e.kind === 'LOCAL'
                    ? <rect x={x - 5} y={y - 5} width="10" height="10" transform={`rotate(45 ${x} ${y})`} fill={fill} />
                    : <circle cx={x} cy={y} r="5" fill={fill} />}
                  {isSel && <circle cx={x} cy={y} r="10" fill="none" stroke="#e2e8f0" strokeWidth="1.5" />}
                  <title>{`${e.node} ${e.kind} ${e.msg_type || e.label || ''} L=${e.lamport} V=${fmtVector(e.vector)}`}</title>
                </g>
              );
            })}
          </svg>
        )}
        <div className="flex flex-wrap gap-4 text-[11px] text-slate-400">
          <span><span className="inline-block w-2.5 h-2.5 rounded-full bg-sky-400 mr-1" />send</span>
          <span><span className="inline-block w-2.5 h-2.5 rounded-full bg-emerald-400 mr-1" />receive</span>
          <span><span className="inline-block w-2.5 h-2.5 rotate-45 bg-amber-400 mr-1" />local event</span>
          <span><span className="inline-block w-2.5 h-2.5 rounded-full bg-rose-500 mr-1" />failed send</span>
          <span><span className="inline-block w-4 h-0.5 bg-rose-500 mr-1 align-middle" />message drawn backwards</span>
        </div>
      </Panel>

      {selected.length > 0 && (
        <Panel title="Selected events">
          {relation && (
            <div className={`text-xs font-semibold rounded-lg px-3 py-2 border ${relation === 'CONCURRENT' ? 'text-amber-200 border-amber-500/40 bg-amber-500/10' : 'text-emerald-200 border-emerald-500/40 bg-emerald-500/10'}`}>
              {relationText(relation, selected[0], selected[1])}
            </div>
          )}
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono">
              <thead className="text-slate-500 text-left">
                <tr><th className="py-1 pr-3">Satellite</th><th className="pr-3">Event</th><th className="pr-3">Lamport</th><th className="pr-3">Vector</th><th className="pr-3">Own clock</th><th>Skew vs true</th></tr>
              </thead>
              <tbody className="text-slate-200">
                {selected.map((e) => (
                  <tr key={e.event_id} className="border-t border-slate-800">
                    <td className="py-1.5 pr-3">{e.node} #{e.seq}</td>
                    <td className="pr-3">{e.kind} {e.msg_type || e.label} {e.peer ? (e.kind === 'SEND' ? `→ ${e.peer}` : `← ${e.peer}`) : ''}</td>
                    <td className="pr-3">{e.lamport}</td>
                    <td className="pr-3">{fmtVector(e.vector)}</td>
                    <td className="pr-3">{new Date(e.phys_ts * 1000).toISOString().slice(11, 23)}</td>
                    <td>{((e.phys_ts - e.true_ts) * 1000).toFixed(1)} ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}
    </div>
  );
}
