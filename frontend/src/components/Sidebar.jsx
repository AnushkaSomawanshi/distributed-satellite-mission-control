import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Network,
  Activity,
  Radio,
  History,
  Zap,
  Server,
  Video,
  Terminal,
  Target,
  GitBranch,
  Crown,
  Clock,
  Swords,
  Camera,
  Workflow,
  RadioTower,
  HardDrive,
  Cloud,
} from 'lucide-react';

const navItems = [
  { path: '/', name: 'Mission Overview', icon: LayoutDashboard },
  { path: '/registry', name: 'Satellite Fleet', icon: Server },
  { path: '/topology', name: 'Fleet Topology', icon: Network },
  { path: '/telemetry', name: 'Live Telemetry', icon: Activity },
  { path: '/tasks', name: 'Mission Tasks', icon: Target },
  { path: '/observatory', name: 'Communications', icon: Radio },
  { path: '/runtime-observability', name: 'System Events', icon: Terminal },
  { path: '/incidents', name: 'Incidents & Recovery', icon: History },
  { path: '/faults', name: 'Fault Controls', icon: Zap },
  { path: '/partition', name: 'Network Reconciliation', icon: Network },
  { path: '/multimedia', name: 'Payload Streaming', icon: Video }
];

// FA-2 (Unit 3): algorithms that run between the satellites
const fa2Items = [
  { path: '/lens', name: 'Causality Lens', icon: GitBranch },
  { path: '/election', name: 'Leader Election', icon: Crown },
  { path: '/clocks', name: 'Clock Sync', icon: Clock },
  { path: '/arena', name: 'Algorithm Arena', icon: Swords },
  { path: '/snapshots', name: 'Global Snapshot', icon: Camera },
  { path: '/deadlock', name: 'Deadlock Detection', icon: Workflow },
  { path: '/blackout', name: 'Ground Blackout', icon: RadioTower }
];

// FA-2 (Unit 4): data, cloud and web layers
const unit4Items = [
  { path: '/orbitfs', name: 'OrbitFS', icon: HardDrive },
  { path: '/unit4', name: 'Cloud & Data Lab', icon: Cloud }
];


export default function Sidebar() {
  return (
    <aside className="w-56 glass-panel border-r border-slate-800/80 p-3 flex flex-col justify-between shrink-0 min-h-[calc(100vh-4rem)]">
      <div className="space-y-6">
        <div className="px-3 py-2 text-xs font-semibold text-cyan-400/80 uppercase tracking-wider font-orbitron">
          ORBITTRACK
        </div>
        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center space-x-3 px-3.5 py-2 rounded-xl text-xs font-medium transition-all duration-150 ${
                    isActive
                      ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 glow-cyan font-semibold'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`
                }
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span>{item.name}</span>
              </NavLink>
            );
          })}
        </nav>
        <div className="px-3 pt-2 text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Distributed algorithms</div>
        <nav className="space-y-1">
          {fa2Items.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center space-x-3 px-3.5 py-2 rounded-xl text-xs font-medium transition-all duration-150 ${
                    isActive
                      ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 glow-cyan font-semibold'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`
                }
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span>{item.name}</span>
              </NavLink>
            );
          })}
        </nav>
        <div className="px-3 pt-2 text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Cloud &amp; data</div>
        <nav className="space-y-1">
          {unit4Items.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center space-x-3 px-3.5 py-2 rounded-xl text-xs font-medium transition-all duration-150 ${
                    isActive
                      ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 glow-cyan font-semibold'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`
                }
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span>{item.name}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>

      <div className="px-3 py-3 border-t border-slate-800/80 text-[11px] text-slate-500">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400" />
          <span>Mission services</span>
        </div>
        <p className="mt-1">Operational status is sourced from Mission Control.</p>
      </div>
    </aside>
  );
}

