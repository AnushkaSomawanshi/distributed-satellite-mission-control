import React, { useState, useEffect } from 'react';
import { History, Play, Pause, SkipForward, SkipBack, RotateCcw, AlertTriangle, ShieldCheck } from 'lucide-react';

export default function IncidentConsolePage() {
  const [incidents, setIncidents] = useState([]);
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);

  const fetchIncidents = async () => {
    try {
      const res = await fetch('/api/incidents');
      const data = await res.json();
      const incList = data.incidents || [];
      setIncidents(incList);
      if (incList.length > 0 && !selectedIncident) {
        loadIncident(incList[0].incident_id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const loadIncident = async (id) => {
    try {
      const res = await fetch(`/api/incidents/${id}`);
      const data = await res.json();
      setSelectedIncident(data);
      setCurrentStep(0);
      setIsPlaying(false);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchIncidents();
  }, []);

  useEffect(() => {
    let interval;
    if (isPlaying && selectedIncident && selectedIncident.event_timeline) {
      interval = setInterval(() => {
        setCurrentStep((prev) => {
          if (prev < selectedIncident.event_timeline.length - 1) {
            return prev + 1;
          } else {
            setIsPlaying(false);
            return prev;
          }
        });
      }, 2000 / playbackSpeed);
    }
    return () => clearInterval(interval);
  }, [isPlaying, selectedIncident, playbackSpeed]);

  const timeline = selectedIncident?.event_timeline || [];
  const activeEvent = timeline[currentStep] || {};

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold font-orbitron text-slate-100 flex items-center space-x-2">
            <History className="w-5 h-5 text-cyan-400" />
            <span>Distributed Incident Console & Timeline Replay</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Persisted multi-step timeline player for failure detection, ring election, mutex claims, and task reassignment.
          </p>
        </div>
      </div>

      {/* Incident Selection & Controls */}
      <div className="glass-panel p-5 rounded-xl border border-slate-800/80 space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-4 font-mono text-xs">
          <div className="flex items-center space-x-3">
            <span className="text-slate-400">Select Incident:</span>
            <select
              value={selectedIncident?.incident_id || ''}
              onChange={(e) => loadIncident(e.target.value)}
              className="bg-slate-900 border border-slate-700 text-slate-200 rounded px-3 py-1.5 font-bold"
            >
              {incidents.map((inc) => (
                <option key={inc.incident_id} value={inc.incident_id}>
                  {inc.incident_id} - {inc.title}
                </option>
              ))}
            </select>
          </div>

          {/* Player Controls */}
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setCurrentStep(0)}
              className="p-2 bg-slate-900 hover:bg-slate-800 text-slate-300 rounded border border-slate-800"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
            <button
              onClick={() => setCurrentStep((prev) => Math.max(0, prev - 1))}
              className="p-2 bg-slate-900 hover:bg-slate-800 text-slate-300 rounded border border-slate-800"
            >
              <SkipBack className="w-4 h-4" />
            </button>
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold rounded-lg flex items-center space-x-2 transition-all glow-cyan"
            >
              {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              <span>{isPlaying ? 'Pause' : 'Play Replay'}</span>
            </button>
            <button
              onClick={() => setCurrentStep((prev) => Math.min(timeline.length - 1, prev + 1))}
              className="p-2 bg-slate-900 hover:bg-slate-800 text-slate-300 rounded border border-slate-800"
            >
              <SkipForward className="w-4 h-4" />
            </button>
            <select
              value={playbackSpeed}
              onChange={(e) => setPlaybackSpeed(Number(e.target.value))}
              className="bg-slate-900 border border-slate-700 text-slate-300 rounded px-2 py-1 font-bold"
            >
              <option value={1}>1x Speed</option>
              <option value={2}>2x Speed</option>
              <option value={5}>5x Speed</option>
            </select>
          </div>
        </div>

        {/* Progress Bar */}
        {timeline.length > 0 && (
          <div className="space-y-1">
            <div className="flex justify-between text-[11px] font-mono text-slate-400">
              <span>Step {currentStep + 1} of {timeline.length}</span>
              <span>{activeEvent.timestamp ? new Date(activeEvent.timestamp * 1000).toLocaleTimeString() : ''}</span>
            </div>
            <div className="w-full bg-slate-900 rounded-full h-2 overflow-hidden border border-slate-800">
              <div
                className="bg-cyan-400 h-full transition-all duration-300"
                style={{ width: `${((currentStep + 1) / timeline.length) * 100}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Active Step Details */}
      {activeEvent && (
        <div className="glass-panel p-5 rounded-xl border border-cyan-500/30 space-y-3 font-mono text-xs">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="font-bold text-cyan-300">Active Replay Event Step: {activeEvent.event_type || 'INCIDENT_STEP'}</span>
            <span className="text-emerald-400 font-bold">Lamport T={activeEvent.lamport_timestamp || 1}</span>
          </div>
          <div className="text-slate-300 font-semibold">{activeEvent.message || activeEvent.description || 'Executing incident recovery step.'}</div>
          <div className="p-3 bg-slate-900 rounded border border-slate-800 text-slate-400 font-mono text-[11px]">
            Payload: {JSON.stringify(activeEvent.payload || activeEvent, null, 2)}
          </div>
        </div>
      )}
    </div>
  );
}
