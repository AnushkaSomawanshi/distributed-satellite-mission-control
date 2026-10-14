import React, { useState } from 'react';
import { Camera, Shuffle, CheckCircle2, XCircle } from 'lucide-react';
import { SATS, api, usePoll, useAction, PageHeader, Panel, Btn, Select, ErrorNote, Stat } from '../lib/fa2';

export default function GlobalSnapshotPage() {
  const [initiator, setInitiator] = useState('');
  const [snap, setSnap] = useState(null);
  const [tasks, , reloadTasks] = usePoll('/api/fa2/tasks', 3000);
  const [history, , reloadHistory] = usePoll('/api/fa2/snapshots', 5000);
  const { busy, error, run } = useAction();

  const take = async () => {
    const res = await run('snap', () => api('/api/fa2/snapshot', { method: 'POST', body: initiator ? { initiator } : {} }));
    if (res) setSnap(res);
    reloadHistory();
  };

  const c = snap?.consistency;
  return (
    <div className="space-y-6">
      <PageHeader
        icon={Camera}
        title="Global Snapshot (Chandy–Lamport)"
        subtitle="The initiator records its state and sends a MARKER on every channel; each satellite records its state on its first marker and records the messages that arrive on each channel until that channel's marker arrives. Channels are FIFO. Turn on task handoff traffic to catch tasks in transit."
      >
        <Btn tone={tasks?.traffic ? 'danger' : 'ghost'} busy={busy === 'traffic'}
          onClick={() => run('traffic', async () => { await api('/api/fa2/tasks/traffic', { method: 'POST', body: { enabled: !tasks?.traffic } }); reloadTasks(); })}>
          <span className="inline-flex items-center gap-1"><Shuffle className="w-3.5 h-3.5" />{tasks?.traffic ? 'Stop handoff traffic' : 'Start handoff traffic'}</span>
        </Btn>
        <Select label="Initiator" value={initiator} onChange={setInitiator} options={[{ value: '', label: 'leader' }, ...SATS]} />
        <Btn busy={busy === 'snap'} onClick={take}>Take snapshot</Btn>
      </PageHeader>
      <ErrorNote error={error} />

      {snap && (
        <>
          <div className={`rounded-xl border px-4 py-3 text-sm flex items-center gap-2 ${c.holds ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200' : 'border-rose-500/40 bg-rose-500/10 text-rose-200'}`}>
            {c.holds ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
            <span><b>{c.holds ? 'Consistent.' : 'Not consistent.'}</b> {c.invariant}. {c.missing.length ? `Missing: ${c.missing.join(', ')}. ` : ''}{c.duplicated.length ? `Duplicated: ${c.duplicated.join(', ')}.` : ''}</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Stat label="Initiator" value={snap.initiator} />
            <Stat label="Satellites recorded" value={c.pieces} hint={snap.missing_pieces_from?.length ? `no piece from ${snap.missing_pieces_from.join(', ')}` : 'all responded'} />
            <Stat label="Markers sent" value={snap.markers_sent} hint="N × (N−1) for N live satellites" />
            <Stat label="Tasks caught in transit" value={snap.tasks_in_transit.length} />
          </div>

          <Panel title="Recorded local states">
            <div className="overflow-x-auto">
              <table className="w-full text-xs font-mono">
                <thead className="text-slate-500 text-left"><tr><th className="py-1 pr-3">Satellite</th><th className="pr-3">Tasks held</th><th className="pr-3">Lamport</th><th className="pr-3">Leader / term</th><th className="pr-3">Clock skew</th><th>In CS</th></tr></thead>
                <tbody className="text-slate-200">
                  {Object.entries(snap.satellites).sort().map(([sid, s]) => (
                    <tr key={sid} className="border-t border-slate-800">
                      <td className="py-1.5 pr-3">{sid}</td>
                      <td className="pr-3">{s.tasks.map((t) => `${t.task_id} v${t.version}`).join(', ') || '—'}</td>
                      <td className="pr-3">{s.lamport}</td>
                      <td className="pr-3">{s.leader} / {s.term}</td>
                      <td className="pr-3">{s.clock_skew_ms} ms</td>
                      <td>{s.in_critical_section ? 'yes' : 'no'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>

          <Panel title="Channel states (messages in transit at snapshot time)">
            {snap.tasks_in_transit.length === 0 && <div className="text-xs text-slate-400">No task was in transit. Start handoff traffic and take another snapshot.</div>}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
              {Object.entries(snap.channel_states).filter(([, msgs]) => msgs.length).map(([ch, msgs]) => (
                <div key={ch} className="rounded-lg border border-sky-500/40 bg-sky-500/5 p-2 font-mono text-xs">
                  <div className="text-sky-300 font-semibold">{ch}</div>
                  {msgs.map((m, i) => <div key={i} className="text-slate-300">{m.msg_type} {m.task_id || ''}</div>)}
                </div>
              ))}
            </div>
            <p className="text-[11px] text-slate-500">{Object.keys(snap.channel_states).length} channels recorded; empty channels are not shown.</p>
          </Panel>
        </>
      )}

      <Panel title="Snapshot history">
        {(history?.snapshots || []).length === 0 ? <div className="text-xs text-slate-400">No snapshots yet.</div> : (
          <table className="w-full text-xs font-mono">
            <thead className="text-slate-500 text-left"><tr><th className="py-1 pr-3">Time</th><th className="pr-3">Initiator</th><th className="pr-3">Consistent</th><th className="pr-3">In transit</th><th>ID</th></tr></thead>
            <tbody className="text-slate-200">
              {history.snapshots.slice().reverse().map((s) => (
                <tr key={s.snapshot_id} className="border-t border-slate-800 cursor-pointer hover:bg-slate-900/50" onClick={() => setSnap(s)}>
                  <td className="py-1.5 pr-3">{new Date(s.taken_at * 1000).toLocaleTimeString()}</td>
                  <td className="pr-3">{s.initiator}</td>
                  <td className={`pr-3 ${s.consistency.holds ? 'text-emerald-300' : 'text-rose-300'}`}>{s.consistency.holds ? 'yes' : 'no'}</td>
                  <td className="pr-3">{s.tasks_in_transit.map((t) => `${t.task_id} (${t.channel})`).join(', ') || '—'}</td>
                  <td className="text-slate-500">{s.snapshot_id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </div>
  );
}
