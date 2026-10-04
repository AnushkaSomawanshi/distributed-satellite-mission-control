import React, { useState, useEffect } from 'react';
import { Target, Cpu, CheckCircle, ShieldAlert, ArrowRight, RefreshCw, Clock } from 'lucide-react';

export default function MissionTasksPage() {
  const [tasks, setTasks] = useState([]);
  const [capabilitiesMap, setCapabilitiesMap] = useState({});
  const [loading, setLoading] = useState(false);
  const [selectedTask, setSelectedTask] = useState(null);
  const [reassignNode, setReassignNode] = useState('SAT-01');

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/tasks');
      const data = await res.json();
      setTasks(data.tasks || []);
      setCapabilitiesMap(data.capabilities_map || {});
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, []);

  const handleReassign = async (taskId) => {
    try {
      const res = await fetch(`/api/tasks/${taskId}/reassign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_owner: reassignNode, reason: 'OPERATOR_MANUAL_REASSIGNMENT' })
      });
      if (res.ok) {
        fetchTasks();
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold font-orbitron text-slate-100 flex items-center space-x-2">
            <Target className="w-5 h-5 text-cyan-400" />
            <span>Mission Tasks & Capability Allocation</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            First-class mission tasks mapped to satellite capability constraints and vector clock versioning.
          </p>
        </div>
        <button
          onClick={fetchTasks}
          disabled={loading}
          className="px-3.5 py-2 bg-slate-900 border border-slate-800 hover:border-cyan-500/40 text-slate-200 rounded-xl text-xs font-semibold flex items-center space-x-2 transition-all"
        >
          <RefreshCw className={`w-4 h-4 text-cyan-400 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Tasks</span>
        </button>
      </div>

      {/* Satellite Capabilities Overview */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        {Object.entries(capabilitiesMap).map(([satId, caps]) => (
          <div key={satId} className="glass-panel p-4 rounded-xl border border-slate-800/80 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-orbitron font-bold text-cyan-300 text-sm">{satId}</span>
              <Cpu className="w-4 h-4 text-slate-500" />
            </div>
            <div className="flex flex-wrap gap-1">
              {caps.map((cap) => (
                <span key={cap} className="px-2 py-0.5 bg-slate-900 text-slate-300 border border-slate-700/60 rounded text-[10px] font-mono font-semibold">
                  {cap}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Mission Tasks Table */}
      <div className="glass-panel rounded-xl border border-slate-800/80 overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
          <span className="font-orbitron font-semibold text-slate-200 text-sm">Active Constellation Mission Tasks</span>
          <span className="text-xs font-mono text-cyan-400">{tasks.length} Managed Tasks</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900/50 text-slate-400 font-mono">
                <th className="p-3.5">Task ID</th>
                <th className="p-3.5">Mission</th>
                <th className="p-3.5">Priority</th>
                <th className="p-3.5">Required Capabilities</th>
                <th className="p-3.5">Current Owner</th>
                <th className="p-3.5">Status</th>
                <th className="p-3.5">Lamport T</th>
                <th className="p-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {tasks.map((task) => (
                <tr key={task.task_id} className="hover:bg-slate-900/40 transition-colors">
                  <td className="p-3.5 font-mono font-bold text-cyan-300">{task.task_id}</td>
                  <td className="p-3.5 text-slate-300">{task.mission_id}</td>
                  <td className="p-3.5">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${task.priority === 'HIGH' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' : 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'}`}>
                      {task.priority}
                    </span>
                  </td>
                  <td className="p-3.5 font-mono">
                    <div className="flex flex-wrap gap-1">
                      {task.required_capabilities.map((c) => (
                        <span key={c} className="px-1.5 py-0.5 bg-slate-900 text-slate-300 border border-slate-800 rounded text-[10px]">
                          {c}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="p-3.5 font-mono font-bold text-slate-200">
                    {task.current_owner}
                    {task.previous_owner && <span className="text-[10px] text-slate-500 block">was {task.previous_owner}</span>}
                  </td>
                  <td className="p-3.5">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${task.status === 'RUNNING' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'}`}>
                      {task.status}
                    </span>
                  </td>
                  <td className="p-3.5 font-mono text-cyan-400">T={task.lamport_timestamp}</td>
                  <td className="p-3.5 text-right space-x-2">
                    <button
                      onClick={() => setSelectedTask(task)}
                      className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-[11px] font-medium"
                    >
                      Inspect
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Task Reassignment Controls */}
      {selectedTask && (
        <div className="glass-panel p-5 rounded-xl border border-cyan-500/40 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="font-orbitron font-bold text-cyan-300 text-sm">
              Manual Task Transfer: {selectedTask.task_id}
            </h3>
            <button onClick={() => setSelectedTask(null)} className="text-xs text-slate-400 hover:text-slate-200">Close</button>
          </div>
          <p className="text-xs text-slate-300">{selectedTask.description}</p>
          <div className="flex items-center space-x-4 text-xs font-mono">
            <div>
              <span className="text-slate-400">Current Owner:</span>{' '}
              <span className="font-bold text-slate-200">{selectedTask.current_owner}</span>
            </div>
            <div>
              <span className="text-slate-400">Transfer To:</span>{' '}
              <select
                value={reassignNode}
                onChange={(e) => setReassignNode(e.target.value)}
                className="bg-slate-900 border border-slate-700 text-slate-200 rounded px-2 py-1 ml-2 font-mono"
              >
                {['SAT-01', 'SAT-02', 'SAT-03', 'SAT-04', 'SAT-05'].map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            <button
              onClick={() => handleReassign(selectedTask.task_id)}
              className="px-4 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold rounded-lg transition-all"
            >
              Transfer Ownership
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
