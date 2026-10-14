import React, { useRef, useState } from 'react';
import { HardDrive, Upload, ShieldCheck, Trash2, Download } from 'lucide-react';
import { SATS, api, usePoll, useAction, PageHeader, Panel, Btn, ErrorNote, Stat } from '../lib/fa2';

const fmtBytes = (b) => (b > 1048576 ? `${(b / 1048576).toFixed(1)} MB` : b > 1024 ? `${(b / 1024).toFixed(1)} KB` : `${b} B`);

function toBase64(buf) {
  let s = '';
  const bytes = new Uint8Array(buf);
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return btoa(s);
}

export default function OrbitFSPage() {
  const [status] = usePoll('/api/orbitfs/status', 2000);
  const [files, , reloadFiles] = usePoll('/api/orbitfs/files', 2000);
  const [selected, setSelected] = useState(null);
  const [verify, setVerify] = useState(null);
  const fileRef = useRef(null);
  const { busy, error, run } = useAction();

  const upload = async (file) => {
    const buf = await file.arrayBuffer();
    const isImage = file.type.startsWith('image/');
    await run('upload', async () => {
      const res = await api('/api/orbitfs/files', { method: 'POST', body: { path: `${isImage ? 'images' : 'uploads'}/${file.name}`, content_b64: toBase64(buf), content_type: file.type || 'application/octet-stream' } });
      setSelected(res.path);
      reloadFiles();
    });
  };

  const list = files?.files || [];
  const current = list.find((f) => f.path === selected) || list[0];
  const dns = status?.datanodes || {};

  return (
    <div className="space-y-6">
      <PageHeader
        icon={HardDrive}
        title="OrbitFS — distributed file system"
        subtitle="Mission Control is the NameNode (metadata only). File data is split into chunks stored on 3 satellites each, written through a replication pipeline and checked with SHA-256. Crash a satellite and watch the NameNode copy its chunks to others."
      >
        <input ref={fileRef} type="file" className="hidden" onChange={(e) => e.target.files[0] && upload(e.target.files[0])} />
        <Btn busy={busy === 'upload'} onClick={() => fileRef.current?.click()}>
          <span className="inline-flex items-center gap-1"><Upload className="w-3.5 h-3.5" />Upload a file (images trigger a function)</span>
        </Btn>
      </PageHeader>
      <ErrorNote error={error} />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Files" value={status?.files ?? '—'} />
        <Stat label="Chunks" value={status?.chunks ?? '—'} hint={`${status ? fmtBytes(status.chunk_size) : ''} blocks, replication ${status?.replication_factor ?? 3}`} />
        <Stat label="Under-replicated" value={status?.under_replicated_chunks ?? '—'} hint="repaired automatically every 4 s" />
        <Stat label="DataNodes alive" value={Object.values(dns).filter((d) => d.alive).length} hint="satellites" />
      </div>

      <Panel title="DataNodes (satellites)">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          {SATS.map((s) => {
            const d = dns[s] || {};
            return (
              <div key={s} className={`rounded-xl border p-3 font-mono text-xs space-y-1 ${d.alive ? 'border-slate-800 bg-slate-900/70' : 'border-rose-500/50 bg-rose-500/10'}`}>
                <div className="flex justify-between"><span className="font-bold text-slate-100">{s}</span><span className={d.alive ? 'text-emerald-300' : 'text-rose-300'}>{d.alive ? 'UP' : 'DOWN'}</span></div>
                <div className="text-slate-400">{d.chunks ?? 0} chunks · {fmtBytes(d.used_bytes || 0)}</div>
                <div className="flex gap-1 pt-1">
                  <Btn tone="ghost" busy={busy === `c-${s}`} onClick={() => run(`c-${s}`, () => api('/api/fa2/faults/crash', { method: 'POST', body: { target: s } }))}>Crash</Btn>
                  <Btn tone="ghost" busy={busy === `r-${s}`} onClick={() => run(`r-${s}`, () => api('/api/fa2/faults/recover', { method: 'POST', body: { target: s } }))}>Recover</Btn>
                </div>
              </div>
            );
          })}
        </div>
      </Panel>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Panel title="Files" className="lg:col-span-1">
          {list.length === 0 ? <div className="text-xs text-slate-400">No files yet. Upload one, archive telemetry on the Cloud &amp; Data Lab page, or take a snapshot (snapshots are archived here).</div> : (
            <div className="space-y-1 max-h-96 overflow-y-auto">
              {list.map((f) => (
                <button key={f.path} onClick={() => { setSelected(f.path); setVerify(null); }}
                  className={`w-full text-left px-2 py-1.5 rounded-lg text-xs font-mono flex justify-between ${current?.path === f.path ? 'bg-cyan-500/10 text-cyan-200' : 'text-slate-300 hover:bg-slate-800/60'}`}>
                  <span className="truncate">{f.path}</span>
                  <span className={f.under_replicated ? 'text-amber-300' : 'text-slate-500'}>{fmtBytes(f.size)}</span>
                </button>
              ))}
            </div>
          )}
        </Panel>

        <Panel title={current ? current.path : 'Chunk map'} className="lg:col-span-2"
          right={current && (
            <div className="flex gap-2">
              <Btn tone="ghost" busy={busy === 'verify'} onClick={() => run('verify', async () => setVerify(await api(`/api/orbitfs/files/verify?path=${encodeURIComponent(current.path)}`)))}>
                <span className="inline-flex items-center gap-1"><ShieldCheck className="w-3.5 h-3.5" />Read &amp; verify</span>
              </Btn>
              <a className="px-3 py-2 rounded-lg text-xs font-semibold bg-slate-800 text-slate-200 border border-slate-700 inline-flex items-center gap-1" href={`/api/orbitfs/files/download?path=${encodeURIComponent(current.path)}`}><Download className="w-3.5 h-3.5" />Download</a>
              <Btn tone="ghost" busy={busy === 'del'} onClick={() => run('del', async () => { await api(`/api/orbitfs/files?path=${encodeURIComponent(current.path)}`, { method: 'DELETE' }); setSelected(null); reloadFiles(); })}>
                <Trash2 className="w-3.5 h-3.5" />
              </Btn>
            </div>
          )}>
          {!current ? <div className="text-xs text-slate-400">Select a file.</div> : (
            <>
              <div className="text-[11px] text-slate-400 font-mono">{fmtBytes(current.size)} · {current.chunks.length} chunk(s) · sha256 {current.sha256.slice(0, 16)}…</div>
              <div className="overflow-x-auto">
                <table className="text-xs font-mono">
                  <thead className="text-slate-500"><tr><th className="py-1 pr-3 text-left">Chunk</th>{SATS.map((s) => <th key={s} className="px-2">{s}</th>)}<th className="pl-3 text-left">Live copies</th></tr></thead>
                  <tbody>
                    {current.chunks.map((c) => (
                      <tr key={c.chunk_id} className="border-t border-slate-800">
                        <td className="py-1 pr-3 text-slate-300">#{c.index} <span className="text-slate-500">{fmtBytes(c.size)}</span></td>
                        {SATS.map((s) => {
                          const has = c.replicas.includes(s);
                          const live = c.live_replicas.includes(s);
                          return <td key={s} className="px-2 text-center"><span className={`inline-block w-4 h-4 rounded ${has ? (live ? 'bg-cyan-400' : 'bg-rose-500/70') : 'bg-slate-800'}`} /></td>;
                        })}
                        <td className={`pl-3 ${c.live_replicas.length < 3 ? 'text-amber-300' : 'text-emerald-300'}`}>{c.live_replicas.length}/3</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex gap-4 text-[11px] text-slate-400">
                <span><span className="inline-block w-3 h-3 rounded bg-cyan-400 mr-1 align-middle" />replica on a live satellite</span>
                <span><span className="inline-block w-3 h-3 rounded bg-rose-500/70 mr-1 align-middle" />replica on a down satellite</span>
              </div>
              {verify && (
                <div className="text-xs font-mono text-emerald-200 bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-2">
                  Read back {fmtBytes(verify.bytes)}, SHA-256 matches. Served by: {verify.served.map((s) => `#${current.chunks.findIndex((c) => c.chunk_id === s.chunk_id)}@${s.served_by}${s.tried.length > 1 ? ` (after trying ${s.tried.slice(0, -1).join(', ')})` : ''}`).join(' · ')}
                </div>
              )}
            </>
          )}
        </Panel>
      </div>

      <Panel title="NameNode activity">
        <div className="max-h-56 overflow-y-auto">
          <table className="w-full text-xs font-mono">
            <tbody className="text-slate-300">
              {(status?.recent_actions || []).slice().reverse().map((a, i) => (
                <tr key={i} className="border-t border-slate-800">
                  <td className="py-1 pr-3 text-slate-500">{new Date(a.at * 1000).toLocaleTimeString()}</td>
                  <td className={`pr-3 ${a.action === 'RE_REPLICATED' ? 'text-amber-300' : a.action.startsWith('TRIM') ? 'text-sky-300' : ''}`}>{a.action}</td>
                  <td className="text-slate-400">{Object.entries(a).filter(([k]) => !['at', 'action'].includes(k)).map(([k, v]) => `${k}=${v}`).join(' ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
