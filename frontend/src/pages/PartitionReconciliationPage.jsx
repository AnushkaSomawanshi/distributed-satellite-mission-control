import React, { useState } from 'react';
import { Scale, Link2, Unlink, ShieldCheck, ShieldAlert, PenLine } from 'lucide-react';
import { SATS, api, usePoll, useAction, PageHeader, Panel, Btn, Select, NumberInput, ErrorNote, Stat, fmtVector } from '../lib/fa2';

const ACTIONS = ['SCHEDULE_DOWNLINK', 'SET_POWER_MODE', 'POINT_PAYLOAD', 'RESET_FAULTS', 'SET_TASK_PRIORITY'];

export default function PartitionReconciliationPage() {
  const [cap] = usePoll('/api/fa2/cap/status', 1500);
  const [ledger, , reloadLedger] = usePoll('/api/fa2/ledger', 2500);
  const [board, , reloadBoard] = usePoll('/api/fa2/board', 1500);
  const [via, setVia] = useState('SAT-05');
  const [action, setAction] = useState('SCHEDULE_DOWNLINK');
  const [target, setTarget] = useState('SAT-02');
  const [param, setParam] = useState('12:00 UTC via Pune');
  const [lastCommit, setLastCommit] = useState(null);
  const [bVia, setBVia] = useState('SAT-01');
  const [bKey, setBKey] = useState('downlink_window');
  const [bVal, setBVal] = useState('12:00 via Pune');
  const [tamperSat, setTamperSat] = useState('SAT-02');
  const [tamperIdx, setTamperIdx] = useState(0);
  const { busy, error, run } = useAction();

  const partition = cap?.partition;
  const leaders = cap?.leaders || {};
  const sideLeaders = [...new Set(Object.values(leaders).filter(Boolean))];

  const submit = () => run('submit', async () => {
    const params = action === 'SET_POWER_MODE' ? { mode: param } : action === 'POINT_PAYLOAD' ? { target: param } : { note: param };
    try {
      setLastCommit(await api('/api/fa2/ledger/submit', { method: 'POST', body: { via, action, target, params } }));
    } finally { reloadLedger(); }
  });

  const boardKeys = new Set();
  Object.values(board?.satellites || {}).forEach((s) => Object.keys(s.keys || {}).forEach((k) => boardKeys.add(k)));

  return (
    <div className="space-y-6">
      <PageHeader
        icon={Scale}
        title="CAP trade-off: ledger (CP) vs status board (AP)"
        subtitle="Cut the constellation in two. The command ledger needs signatures from 3 of 5 satellites, so the 2-satellite side refuses writes (consistency). The status board accepts writes on both sides (availability); after healing, vector clocks expose the concurrent writes as a conflict to resolve."
      >
        <Btn tone="danger" disabled={!!partition} busy={busy === 'part'} onClick={() => run('part', () => api('/api/fa2/faults/partition', { method: 'POST', body: { groups: [['SAT-01', 'SAT-02', 'SAT-03'], ['SAT-04', 'SAT-05']] } }))}>
          <span className="inline-flex items-center gap-1"><Unlink className="w-3.5 h-3.5" />Partition {'{01,02,03} | {04,05}'}</span>
        </Btn>
        <Btn tone="ghost" disabled={!partition} busy={busy === 'heal'} onClick={() => run('heal', async () => { await api('/api/fa2/faults/heal', { method: 'POST' }); reloadBoard(); reloadLedger(); })}>
          <span className="inline-flex items-center gap-1"><Link2 className="w-3.5 h-3.5" />Heal</span>
        </Btn>
      </PageHeader>
      <ErrorNote error={error} />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Network" value={partition ? 'PARTITIONED' : 'connected'} hint={partition ? partition.map((g) => `{${g.join(',')}}`).join(' | ') : ''} />
        <Stat label="Leaders" value={sideLeaders.join(' & ') || '—'} hint={sideLeaders.length > 1 ? 'one per side: Bully ran on each side' : ''} />
        <Stat label="Ledger heights" value={Object.values(cap?.ledger_heights || {}).join(' · ')} hint="SAT-01 … SAT-05" />
        <Stat label="Board conflicts" value={Object.values(cap?.board_conflicts || {}).reduce((a, b) => a + (b || 0), 0)} hint="keys with concurrent versions" />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Panel title="CP — signed command ledger (blockchain, proof of authority)" icon={ShieldCheck}>
          <div className="flex flex-wrap items-end gap-2">
            <Select label="Submit via leader" value={via} onChange={setVia} options={SATS.map((s) => ({ value: s, label: `${s}${leaders[s] === s ? ' (leader)' : ''}` }))} />
            <Select label="Command" value={action} onChange={setAction} options={ACTIONS} />
            <Select label="Target" value={target} onChange={setTarget} options={SATS} />
            <label className="text-[11px] text-slate-400 flex items-center gap-1.5">Param
              <input value={param} onChange={(e) => setParam(e.target.value)} className="w-40 bg-slate-900 border border-slate-700 rounded-md px-2 py-1.5 text-xs text-slate-200" />
            </label>
            <Btn busy={busy === 'submit'} onClick={submit}>Propose block</Btn>
          </div>
          {lastCommit && (
            <div className={`text-xs font-mono rounded-lg border p-2 ${lastCommit.status === 'COMMITTED' ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200' : 'border-rose-500/40 bg-rose-500/10 text-rose-200'}`}>
              {lastCommit.status} via {lastCommit.submitted_via}: {lastCommit.signatures}/{lastCommit.quorum} signatures needed {lastCommit.quorum} · votes {Object.entries(lastCommit.votes || {}).map(([k, v]) => `${k}:${v}`).join(' ')}
            </div>
          )}
          <table className="w-full text-xs font-mono">
            <thead className="text-slate-500 text-left"><tr><th className="py-1 pr-3">Copy on</th><th className="pr-3">Height</th><th className="pr-3">Tip</th><th className="pr-3">Verified by Mission Control</th><th>Majority</th></tr></thead>
            <tbody className="text-slate-200">
              {SATS.map((s) => {
                const c = ledger?.copies?.[s] || {};
                return (
                  <tr key={s} className="border-t border-slate-800">
                    <td className="py-1.5 pr-3">{s}</td>
                    <td className="pr-3">{c.height ?? '—'}</td>
                    <td className="pr-3 text-slate-400">{c.tip ? c.tip.slice(0, 10) : '—'}</td>
                    <td className={`pr-3 ${c.verification?.valid ? 'text-emerald-300' : 'text-rose-300'}`}>{c.reachable === false ? 'unreachable' : c.verification?.valid ? 'valid' : `INVALID at block ${c.verification?.bad_index}: ${c.verification?.reason}`}</td>
                    <td>{c.agrees_with_majority ? 'yes' : c.reachable ? 'no' : ''}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div className="flex flex-wrap items-end gap-2 pt-2 border-t border-slate-800">
            <ShieldAlert className="w-4 h-4 text-rose-300" />
            <Select label="Tamper with copy on" value={tamperSat} onChange={setTamperSat} options={SATS} />
            <NumberInput label="block" value={tamperIdx} onChange={setTamperIdx} width="w-16" />
            <Btn tone="ghost" busy={busy === 'tamper'} onClick={() => run('tamper', async () => { await api('/api/fa2/ledger/tamper', { method: 'POST', body: { target: tamperSat, index: Number(tamperIdx) } }); reloadLedger(); })}>Edit block in place</Btn>
            <Btn tone="ghost" busy={busy === 'repair'} onClick={() => run('repair', async () => { await api('/api/fa2/ledger/repair', { method: 'POST', body: { target: tamperSat } }); reloadLedger(); })}>Repair from peers</Btn>
          </div>
          <div className="max-h-56 overflow-y-auto space-y-1">
            {(ledger?.blocks || []).map((b) => (
              <div key={b.hash} className="text-[11px] font-mono bg-slate-900/70 border border-slate-800 rounded-lg px-2 py-1">
                <span className="text-cyan-300">#{b.index}</span> {b.commands.map((c) => `${c.action} → ${c.target} ${JSON.stringify(c.params)}`).join('; ')}
                <div className="text-slate-500">hash {b.hash.slice(0, 12)} · prev {b.prev_hash.slice(0, 12)} · term {b.term} by {b.proposer} · signed by {b.signers.join(', ')}</div>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="AP — replicated status board (vector clocks)" icon={PenLine}>
          <div className="flex flex-wrap items-end gap-2">
            <Select label="Write on" value={bVia} onChange={setBVia} options={SATS} />
            <label className="text-[11px] text-slate-400 flex items-center gap-1.5">Key
              <input value={bKey} onChange={(e) => setBKey(e.target.value)} className="w-32 bg-slate-900 border border-slate-700 rounded-md px-2 py-1.5 text-xs text-slate-200" />
            </label>
            <label className="text-[11px] text-slate-400 flex items-center gap-1.5">Value
              <input value={bVal} onChange={(e) => setBVal(e.target.value)} className="w-40 bg-slate-900 border border-slate-700 rounded-md px-2 py-1.5 text-xs text-slate-200" />
            </label>
            <Btn busy={busy === 'put'} onClick={() => run('put', async () => { await api('/api/fa2/board/put', { method: 'POST', body: { via: bVia, key: bKey, value: bVal } }); reloadBoard(); })}>Write</Btn>
          </div>
          <p className="text-[11px] text-slate-500">Try: partition, write the same key on SAT-01 and on SAT-04 with different values, then heal.</p>
          {[...boardKeys].sort().map((k) => (
            <div key={k} className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-200 font-mono">{k}</span>
                <div className="flex gap-1">
                  <Btn tone="ghost" busy={busy === `lww-${k}`} onClick={() => run(`lww-${k}`, () => api('/api/fa2/board/resolve', { method: 'POST', body: { via: bVia, key: k, strategy: 'lww' } }))}>Resolve: last writer wins</Btn>
                  <Btn tone="ghost" busy={busy === `merge-${k}`} onClick={() => run(`merge-${k}`, () => api('/api/fa2/board/resolve', { method: 'POST', body: { via: bVia, key: k, strategy: 'merge' } }))}>Resolve: merge</Btn>
                </div>
              </div>
              <table className="w-full text-[11px] font-mono">
                <tbody className="text-slate-300">
                  {SATS.map((s) => {
                    const versions = board?.satellites?.[s]?.keys?.[k] || [];
                    const conflict = versions.length > 1;
                    return (
                      <tr key={s} className={`border-t border-slate-800 ${conflict ? 'bg-amber-500/10' : ''}`}>
                        <td className="py-1 pr-3 w-16">{s}</td>
                        <td>{versions.length === 0 ? <span className="text-slate-600">—</span> : versions.map((v, i) => (
                          <span key={i} className={`mr-3 ${conflict ? 'text-amber-200' : ''}`}>"{String(v.value)}" <span className="text-slate-500">by {v.writer} {fmtVector(v.vclock)}</span></span>
                        ))}{conflict && <span className="text-amber-300 font-semibold">CONFLICT (concurrent)</span>}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ))}
          {boardKeys.size === 0 && <div className="text-xs text-slate-400">The board is empty. Write a key.</div>}
        </Panel>
      </div>
    </div>
  );
}
