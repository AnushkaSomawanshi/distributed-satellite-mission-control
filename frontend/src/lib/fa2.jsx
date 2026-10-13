import React, { useEffect, useRef, useState } from 'react';

export const SATS = ['SAT-01', 'SAT-02', 'SAT-03', 'SAT-04', 'SAT-05'];

export const MUTEX_ALGOS = [
  { id: 'centralised', name: 'Centralised', theory: '3 per entry (0 if the requester leads)' },
  { id: 'ricart_agrawala', name: 'Ricart–Agrawala', theory: '2(N−1) = 8' },
  { id: 'token_ring', name: 'Token Ring', theory: 'depends on load (idle hops count)' },
  { id: 'lodha_kshemkalyani', name: 'Lodha–Kshemkalyani', theory: 'between N−1 = 4 and 2(N−1) = 8' },
];

export const ALGO_COLORS = {
  centralised: '#38bdf8',
  ricart_agrawala: '#a78bfa',
  token_ring: '#f59e0b',
  lodha_kshemkalyani: '#34d399',
  bully: '#f472b6',
  ring: '#22d3ee',
};

export async function api(path, { method = 'GET', body } = {}) {
  const res = await fetch(path, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = null;
  try {
    data = await res.json();
  } catch (e) {
    data = null;
  }
  if (!res.ok) {
    const detail = data && (data.detail || data.message);
    throw new Error(typeof detail === 'string' ? detail : `HTTP ${res.status}`);
  }
  return data;
}

/** Poll an endpoint while the page is open. Returns [data, error, refresh]. */
export function usePoll(path, intervalMs = 2000) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const alive = useRef(true);
  const load = async () => {
    try {
      const d = await api(path);
      if (alive.current) {
        setData(d);
        setError(null);
      }
    } catch (e) {
      if (alive.current) setError(e.message);
    }
  };
  useEffect(() => {
    alive.current = true;
    load();
    const t = setInterval(load, intervalMs);
    return () => {
      alive.current = false;
      clearInterval(t);
    };
  }, [path, intervalMs]);
  return [data, error, load];
}

/** Run an async action with busy + error state. */
export function useAction() {
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState(null);
  const run = async (name, fn) => {
    setBusy(name);
    setError(null);
    try {
      return await fn();
    } catch (e) {
      setError(e.message);
      return null;
    } finally {
      setBusy(null);
    }
  };
  return { busy, error, run, setError };
}

export function PageHeader({ icon: Icon, title, subtitle, children }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h2 className="text-xl font-bold font-orbitron text-slate-100 flex items-center gap-2">
          {Icon && <Icon className="w-5 h-5 text-cyan-400" />}
          <span>{title}</span>
        </h2>
        {subtitle && <p className="text-xs text-slate-400 mt-1 max-w-3xl">{subtitle}</p>}
      </div>
      {children && <div className="flex flex-wrap items-center gap-2">{children}</div>}
    </div>
  );
}

export function Panel({ title, icon: Icon, right, children, className = '' }) {
  return (
    <div className={`glass-panel p-5 rounded-xl border border-slate-800/80 space-y-4 ${className}`}>
      {(title || right) && (
        <div className="flex flex-wrap items-center justify-between gap-2">
          {title && (
            <h3 className="font-orbitron font-semibold text-slate-200 text-sm flex items-center gap-2">
              {Icon && <Icon className="w-4 h-4 text-cyan-400" />}
              <span>{title}</span>
            </h3>
          )}
          {right}
        </div>
      )}
      {children}
    </div>
  );
}

export function Btn({ onClick, busy, disabled, children, tone = 'primary', title }) {
  const tones = {
    primary: 'bg-cyan-600 hover:bg-cyan-500 text-slate-950',
    ghost: 'bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700',
    danger: 'bg-rose-600/90 hover:bg-rose-500 text-white',
  };
  return (
    <button
      title={title}
      onClick={onClick}
      disabled={disabled || busy}
      className={`px-3 py-2 rounded-lg text-xs font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed ${tones[tone]}`}
    >
      {busy ? 'Working…' : children}
    </button>
  );
}

export function Select({ value, onChange, options, label }) {
  return (
    <label className="text-[11px] text-slate-400 flex items-center gap-1.5">
      {label && <span>{label}</span>}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="bg-slate-900 border border-slate-700 rounded-md px-2 py-1.5 text-xs text-slate-200"
      >
        {options.map((o) => (
          <option key={o.value ?? o} value={o.value ?? o}>
            {o.label ?? o}
          </option>
        ))}
      </select>
    </label>
  );
}

export function NumberInput({ value, onChange, label, step = 1, width = 'w-20' }) {
  return (
    <label className="text-[11px] text-slate-400 flex items-center gap-1.5">
      {label && <span>{label}</span>}
      <input
        type="number"
        step={step}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={`${width} bg-slate-900 border border-slate-700 rounded-md px-2 py-1.5 text-xs text-slate-200`}
      />
    </label>
  );
}

export function ErrorNote({ error }) {
  if (!error) return null;
  return <div className="text-xs text-rose-300 bg-rose-500/10 border border-rose-500/30 rounded-lg px-3 py-2">{error}</div>;
}

export function Stat({ label, value, hint }) {
  return (
    <div className="bg-slate-900/80 rounded-xl border border-slate-800 p-3">
      <div className="text-[10px] uppercase tracking-wide text-slate-500">{label}</div>
      <div className="text-lg font-bold text-slate-100 font-mono mt-0.5">{value ?? '—'}</div>
      {hint && <div className="text-[10px] text-slate-500 mt-0.5">{hint}</div>}
    </div>
  );
}

/** Vector clock comparison, same rule as the satellites use. */
export function compareVectors(a = {}, b = {}) {
  let less = false;
  let greater = false;
  const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
  keys.forEach((k) => {
    const x = a[k] || 0;
    const y = b[k] || 0;
    if (x < y) less = true;
    else if (x > y) greater = true;
  });
  if (less && !greater) return 'BEFORE';
  if (greater && !less) return 'AFTER';
  if (!less && !greater) return 'EQUAL';
  return 'CONCURRENT';
}

export const fmtVector = (v = {}) => `[${SATS.map((s) => v[s] ?? 0).join(', ')}]`;
