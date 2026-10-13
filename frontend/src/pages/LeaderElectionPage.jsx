import React, { useState } from 'react';
import { Crown, Radio, Skull, HeartPulse } from 'lucide-react';
import { SATS, api, usePoll, useAction, PageHeader, Panel, Btn, Select, ErrorNote, Stat } from '../lib/fa2';

const stateTone = {
  ALIVE: 'text-emerald-300',
  SUSPECTED: 'text-amber-300',
  DEAD: 'text-rose-300',
  UNKNOWN: 'text-slate-500',
};

export default function LeaderElectionPage() {
  const [algorithm, setAlgorithm] = useState('bully');
  const [initiator, setInitiator] = useState('SAT-01');
  const [crashTarget, setCrashTarget] = useState('SAT-03');
  const [lastRun, setLastRun] = useState(null);
  const [state] = usePoll('/api/fa2/state', 1500);
  const [runs, , reloadRuns] = usePoll('/api/fa2/arena/runs?limit=20', 5000);
  const { busy, error, run } = useAction();

  const sats = state?.satellites || {};
  const leaders = Object.values(sats).filter((s) => !s.unreachable && !s.silent).map((s) => `${s.election?.leader}|${s.election?.term}`);
  const agreed = leaders.length && new Set(leaders).size === 1 ? leaders[0].split('|') : null;
  const electionRuns = (runs?.runs || []).filter((r) => r.kind === 'election' || r.kind === 'leader_failure').reverse();

  const act = async (name, fn) => {
    const res = await run(name, fn);
    if (res && res.kind) setLastRun(res);
    reloadRuns();
  };

  return (
    <div className="space-y-6">
      <PageHeader
        icon={Crown}
        title="Leader Election"
        subtitle="Bully and Ring run between the satellites over their P2P links. Priority = (health in tens, ID), so an unhealthy satellite never leads. When beacons show the leader dead, the survivors elect a new one by themselves."
      />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Agreed leader" value={agreed ? agreed[0] : 'no agreement'} />
        <Stat label="Term" value={agreed ? agreed[1] : '—'} />
        <Stat label="Responsive satellites" value={Object.values(sats).filter((s) => !s.unreachable && !s.silent).length} />
        <Stat label="Default algorithm" value={Object.values(sats).find((s) => s.election)?.election?.default_algorithm || '—'} hint="used for automatic re-election" />
      </div>

      <Panel title="Run an election" icon={Radio}>
        <div className="flex flex-wrap items-end gap-3">
          <Select label="Algorithm" value={algorithm} onChange={setAlgorithm} options={[{ value: 'bully', label: 'Bully' }, { value: 'ring', label: 'Ring' }]} />
          <Select label="Initiator" value={initiator} onChange={setInitiator} options={SATS} />
          <Btn busy={busy === 'run'} onClick={() => act('run', () => api('/api/fa2/election/run', { method: 'POST', body: { algorithm, initiator } }))}>
            Start election
          </Btn>
          <Btn tone="danger" busy={busy === 'failover'} onClick={() => act('failover', () => api('/api/fa2/election/leader-failure', { method: 'POST', body: { algorithm } }))}
            title="Crashes the current leader, waits for the survivors to agree on a new one, then recovers it">
            <span className="inline-flex items-center gap-1"><Skull className="w-3.5 h-3.5" />Crash the leader &amp; measure failover</span>
          </Btn>
        </div>
        <div className="flex flex-wrap items-end gap-3 pt-2 border-t border-slate-800">
          <Select label="Satellite" value={crashTarget} onChange={setCrashTarget} options={SATS} />
          <Btn tone="ghost" busy={busy === 'crash'} onClick={() => run('crash', () => api('/api/fa2/faults/crash', { method: 'POST', body: { target: crashTarget } }))}>Crash (go silent)</Btn>
          <Btn tone="ghost" busy={busy === 'recover'} onClick={() => run('recover', () => api('/api/fa2/faults/recover', { method: 'POST', body: { target: crashTarget } }))}>
            <span className="inline-flex items-center gap-1"><HeartPulse className="w-3.5 h-3.5" />Recover</span>
          </Btn>
          <span className="text-[11px] text-slate-500">A recovered satellite holds a Bully election, as in the textbook algorithm.</span>
        </div>
        <ErrorNote error={error} />
        {lastRun && (
          <div className="text-xs font-mono text-slate-300 bg-slate-900/70 border border-slate-800 rounded-lg p-3 space-y-1">
            <div className="text-cyan-300 font-semibold">{lastRun.kind === 'leader_failure' ? `Failover after crashing ${lastRun.failed_leader}` : `${lastRun.algorithm} election from ${lastRun.initiator}`}: {lastRun.status}</div>
            <div>New leader {lastRun.agreement?.leader ?? '—'} (term {lastRun.agreement?.term ?? '—'}), agreed by {(lastRun.agreement?.agreed_by || []).join(', ')}</div>
            <div>{lastRun.messages} messages: {Object.entries(lastRun.messages_by_type || {}).map(([k, v]) => `${k} ${v}`).join(' · ')}</div>
            {lastRun.kind === 'leader_failure'
              ? <div>Detected by beacons after {lastRun.detection_ms} ms · new leader agreed after {lastRun.time_to_new_leader_ms} ms</div>
              : <div>Agreement observed after {lastRun.agreement_observed_ms} ms (event span {lastRun.event_duration_ms} ms)</div>}
          </div>
        )}
      </Panel>

      <Panel title="What each satellite believes">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          {SATS.map((sid) => {
            const s = sats[sid] || {};
            const el = s.election || {};
            const down = s.unreachable || s.silent;
            return (
              <div key={sid} className={`rounded-xl border p-3 space-y-2 font-mono text-xs ${el.leader === sid && !down ? 'border-cyan-500/60 bg-cyan-500/5' : 'border-slate-800 bg-slate-900/70'}`}>
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-100">{sid}</span>
                  {down ? <span className="text-rose-300 text-[10px]">{s.silent ? 'SILENT' : 'UNREACHABLE'}</span>
                    : el.leader === sid ? <span className="text-cyan-300 text-[10px] inline-flex items-center gap-1"><Crown className="w-3 h-3" />LEADER</span> : null}
                </div>
                {!s.unreachable && (
                  <>
                    <div className="text-slate-400">leader <span className="text-slate-100">{el.leader ?? '—'}</span> · term <span className="text-slate-100">{el.term ?? 0}</span></div>
                    <div className="text-slate-400">priority <span className="text-slate-100">({(el.priority || []).join(', ')})</span></div>
                    {el.running && <div className="text-amber-300">running {el.running_algorithm} election…</div>}
                    <div className="pt-1 border-t border-slate-800 space-y-0.5">
                      {Object.entries(s.peers || {}).sort().map(([pid, p]) => (
                        <div key={pid} className="flex justify-between">
                          <span className="text-slate-500">{pid}</span>
                          <span className={stateTone[p.state] || 'text-slate-400'}>{p.state}{p.silence_s != null ? ` ${p.silence_s}s` : ''}</span>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
            );
          })}
        </div>
        <p className="text-[11px] text-slate-500">Peer states come from satellite-to-satellite beacons every 2 s: SUSPECTED after 3 s of silence, DEAD after 5 s.</p>
      </Panel>

      <Panel title="Recent elections (measured)">
        {electionRuns.length === 0 ? <div className="text-xs text-slate-400">No elections run from this page yet.</div> : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono">
              <thead className="text-slate-500 text-left">
                <tr><th className="py-1 pr-3">Kind</th><th className="pr-3">Algorithm</th><th className="pr-3">Leader</th><th className="pr-3">Messages</th><th className="pr-3">Time to agreement</th><th>Status</th></tr>
              </thead>
              <tbody className="text-slate-200">
                {electionRuns.map((r) => (
                  <tr key={r.run_id} className="border-t border-slate-800">
                    <td className="py-1.5 pr-3">{r.kind === 'leader_failure' ? `failover (${r.failed_leader} crashed)` : `from ${r.initiator}`}</td>
                    <td className="pr-3">{r.algorithm}</td>
                    <td className="pr-3">{r.agreement?.leader ?? '—'}</td>
                    <td className="pr-3">{r.messages}</td>
                    <td className="pr-3">{r.time_to_new_leader_ms ?? r.agreement_observed_ms ?? '—'} ms</td>
                    <td>{r.status}</td>
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
