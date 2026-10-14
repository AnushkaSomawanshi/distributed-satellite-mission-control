import React, { useState } from 'react';
import { Target, Cpu, Shuffle, ArrowRight } from 'lucide-react';
import { SATS, api, usePoll, useAction, PageHeader, Panel, Btn, Select, ErrorNote, Stat } from '../lib/fa2';

const statusTone = {
  RUNNING: 'text-emerald-300',
  OWNER_SILENT: 'text-amber-300',
  IN_TRANSIT_OR_UNASSIGNED: 'text-sky-300',
  DUPLICATE_PENDING_FENCING: 'text-rose-300',
};

export default function MissionTasksPage() {
  const [data, , reload] = usePoll('/api/fa2/tasks', 2000);
  const [target, setTarget] = useState({});
  const { busy, error, run } = useAction();
  const tasks = data?.tasks || [];
  const caps = data?.capabilities_map || {};

  const assign = (taskId) => run(`assign-${taskId}`, async () => {
    await api(`/api/tasks/${taskId}/reassign`, { method: 'POST', body: { new_owner: target[taskId] || 'SAT-01' } });
    reload();
  });

  return (
    <div className="space-y-6">
      <PageHeader
        icon={Target}
        title="Mission Tasks"
        subtitle="Tasks are owned by the satellites. When an owner is declared dead, the elected leader moves its tasks to the best capable satellite (version + 1); a satellite that returns with an old copy is told to drop it."
      >
        <Btn tone={data?.traffic ? 'danger' : 'ghost'} busy={busy === 'traffic'}
          onClick={() => run('traffic', () => api('/api/fa2/tasks/traffic', { method: 'POST', body: { enabled: !data?.traffic } }))}>
          <span className="inline-flex items-center gap-1"><Shuffle className="w-3.5 h-3.5" />{data?.traffic ? 'Stop handoff traffic' : 'Start handoff traffic'}</span>
        </Btn>
      </PageHeader>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Leader (decides reassignment)" value={data?.leader || '—'} />
        <Stat label="Tasks running" value={tasks.filter((t) => t.status === 'RUNNING').length} hint={`of ${tasks.length}`} />
        <Stat label="Handoff traffic" value={data?.traffic ? 'ON' : 'OFF'} hint="tasks follow the satellites' footprints" />
        <Stat label="Source" value={data?.source || '—'} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
        {SATS.map((s) => (
          <div key={s} className="glass-panel p-3 rounded-xl border border-slate-800/80 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-orbitron font-bold text-cyan-300 text-sm">{s}</span>
              <Cpu className="w-4 h-4 text-slate-500" />
            </div>
            <div className="flex flex-wrap gap-1">
              {(caps[s] || []).map((c) => <span key={c} className="px-2 py-0.5 bg-slate-900 text-slate-300 border border-slate-700/60 rounded text-[10px] font-mono">{c}</span>)}
            </div>
            <div className="text-[11px] text-slate-400 font-mono">
              owns {tasks.filter((t) => t.current_owner === s).map((t) => t.task_id).join(', ') || 'nothing'}
            </div>
          </div>
        ))}
      </div>

      <Panel title="Tasks">
        <ErrorNote error={error} />
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="text-slate-500 text-left">
              <tr><th className="py-1 pr-3">Task</th><th className="pr-3">Type</th><th className="pr-3">Priority</th><th className="pr-3">Needs</th><th className="pr-3">Owner</th><th className="pr-3">Version</th><th className="pr-3">Status</th><th>Move to (via leader)</th></tr>
            </thead>
            <tbody className="text-slate-200">
              {tasks.map((t) => (
                <tr key={t.task_id} className="border-t border-slate-800 align-top">
                  <td className="py-2 pr-3 font-mono text-cyan-300">{t.task_id}</td>
                  <td className="pr-3">{t.task_type}<div className="text-[10px] text-slate-500 max-w-xs">{t.description}</div></td>
                  <td className="pr-3">{t.priority}</td>
                  <td className="pr-3 font-mono text-[10px]">{(t.required_capabilities || []).join(' + ')}</td>
                  <td className="pr-3 font-mono">{t.current_owner || '—'}</td>
                  <td className="pr-3 font-mono">v{t.version ?? '—'}</td>
                  <td className={`pr-3 font-mono text-[11px] ${statusTone[t.status] || ''}`}>{t.status}</td>
                  <td>
                    <div className="flex items-center gap-2">
                      <Select value={target[t.task_id] || 'SAT-01'} onChange={(v) => setTarget({ ...target, [t.task_id]: v })} options={SATS} />
                      <Btn tone="ghost" busy={busy === `assign-${t.task_id}`} onClick={() => assign(t.task_id)}>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Btn>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-[11px] text-slate-500">The leader rejects a move to a satellite without the required capabilities.</p>
      </Panel>

      <Panel title="Recent automatic reassignments (decided by the leader)">
        {(data?.recent_reassignments || []).length === 0 ? <div className="text-xs text-slate-400">None yet. Crash a task owner on the Leader Election page to see one.</div> : (
          <table className="w-full text-xs font-mono">
            <thead className="text-slate-500 text-left"><tr><th className="py-1 pr-3">Task</th><th className="pr-3">From</th><th className="pr-3">To</th><th className="pr-3">Version</th><th>Reason</th></tr></thead>
            <tbody className="text-slate-200">
              {data.recent_reassignments.slice().reverse().map((r, i) => (
                <tr key={i} className="border-t border-slate-800"><td className="py-1.5 pr-3">{r.task_id}</td><td className="pr-3">{r.from}</td><td className="pr-3">{r.to}</td><td className="pr-3">v{r.version}</td><td>{r.reason}</td></tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </div>
  );
}
