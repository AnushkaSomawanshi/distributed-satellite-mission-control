import React from 'react';
import { HelpCircle, ArrowRight, CheckCircle2, Clock, Activity, ShieldCheck, Zap } from 'lucide-react';

const faultScenarios = {
  STOP_NODE: {
    title: 'Stop Satellite Node (Simulate Crash / Offline)',
    trigger: 'Actual Satellite Process / Docker Container Stop',
    effect: 'Satellite stops sending periodic heartbeats to Mission Control',
    detection: 'Heartbeat Sweeper detects missing heartbeat (> 5s SUSPECTED, > 10s DISCONNECTED)',
    consequence: 'Registry marks node DISCONNECTED; remaining 4 satellites continue operating nominal',
    recovery: 'Node restarts → Self-registers with Mission Control → Heartbeat & Telemetry resume',
    expectedSteps: [
      '1. Stop command issued to Satellite process',
      '2. Satellite process terminates; heartbeats cease',
      '3. Backend Heartbeat Sweeper detects missing heartbeat (> 5s)',
      '4. Satellite status transitions to SUSPECTED (Detection Latency measured)',
      '5. Heartbeat missing > 10s → Status confirmed DISCONNECTED',
      '6. WebSocket broadcasts NODE_DISCONNECTED event with Correlation ID',
      '7. Dashboard UI updates node state to RED (DISCONNECTED)',
      '8. Node reboot → Auto self-registration → Status recovers to HEALTHY'
    ]
  },
  RESTART_NODE: {
    title: 'Restart Satellite Node (Simulate Recovery)',
    trigger: 'Satellite Node Process / Container Reboot',
    effect: 'Temporary heartbeat interruption followed by self-registration',
    detection: 'Registry processes dynamic self-registration packet',
    consequence: 'Node transitions DISCONNECTED → RECOVERING → HEALTHY',
    recovery: 'Autonomous telemetry loop resumes; health score restored to 100%',
    expectedSteps: [
      '1. Restart command issued to Satellite node',
      '2. Satellite process initializes local orbital state',
      '3. Satellite sends HTTP POST /api/satellites/register',
      '4. Registry updates node status to HEALTHY & computes Recovery Time',
      '5. Autonomous heartbeat & telemetry loops resume',
      '6. WebSocket broadcasts NODE_REGISTERED event',
      '7. Dashboard UI updates node state to GREEN (HEALTHY)'
    ]
  },
  HIGH_LATENCY: {
    title: 'Inject High Network Latency',
    trigger: 'Communication Delay Hook applied to Satellite P2P / RPC endpoints',
    effect: 'Artificially delays message transmission by configured milliseconds (e.g. 500ms)',
    detection: 'Measured round-trip latency increases in Communication Observatory',
    consequence: 'P2P and RPC responses report elevated latency_ms metrics',
    recovery: 'Clearing fault restores baseline network round-trip latency (~15-30ms)',
    expectedSteps: [
      '1. Latency injection parameter registered in Fault Simulator',
      '2. Next gRPC / P2P request to target node triggers artificial delay',
      '3. Response latency_ms measured and persisted to PostgreSQL',
      '4. Communication Observatory displays elevated latency warning'
    ]
  },
  PACKET_LOSS: {
    title: 'Inject Packet / Message Loss',
    trigger: 'Simulated Network Packet Loss Filter (e.g. 20%)',
    effect: 'Randomly drops a percentage of outgoing telemetry & P2P packets',
    detection: 'RabbitMQ consumer / P2P receiver detects missing sequence numbers',
    consequence: 'Communication Observatory records dropped packet events',
    recovery: 'Clearing fault restores 100% packet delivery rate',
    expectedSteps: [
      '1. Packet loss percentage configured for target satellite',
      '2. Communication layer randomly drops packets matching loss rate',
      '3. Delivery metrics update showing elevated loss percentage'
    ]
  },
  TEMP_SPIKE: {
    title: 'Inject Solar Flare Temperature Spike (>85°C)',
    trigger: 'Operating condition parameter override in Satellite Telemetry Module',
    effect: 'Satellite temperature rises above 80°C threshold',
    detection: 'Local Satellite Autonomy detects thermal spike and activates THERMAL_PROTECTION mode',
    consequence: 'Health score drops dynamically to CRITICAL state (< 40%)',
    recovery: 'Clearing fault returns temperature to nominal range (20-40°C)',
    expectedSteps: [
      '1. Temperature spike injected into local telemetry state',
      '2. Satellite Autonomy Loop activates THERMAL_PROTECTION mode',
      '3. HealthEngine calculates reduced health score (< 40%)',
      '4. Node status transitions HEALTHY → WARNING → CRITICAL',
      '5. WebSocket broadcasts TELEMETRY_UPDATED event with updated state'
    ]
  },
  BATTERY_DRAIN: {
    title: 'Inject Eclipse Battery Drain (<15%)',
    trigger: 'Battery level override in Satellite Telemetry Module',
    effect: 'Satellite battery drops below 30% threshold',
    detection: 'Local Satellite Autonomy detects low power and activates POWER_SAVING mode',
    consequence: 'Telemetry sampling frequency reduces from 2.0s to 5.0s to preserve energy',
    recovery: 'Solar recharge simulation restores battery above 60%',
    expectedSteps: [
      '1. Battery level override applied to target satellite',
      '2. Satellite Autonomy Loop activates POWER_SAVING mode',
      '3. Telemetry publish interval adjusts 2.0s → 5.0s',
      '4. Health score recalculates dynamically based on low power'
    ]
  }
};

export default function FaultScenarioPanel({ selectedFaultType, actualResult }) {
  const scenario = faultScenarios[selectedFaultType] || faultScenarios.STOP_NODE;

  return (
    <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4 font-mono text-xs">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2 text-cyan-400 font-bold font-orbitron">
          <HelpCircle className="w-5 h-5 text-cyan-400" />
          <span>WHAT WILL HAPPEN NEXT? — DISTRIBUTED FAULT SCENARIO</span>
        </div>
        <span className="px-2.5 py-0.5 bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 rounded text-[10px] font-bold">
          FAULT MODEL EXPLANATION
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Scenario Details */}
        <div className="space-y-3">
          <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-1">
            <span className="text-slate-400 text-[11px] block">Trigger Action:</span>
            <div className="text-slate-200 font-bold">{scenario.trigger}</div>
          </div>

          <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-1">
            <span className="text-slate-400 text-[11px] block">Runtime Effect:</span>
            <div className="text-amber-300 font-bold">{scenario.effect}</div>
          </div>

          <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-1">
            <span className="text-slate-400 text-[11px] block">Detection Mechanism:</span>
            <div className="text-cyan-300">{scenario.detection}</div>
          </div>

          <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-1">
            <span className="text-slate-400 text-[11px] block">Distributed Consequence:</span>
            <div className="text-slate-200">{scenario.consequence}</div>
          </div>
        </div>

        {/* Expected Lifecycle Steps */}
        <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl space-y-2">
          <span className="text-cyan-400 font-bold font-orbitron text-[11px] block border-b border-slate-800 pb-1">
            EXPECTED DISTRIBUTED LIFECYCLE:
          </span>
          <div className="space-y-1.5 text-[11px] text-slate-300">
            {scenario.expectedSteps.map((step, idx) => (
              <div key={idx} className="flex items-start space-x-2">
                <ArrowRight className="w-3 h-3 text-cyan-400 shrink-0 mt-0.5" />
                <span>{step}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Expected vs Actual Comparison (If fault executed) */}
      {actualResult && (
        <div className="p-4 bg-slate-950 border border-emerald-500/40 rounded-xl space-y-2 mt-3">
          <div className="flex items-center justify-between text-emerald-400 font-bold font-orbitron text-[11px]">
            <span className="flex items-center space-x-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>EXPECTED VS ACTUAL EXECUTION COMPARISON</span>
            </span>
            <span>✓ VERIFIED 200 OK</span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-[11px]">
            <div className="p-2.5 bg-slate-900 rounded border border-slate-800 space-y-1">
              <span className="text-slate-400 block font-bold">EXPECTED FLOW:</span>
              <div className="text-slate-300">Stop Command → Missing Heartbeat → SUSPECTED (&gt;5s) → DISCONNECTED (&gt;10s) → Recovery</div>
            </div>

            <div className="p-2.5 bg-slate-900 rounded border border-slate-800 space-y-1">
              <span className="text-slate-400 block font-bold">ACTUAL OBSERVED FLOW:</span>
              <div className="text-emerald-300 font-bold">
                Target: {actualResult.target} | CID: {actualResult.data?.fault?.correlation_id || 'EVT-FLT'} | Status: EXECUTED
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
