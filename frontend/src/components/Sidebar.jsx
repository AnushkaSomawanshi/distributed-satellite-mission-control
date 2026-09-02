import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Network,
  Activity,
  Radio,
  History,
  BookOpen,
  Zap,
  Server,
  Video,
  Layers,
  PlayCircle,
  HelpCircle
} from 'lucide-react';

const navItems = [
  { path: '/', name: 'Mission Overview', icon: LayoutDashboard },
  { path: '/topology', name: 'Constellation Topology', icon: Network },
  { path: '/observatory', name: 'Communication Observatory', icon: Radio },
  { path: '/replay', name: 'Communication Replay', icon: History },
  { path: '/concepts', name: 'Distributed Concepts Matrix', icon: BookOpen },
  { path: '/faults', name: 'Fault Simulator', icon: Zap },
  { path: '/registry', name: 'Satellite Registry', icon: Server },
  { path: '/telemetry', name: 'Live Telemetry Charts', icon: Activity },
  { path: '/multimedia', name: 'Satellite WebRTC Feed', icon: Video },
  { path: '/middleware', name: 'Middleware Architecture', icon: Layers },
  { path: '/demo-center', name: 'Classroom Demo Center', icon: PlayCircle },
  { path: '/teacher-questions', name: 'Teacher Questions & Viva', icon: HelpCircle }
];

export default function Sidebar() {
  return (
    <aside className="w-64 glass-panel border-r border-slate-800/80 p-4 flex flex-col justify-between shrink-0 min-h-[calc(100vh-4rem)]">
      <div className="space-y-6">
        <div className="px-3 py-2 text-xs font-semibold text-cyan-400/80 uppercase tracking-wider font-orbitron">
          Navigation & Controls
        </div>
        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-xs font-medium transition-all duration-150 ${
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

      {/* Syllabus Badge */}
      <div className="p-3.5 bg-slate-900/90 border border-slate-800 rounded-xl space-y-2 text-xs">
        <div className="flex items-center justify-between text-slate-300 font-semibold font-orbitron">
          <span>FA-1 Distributed Systems</span>
          <span className="text-cyan-400 font-mono">Unit 1 & 2</span>
        </div>
        <p className="text-[11px] text-slate-500 leading-relaxed">
          gRPC • RabbitMQ • WebSockets • P2P • WebRTC • Service Discovery • Fault Tolerance
        </p>
      </div>
    </aside>
  );
}
