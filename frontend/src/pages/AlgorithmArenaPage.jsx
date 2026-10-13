import React, { useState } from 'react';
import { Swords, Lock, Crown, ShieldCheck } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell, LabelList } from 'recharts';
import { MUTEX_ALGOS, ALGO_COLORS, api, usePoll, useAction, PageHeader, Panel, Btn, Select, NumberInput, ErrorNote } from '../lib/fa2';

const SHORT = { centralised: 'Central', ricart_agrawala: 'R–A', token_ring: 'Token', lodha_kshemkalyani: 'L–K' };
const nameOf = (id) => MUTEX_ALGOS.find((a) => a.id === id)?.name || id;

function MetricChart({ title, data, dataKey, unit = '', note }) {
  return (
    <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-3">
      <div className="text-xs font-semibold text-slate-200">{title}</div>
      {note && <div className="text-[10px] text-slate-500">{note}</div>}
      <div className="h-48 mt-2">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 16, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="#1e293b" vertical={false} />
            <XAxis dataKey="label" stroke="#94a3b8" fontSize={10} interval={0} />
            <YAxis stroke="#94a3b8" fontSize={10} width={40} />
            <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155', fontSize: 12 }} formatter={(v) => [`${v}${unit}`, title]} />
            <Bar dataKey={dataKey} isAnimationActive={false} radius={[3, 3, 0, 0]}>
              {data.map((d) => <Cell key={d.label} fill={ALGO_COLORS[d.id] || '#38bdf8'} />)}
              <LabelList dataKey={dataKey} position="top" fill="#cbd5e1" fontSize={10} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default function AlgorithmArenaPage() {
  const [algorithm, setAlgorithm] = useState('all');
  const [rounds, setRounds] = useState(3);
  const [holdMs, setHoldMs] = useState(100);
  const [progress, setProgress] = useState('');
  const [summary, , reload] = usePoll('/api/fa2/arena/summary', 4000);
  const [runs, , reloadRuns] = usePoll('/api/fa2/arena/runs?limit=40', 4000);
  const { busy, error, run } = useAction();

  const latest = summary?.latest || {};
  const mutexRows = MUTEX_ALGOS.map((a) => latest[`mutex:${a.id}`]).filter(Boolean).map((r) => ({
    id: r.algorithm, label: SHORT[r.algorithm] || r.algorithm, ...r,
    violations: (r.safety_violations || []).length,
  }));
  const electionRows = ['election:bully', 'election:ring', 'leader_failure:bully', 'leader_failure:ring']
    .map((k) => latest[k]).filter(Boolean).map((r) => ({
      id: r.algorithm,
      label: `${r.algorithm}${r.kind === 'leader_failure' ? ' failover' : ''}`,
      messages: r.messages,
      time: r.time_to_new_leader_ms ?? r.agreement_observed_ms,
    }));

  const runMutex = async () => {
    const algos = algorithm === 'all' ? MUTEX_ALGOS.map((a) => a.id) : [algorithm];
    await run('mutex', async () => {
      for (const a of algos) {
        setProgress(`Running ${nameOf(a)}…`);
        await api('/api/fa2/arena/mutex', { method: 'POST', body: { algorithm: a, rounds: Number(rounds), hold_ms: Number(holdMs) } });
        reload();
      }
      setProgress('');
    });
    setProgress('');
    reloadRuns();
  };

  const runElections = async () => {
    await run('elections', async () => {
      for (const a of ['bully', 'ring']) {
        setProgress(`Running ${a} election…`);
        await api('/api/fa2/election/run', { method: 'POST', body: { algorithm: a, initiator: 'SAT-01' } });
        reload();
      }
      setProgress('');
    });
    setProgress('');
    reloadRuns();
  };

  const runFailover = async (a) => {
    await run(`failover-${a}`, () => api('/api/fa2/election/leader-failure', { method: 'POST', body: { algorithm: a } }));
    reload();
    reloadRuns();
  };

  const history = (runs?.runs || []).slice().reverse();

  return (
    <div className="space-y-6">
      <PageHeader
        icon={Swords}
        title="Algorithm Arena"
        subtitle="Runs the real algorithms on the five satellites under the same load and compares them. Every number below is computed from the events the satellites reported during that run."
      />

      <Panel title="Mutual exclusion: who gets the ground-station downlink?" icon={Lock}>
        <div className="flex flex-wrap items-end gap-3">
          <Select label="Algorithm" value={algorithm} onChange={setAlgorithm}
            options={[{ value: 'all', label: 'All four, one after another' }, ...MUTEX_ALGOS.map((a) => ({ value: a.id, label: a.name }))]} />
          <NumberInput label="Rounds per satellite" value={rounds} onChange={setRounds} width="w-16" />
          <NumberInput label="Hold (ms)" value={holdMs} onChange={setHoldMs} width="w-20" />
          <Btn busy={busy === 'mutex'} onClick={runMutex}>Run with all 5 satellites requesting at once</Btn>
          {progress && <span className="text-xs text-cyan-300">{progress}</span>}
        </div>
        <p className="text-[11px] text-slate-500">Centralised needs an elected leader. Theory for N = 5: {MUTEX_ALGOS.map((a) => `${a.name} ${a.theory}`).join(' · ')}.</p>
        <ErrorNote error={error} />
        {mutexRows.length === 0 ? <div className="text-xs text-slate-400">No mutual-exclusion runs yet.</div> : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <MetricChart title="Messages per critical-section entry" data={mutexRows} dataKey="messages_per_entry" />
              <MetricChart title="Average wait for the downlink" data={mutexRows} dataKey="avg_wait_ms" unit=" ms" />
              <MetricChart title="Fairness inversions" data={mutexRows} dataKey="fairness_inversions" note="an older request was still waiting when a newer one entered" />
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs font-mono">
                <thead className="text-slate-500 text-left">
                  <tr><th className="py-1 pr-3">Algorithm</th><th className="pr-3">Entries</th><th className="pr-3">Messages</th><th className="pr-3">By type</th><th className="pr-3">Max wait</th><th>Safety</th></tr>
                </thead>
                <tbody className="text-slate-200">
                  {mutexRows.map((r) => (
                    <tr key={r.id} className="border-t border-slate-800">
                      <td className="py-1.5 pr-3" style={{ color: ALGO_COLORS[r.id] }}>{nameOf(r.id)}</td>
                      <td className="pr-3">{r.entries}</td>
                      <td className="pr-3">{r.messages}</td>
                      <td className="pr-3 text-slate-400">{Object.entries(r.messages_by_type || {}).map(([k, v]) => `${k} ${v}`).join(' · ')}</td>
                      <td className="pr-3">{r.max_wait_ms} ms</td>
                      <td className={r.violations ? 'text-rose-300' : 'text-emerald-300'}>
                        <span className="inline-flex items-center gap-1"><ShieldCheck className="w-3.5 h-3.5" />{r.violations ? `${r.violations} overlap(s)` : 'never two in CS'}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </Panel>

      <Panel title="Leader election: Bully vs Ring" icon={Crown}>
        <div className="flex flex-wrap items-end gap-3">
          <Btn busy={busy === 'elections'} onClick={runElections}>Run Bully and Ring from SAT-01</Btn>
          <Btn tone="danger" busy={busy === 'failover-bully'} onClick={() => runFailover('bully')}>Crash leader, Bully re-elects</Btn>
          <Btn tone="danger" busy={busy === 'failover-ring'} onClick={() => runFailover('ring')}>Crash leader, Ring re-elects</Btn>
        </div>
        <p className="text-[11px] text-slate-500">Failover time includes beacon detection (leader declared dead after 5 s of silence), so it is dominated by the detector, not the election.</p>
        {electionRows.length === 0 ? <div className="text-xs text-slate-400">No election runs yet.</div> : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <MetricChart title="Messages to elect a leader" data={electionRows} dataKey="messages" />
            <MetricChart title="Time until all satellites agree" data={electionRows} dataKey="time" unit=" ms" />
          </div>
        )}
      </Panel>

      <Panel title="Run history">
        {history.length === 0 ? <div className="text-xs text-slate-400">Nothing run yet.</div> : (
          <div className="overflow-x-auto max-h-80">
            <table className="w-full text-xs font-mono">
              <thead className="text-slate-500 text-left sticky top-0 bg-slate-950">
                <tr><th className="py-1 pr-3">Time</th><th className="pr-3">Kind</th><th className="pr-3">Algorithm</th><th className="pr-3">Result</th><th>Run ID</th></tr>
              </thead>
              <tbody className="text-slate-200">
                {history.map((r) => (
                  <tr key={r.run_id} className="border-t border-slate-800">
                    <td className="py-1.5 pr-3">{new Date(r.started_at * 1000).toLocaleTimeString()}</td>
                    <td className="pr-3">{r.kind}</td>
                    <td className="pr-3">{r.algorithm}</td>
                    <td className="pr-3">{r.kind === 'mutex'
                      ? `${r.entries} entries, ${r.messages_per_entry} msgs/entry, ${(r.safety_violations || []).length} overlaps`
                      : `leader ${r.agreement?.leader ?? '—'}, ${r.messages} msgs, ${r.time_to_new_leader_ms ?? r.agreement_observed_ms ?? '—'} ms`}</td>
                    <td className="text-slate-500">{r.run_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}
