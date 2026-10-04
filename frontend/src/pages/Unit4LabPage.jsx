import React, { useState, useEffect } from 'react';
import { Layers, Database, Zap, Cpu, Server, Play, FileText, CheckCircle2 } from 'lucide-react';

export default function Unit4LabPage() {
  const [activeTab, setActiveTab] = useState('STORAGE');
  const [storageArtifacts, setStorageArtifacts] = useState([]);
  const [serverlessLogs, setServerlessLogs] = useState([]);
  const [hadoopResult, setHadoopResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchStorage = async () => {
    try {
      const res = await fetch('/api/unit4/storage');
      const data = await res.json();
      setStorageArtifacts(data.artifacts || []);
    } catch (e) {
      console.error(e);
    }
  };

  const triggerServerless = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/unit4/serverless', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ function_name: 'GENERATE_INCIDENT_REPORT', event_payload: { origin: 'UNIT4_LAB_MANUAL' } })
      });
      const data = await res.json();
      setServerlessLogs((prev) => [data, ...prev]);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const runHadoop = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/unit4/hadoop?job_name=CONSTELLATION_HEALTH_TRENDS');
      const data = await res.json();
      setHadoopResult(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStorage();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold font-orbitron text-slate-100 flex items-center space-x-2">
            <Layers className="w-5 h-5 text-cyan-400" />
            <span>Unit 4 Advanced Infrastructure Laboratory</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Distributed Storage, Serverless Event Processing, Apache Hadoop MapReduce Analytics, and Kubernetes Deployment Topology.
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex space-x-2 border-b border-slate-800 pb-2">
        {[
          { id: 'STORAGE', name: 'Distributed Storage / DFS', icon: Database },
          { id: 'SERVERLESS', name: 'Serverless Functions', icon: Zap },
          { id: 'HADOOP', name: 'Apache Hadoop MapReduce', icon: Cpu },
          { id: 'KUBERNETES', name: 'Kubernetes Manifests', icon: Server }
        ].map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center space-x-2 transition-all ${
                activeTab === tab.id
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.name}</span>
            </button>
          );
        })}
      </div>

      {/* STORAGE TAB */}
      {activeTab === 'STORAGE' && (
        <div className="glass-panel p-5 rounded-xl border border-slate-800/80 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-orbitron font-semibold text-slate-200 text-sm">Persisted Distributed Storage Artifacts</h3>
            <button onClick={fetchStorage} className="px-3 py-1 bg-slate-900 text-xs font-mono text-cyan-400 border border-slate-800 rounded">
              Refresh Artifacts
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs font-mono">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/50 text-slate-400">
                  <th className="p-3">Artifact ID</th>
                  <th className="p-3">Category</th>
                  <th className="p-3">Path</th>
                  <th className="p-3">Size (bytes)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {storageArtifacts.map((art) => (
                  <tr key={art.artifact_id} className="hover:bg-slate-900/40">
                    <td className="p-3 text-cyan-300 font-bold">{art.artifact_id}</td>
                    <td className="p-3 text-slate-300">{art.category}</td>
                    <td className="p-3 text-slate-400 text-[11px] font-mono">{art.path}</td>
                    <td className="p-3 text-emerald-400 font-bold">{art.size_bytes} B</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* SERVERLESS TAB */}
      {activeTab === 'SERVERLESS' && (
        <div className="glass-panel p-5 rounded-xl border border-slate-800/80 space-y-4 font-mono text-xs">
          <div className="flex items-center justify-between">
            <h3 className="font-orbitron font-semibold text-slate-200 text-sm">Serverless Event Trigger & Execution Logs</h3>
            <button
              onClick={triggerServerless}
              disabled={loading}
              className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold rounded-lg flex items-center space-x-2 transition-all glow-cyan"
            >
              <Zap className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              <span>Trigger Serverless Function</span>
            </button>
          </div>
          <div className="space-y-2">
            {serverlessLogs.map((log) => (
              <div key={log.execution_id} className="p-3 bg-slate-900 rounded-lg border border-slate-800 space-y-1">
                <div className="flex items-center justify-between text-cyan-300 font-bold">
                  <span>{log.function_name} ({log.execution_id})</span>
                  <span className="text-emerald-400">{log.duration_ms} ms</span>
                </div>
                <div className="text-slate-400">{log.output_summary}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* HADOOP TAB */}
      {activeTab === 'HADOOP' && (
        <div className="glass-panel p-5 rounded-xl border border-slate-800/80 space-y-4 font-mono text-xs">
          <div className="flex items-center justify-between">
            <h3 className="font-orbitron font-semibold text-slate-200 text-sm">Apache Hadoop MapReduce Job Execution</h3>
            <button
              onClick={runHadoop}
              disabled={loading}
              className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold rounded-lg flex items-center space-x-2 transition-all glow-cyan"
            >
              <Cpu className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              <span>Run MapReduce Job</span>
            </button>
          </div>
          {hadoopResult && (
            <div className="p-4 bg-slate-900 rounded-lg border border-slate-800 space-y-3">
              <div className="flex items-center justify-between font-bold text-cyan-300">
                <span>JobID: {hadoopResult.job_id}</span>
                <span className="text-emerald-400">Duration: {hadoopResult.job_duration_ms} ms</span>
              </div>
              <div className="text-slate-300 font-semibold">{hadoopResult.engine}</div>
              <div className="text-slate-400">Records Processed: {hadoopResult.records_processed} | Availability: {hadoopResult.overall_system_availability}</div>
            </div>
          )}
        </div>
      )}

      {/* KUBERNETES TAB */}
      {activeTab === 'KUBERNETES' && (
        <div className="glass-panel p-5 rounded-xl border border-slate-800/80 space-y-4 font-mono text-xs">
          <h3 className="font-orbitron font-semibold text-slate-200 text-sm">Kubernetes Deployment Manifest Topology (k8s/)</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 bg-slate-900 rounded-lg border border-slate-800 space-y-2">
              <span className="font-bold text-cyan-300">k8s/configmap.yaml</span>
              <p className="text-slate-400 text-[11px]">Defines namespace 'orbital-mission', ConfigMap parameters for PostgreSQL, RabbitMQ, and Mission Control URLs.</p>
            </div>
            <div className="p-4 bg-slate-900 rounded-lg border border-slate-800 space-y-2">
              <span className="font-bold text-cyan-300">k8s/backend-deployment.yaml</span>
              <p className="text-slate-400 text-[11px]">Deployments & ClusterIP Services for Mission Control backend with liveness/readiness probes.</p>
            </div>
            <div className="p-4 bg-slate-900 rounded-lg border border-slate-800 space-y-2">
              <span className="font-bold text-cyan-300">k8s/satellites-deployment.yaml</span>
              <p className="text-slate-400 text-[11px]">Containerized deployments for independent satellite nodes (SAT-01 through SAT-05).</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
