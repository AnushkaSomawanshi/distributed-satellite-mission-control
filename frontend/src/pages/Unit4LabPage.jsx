import React, { useState } from 'react';
import { Cloud, Database, Zap, Boxes, Network, BookOpen } from 'lucide-react';
import { SATS, api, usePoll, useAction, PageHeader, Panel, Btn, Select, NumberInput, ErrorNote, Stat } from '../lib/fa2';

function MapReduceSection() {
  const [jobs, , reload] = usePoll('/api/mapreduce/jobs', 4000);
  const [job, setJob] = useState('health_stats');
  const [last, setLast] = useState(null);
  const { busy, error, run } = useAction();
  const result = last || jobs?.jobs?.[jobs.jobs.length - 1];
  return (
    <Panel title="MapReduce on OrbitFS (Apache Hadoop case study)" icon={Database}>
      <p className="text-xs text-slate-400">Map tasks run on satellites that hold the chunk (data locality) with a combiner; output is partitioned by key and shuffled straight to reducer satellites. A failed map attempt is re-run on another replica.</p>
      <div className="flex flex-wrap items-end gap-3">
        <Btn tone="ghost" busy={busy === 'archive'} onClick={() => run('archive', async () => { await api('/api/mapreduce/archive', { method: 'POST' }); reload(); })}>
          1. Archive telemetry to OrbitFS ({jobs?.samples_buffered ?? 0} samples)
        </Btn>
        <Select label="Job" value={job} onChange={setJob} options={[{ value: 'health_stats', label: 'health_stats' }, { value: 'status_counts', label: 'status_counts' }]} />
        <Btn busy={busy === 'job'} onClick={() => run('job', async () => { setLast(await api('/api/mapreduce/jobs', { method: 'POST', body: { job } })); reload(); })}>2. Run job on latest archive</Btn>
      </div>
      <ErrorNote error={error} />
      {result && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <Stat label="Input" value={`${result.chunks} chunks`} hint={result.input} />
            <Stat label="Map tasks (data-local)" value={`${result.counters.map_tasks} (${result.counters.data_local_map_tasks})`} />
            <Stat label="Records read" value={result.counters.records_read} />
            <Stat label="Shuffle" value={`${result.counters.shuffle_bytes} B`} hint={`${result.counters.reduce_tasks} reducers: ${result.reducers.join(', ')}`} />
            <Stat label="Time" value={`${result.phases_ms.total} ms`} hint={`map+shuffle ${result.phases_ms.map_and_shuffle} · reduce ${result.phases_ms.reduce}`} />
          </div>
          <div className="text-[11px] text-slate-400 font-mono">Map assignment: {Object.entries(result.map_assignment).map(([s, c]) => `${s}: ${c.length} chunk(s)`).join(' · ')}{result.retries.length ? ` · ${result.retries.length} re-executed` : ''}</div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono">
              <thead className="text-slate-500 text-left"><tr><th className="py-1 pr-3">Key</th><th>Result</th></tr></thead>
              <tbody className="text-slate-200">
                {Object.entries(result.results).map(([k, v]) => (
                  <tr key={k} className="border-t border-slate-800"><td className="py-1 pr-3">{k}</td><td className="text-slate-300">{Object.entries(v).map(([a, b]) => `${a}=${b}`).join('  ')}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </Panel>
  );
}

function ServerlessSection() {
  const [fns] = usePoll('/api/serverless/functions', 2000);
  const [inv, , reload] = usePoll('/api/serverless/invocations?limit=15', 2000);
  const [peer, setPeer] = useState('SAT-03');
  const { busy, error, run } = useAction();
  return (
    <Panel title="Serverless functions" icon={Zap}>
      <p className="text-xs text-slate-400">Each function instance is its own process. The first call pays a cold start; calls within {fns?.idle_timeout_s ?? 20} s reuse a warm instance; idle instances are stopped (scale to zero). Triggers come from the RabbitMQ event streams; outputs go to OrbitFS.</p>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="text-slate-500 text-left"><tr><th className="py-1 pr-3">Function</th><th className="pr-3">Trigger</th><th className="pr-3">Warm instances</th><th className="pr-3">Invocations</th><th>Cold starts</th></tr></thead>
          <tbody className="text-slate-200">
            {(fns?.functions || []).map((f) => (
              <tr key={f.name} className="border-t border-slate-800"><td className="py-1.5 pr-3 font-mono">{f.name}<div className="text-[10px] text-slate-500">{f.description}</div></td><td className="pr-3 font-mono text-[11px]">{f.trigger}</td><td className="pr-3">{f.warm_instances}</td><td className="pr-3">{f.invocations}</td><td>{f.cold_starts}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <Select label="Incident report for" value={peer} onChange={setPeer} options={SATS} />
        <Btn busy={busy === 'inc'} onClick={() => run('inc', async () => { await api('/api/serverless/invoke', { method: 'POST', body: { function: 'incident_report', event: { detail: { peer } } } }); reload(); })}>Invoke now</Btn>
        <span className="text-[11px] text-slate-500">Or crash a satellite / upload an image / take a snapshot to trigger functions automatically.</span>
      </div>
      <ErrorNote error={error} />
      <div className="overflow-x-auto max-h-72">
        <table className="w-full text-xs font-mono">
          <thead className="text-slate-500 text-left sticky top-0 bg-slate-950"><tr><th className="py-1 pr-3">Time</th><th className="pr-3">Function</th><th className="pr-3">Trigger</th><th className="pr-3">Start</th><th className="pr-3">Exec</th><th className="pr-3">PID</th><th>Output</th></tr></thead>
          <tbody className="text-slate-200">
            {(inv?.invocations || []).map((r) => (
              <tr key={r.invocation_id} className="border-t border-slate-800">
                <td className="py-1 pr-3">{new Date(r.started_at * 1000).toLocaleTimeString()}</td>
                <td className="pr-3">{r.function}</td>
                <td className="pr-3 text-slate-400">{r.trigger}</td>
                <td className={`pr-3 ${r.cold_start ? 'text-amber-300' : 'text-emerald-300'}`}>{r.cold_start ? `cold ${r.cold_start_ms} ms` : 'warm'}</td>
                <td className="pr-3">{r.exec_ms ?? '—'} ms</td>
                <td className="pr-3">{r.pid}</td>
                <td className="text-slate-400">{r.output_path || r.error || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {(inv?.scale_events || []).length > 0 && (
        <div className="text-[11px] text-slate-400 font-mono">Scaling: {inv.scale_events.slice(0, 6).map((e) => `${new Date(e.at * 1000).toLocaleTimeString()} ${e.function} ${e.event}`).join(' · ')}</div>
      )}
    </Panel>
  );
}

function ObjectsSection() {
  const [objs] = usePoll('/api/objects', 5000);
  const [name, setName] = useState('satellite.SAT-02.payload');
  const [lat, setLat] = useState(18.52);
  const [lon, setLon] = useState(73.85);
  const [log, setLog] = useState([]);
  const { busy, error, run } = useAction();
  const call = (method, args = {}) => run(method, async () => {
    const r = await api('/api/objects/call', { method: 'POST', body: { name, method, args } });
    setLog((l) => [r, ...l].slice(0, 8));
  });
  const names = Object.keys(objs?.objects || {}).sort();
  return (
    <Panel title="Distributed objects (Pyro5)" icon={Boxes}>
      <p className="text-xs text-slate-400">Each satellite exports a PayloadController object, registered by name in the Pyro name server. Unlike the gRPC procedures from FA-1, calls act on one object with state: point it, capture twice, and status shows the state it kept.</p>
      <div className="flex flex-wrap items-end gap-3">
        <Select label="Object" value={name} onChange={setName} options={names.length ? names : [name]} />
        <Btn tone="ghost" busy={busy === 'status'} onClick={() => call('status')}>status()</Btn>
        <NumberInput label="lat" value={lat} onChange={setLat} step={0.01} />
        <NumberInput label="lon" value={lon} onChange={setLon} step={0.01} />
        <Btn tone="ghost" busy={busy === 'point'} onClick={() => call('point', { lat: Number(lat), lon: Number(lon) })}>point()</Btn>
        <Btn tone="ghost" busy={busy === 'capture'} onClick={() => call('capture')}>capture()</Btn>
      </div>
      <div className="text-[11px] text-slate-500 font-mono">Registered: {names.join(', ') || 'none (name server not reachable?)'}</div>
      <ErrorNote error={error} />
      <div className="space-y-1">
        {log.map((r, i) => (
          <div key={i} className="text-xs font-mono bg-slate-900/70 border border-slate-800 rounded-lg px-2 py-1.5">
            <span className="text-cyan-300">{r.object}.{r.method}({Object.values(r.args).join(', ')})</span> <span className="text-slate-500">{r.latency_ms} ms</span>
            <div className="text-slate-300">{JSON.stringify(r.result)}</div>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function GatewaySection() {
  const [probe, setProbe] = useState(null);
  const { busy, error, run } = useAction();
  const test = () => run('gw', async () => {
    const rows = [];
    for (let i = 0; i < 3; i += 1) {
      const res = await fetch('/api/satellites');
      rows.push({ status: res.status, cache: res.headers.get('X-Cache-Status'), upstream: res.headers.get('X-Upstream'), gateway: res.headers.get('X-Gateway') });
    }
    const who = await (await fetch('/api/gateway/whoami')).json();
    setProbe({ rows, who });
  });
  const via = probe?.rows?.some((r) => r.gateway);
  return (
    <Panel title="Web gateway (Nginx)" icon={Network}>
      <p className="text-xs text-slate-400">The gateway is the single entry point for browsers and satellites: it serves this frontend, proxies the API and WebSockets, caches the busiest read-only endpoints for 1 s, rate-limits each client, and fails over to a warm standby Mission Control. Open the dashboard on port 8080 to go through it.</p>
      <Btn busy={busy === 'gw'} onClick={test}>Probe the path of 3 requests</Btn>
      <ErrorNote error={error} />
      {probe && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <Stat label="Through the gateway" value={via ? 'yes' : 'no'} hint={via ? 'X-Gateway header present' : 'open the app on :8080'} />
            <Stat label="Served by replica" value={`${probe.who.instance} (${probe.who.active ? 'active' : 'passive'})`} />
            <Stat label="Cache results" value={probe.rows.map((r) => r.cache || '—').join(' · ')} hint="MISS then HIT within 1 s" />
          </div>
          {probe.who.role_transitions?.length > 0 && <div className="text-[11px] text-slate-400">Failover history: {probe.who.role_transitions.map((t) => `${new Date(t.at * 1000).toLocaleTimeString()} → ${t.active ? 'active' : 'passive'}`).join(' · ')}</div>}
        </>
      )}
      <p className="text-[11px] text-slate-500">Failover test: <code>docker compose stop mission-control</code>, keep using the dashboard on :8080 (the standby takes over within ~6 s), then <code>docker compose start mission-control</code>.</p>
    </Panel>
  );
}

const CASES = [
  ['AWS', 'AWS Ground Station (antenna time as a service), IoT Core (telemetry ingestion), Lambda (functions), S3 (object storage), DynamoDB (task table)', 'Ground segment = Mission Control; RabbitMQ ingestion ≈ IoT Core; serverless runtime ≈ Lambda; OrbitFS ≈ S3; task mirror ≈ DynamoDB'],
  ['Cloudflare', 'Anycast edge network; Workers run code in 300+ edge locations; edge caching', 'Ground stations as edge points of presence: the gateway micro-cache and functions would run near operators'],
  ['Megaport', 'Software-defined interconnect: private virtual links between data centres and clouds on demand', 'Private links between ground stations and cloud regions so telemetry never crosses the public internet'],
  ['Apache Hadoop', 'HDFS (NameNode + DataNodes, 3 replicas, rack awareness) and MapReduce (data-local map, shuffle, reduce)', 'OrbitFS + MapReduce here: NameNode in Mission Control, DataNodes and map/reduce tasks on satellites'],
  ['Kubernetes', 'Declarative deployments, StatefulSets with stable identity, liveness/readiness probes, self-healing', 'k8s/ manifests: satellites as a StatefulSet (stable SAT-01..05), probes, gateway NodePort'],
];

export default function Unit4LabPage() {
  return (
    <div className="space-y-6">
      <PageHeader icon={Cloud} title="Cloud & Data Lab (Unit 4)" subtitle="MapReduce over OrbitFS, serverless functions, distributed objects and the web gateway — all running for real on this deployment — plus how the case studies map onto it." />
      <MapReduceSection />
      <ServerlessSection />
      <ObjectsSection />
      <GatewaySection />
      <Panel title="Case studies mapped onto OrbitTrack" icon={BookOpen}>
        <table className="w-full text-xs">
          <thead className="text-slate-500 text-left"><tr><th className="py-1 pr-3">Case study</th><th className="pr-3">What it provides</th><th>Where it appears here</th></tr></thead>
          <tbody className="text-slate-300">
            {CASES.map(([n, what, here]) => <tr key={n} className="border-t border-slate-800 align-top"><td className="py-1.5 pr-3 font-semibold text-slate-100">{n}</td><td className="pr-3">{what}</td><td>{here}</td></tr>)}
          </tbody>
        </table>
      </Panel>
    </div>
  );
}
