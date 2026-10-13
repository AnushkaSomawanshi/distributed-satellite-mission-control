import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import SatelliteDetailModal from './components/SatelliteDetailModal';
import EventTraceDrawer from './components/EventTraceDrawer';

import MissionOverview from './pages/MissionOverview';
import ConstellationMap from './pages/ConstellationMap';
import CommunicationObservatory from './pages/CommunicationObservatory';
import CommunicationReplay from './pages/CommunicationReplay';
import DistributedConcepts from './pages/DistributedConcepts';
import FaultSimulatorPage from './pages/FaultSimulatorPage';
import SatelliteRegistryPage from './pages/SatelliteRegistryPage';
import LiveTelemetryPage from './pages/LiveTelemetryPage';
import MultimediaPage from './pages/MultimediaPage';
import MiddlewarePage from './pages/MiddlewarePage';
import SystemHealthDemo from './pages/SystemHealthDemo';
import RuntimeObservabilityPage from './pages/RuntimeObservabilityPage';

import MissionTasksPage from './pages/MissionTasksPage';
import ClockSyncPage from './pages/ClockSyncPage';
import RingElectionPage from './pages/RingElectionPage';
import MutexManagerPage from './pages/MutexManagerPage';
import GlobalSnapshotPage from './pages/GlobalSnapshotPage';
import IncidentConsolePage from './pages/IncidentConsolePage';
import FailureIntelligencePage from './pages/FailureIntelligencePage';
import ExperimentLabPage from './pages/ExperimentLabPage';
import PartitionReconciliationPage from './pages/PartitionReconciliationPage';


export default function App() {
  const [satellites, setSatellites] = useState([]);
  const [systemHealth, setSystemHealth] = useState({});
  const [observatoryStats, setObservatoryStats] = useState({});
  const [activeFaults, setActiveFaults] = useState([]);
  const [telemetryHistory, setTelemetryHistory] = useState([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [selectedSatForModal, setSelectedSatForModal] = useState(null);
  const [activeCorrelationId, setActiveCorrelationId] = useState(null);

  // Fetch initial satellite data & health
  const fetchSatelliteData = async () => {
    try {
      const res = await fetch('/api/satellites');
      const data = await res.json();
      const satList = data.satellites || [];
      setSatellites(satList);

      // Historical chart points are created only from validated WebSocket observations.
      // The registry snapshot is current state, not historical telemetry.
    } catch (e) {}

    try {
      const res = await fetch('/api/health');
      const data = await res.json();
      setSystemHealth(data);
    } catch (e) {}

    try {
      const res = await fetch('/api/observatory/stats');
      const data = await res.json();
      setObservatoryStats(data);
    } catch (e) {}

    try {
      const res = await fetch('/api/faults');
      const data = await res.json();
      setActiveFaults(data.active_faults || []);
    } catch (e) {}
  };

  useEffect(() => {
    fetchSatelliteData();
    const timer = setInterval(fetchSatelliteData, 3000);
    return () => clearInterval(timer);
  }, []);

  // Live WebSocket Connection
  useEffect(() => {
    let ws;
    let reconnectTimer;
    let disposed = false;
    const connectWS = () => {
      if (disposed) return;
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws`;
      ws = new WebSocket(wsUrl);

      ws.onopen = () => setWsConnected(true);
      ws.onclose = () => {
        setWsConnected(false);
        if (!disposed) reconnectTimer = setTimeout(connectWS, 3000);
      };
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          
          if (['FAULT_INJECTED', 'FAULTS_CLEARED', 'SATELLITE_STATUS_CHANGED', 'LEADER_ELECTION_COMPLETED', 'HEARTBEAT_TIMEOUT', 'NODE_SUSPECTED', 'NODE_DISCONNECTED', 'TASK_REASSIGNED', 'MUTEX_REQUEST_PROCESSED', 'SNAPSHOT_COMPLETED', 'AUTONOMOUS_REALLOCATION_COMPLETED'].includes(msg.event_type)) {
            fetchSatelliteData();
          }

          if (msg.event_type === 'TELEMETRY_UPDATED') {
            const telemetry = msg.telemetry?.data || msg.telemetry || {};
            const satId = telemetry.satellite_id;
            const requiredMeasurements = ['battery', 'temperature', 'cpu_usage', 'memory_usage', 'signal_strength'];
            const validMeasurements = requiredMeasurements.every((key) =>
              Number.isFinite(Number(telemetry[key])) && telemetry[key] !== null && telemetry[key] !== undefined
            );
            if (satId && validMeasurements) {
              const timeStr = new Date(Number(telemetry.timestamp || msg.timestamp || Date.now() / 1000) * 1000).toLocaleTimeString();
              setTelemetryHistory((prev) => {
                const lastPoint = prev.length > 0 ? { ...prev[prev.length - 1} } : {};
                const newPoint = {
                  ...lastPoint,
                  time: timeStr,
                  [`${satId}_battery`]: Number(telemetry.battery),
                  [`${satId}_temp`]: Number(telemetry.temperature),
                  [`${satId}_cpu`]: Number(telemetry.cpu_usage),
                };
                if (telemetry.health_score !== null && telemetry.health_score !== undefined && Number.isFinite(Number(telemetry.health_score))) {
                  newPoint[`${satId}_health`] = Number(telemetry.health_score);
                }
                const next = [...prev, newPoint];
                if (next.length > 35) next.shift();
                return next;
              });
            }
          }
        } catch (e) {}
      };
    };

    connectWS();
    return () => {
      disposed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws) ws.close();
      setWsConnected(false);
    };
  }, []);

  return (
    <Router>
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
        <Header systemHealth={systemHealth} wsConnected={wsConnected} />
        <div className="flex flex-1">
          <Sidebar />
          <main className="flex-1 min-w-0 p-4 overflow-y-auto">
            <Routes>
              <Route path="/" element={<MissionOverview satellites={satellites} observatoryStats={observatoryStats} wsConnected={wsConnected} onSelectSatellite={setSelectedSatForModal} onSelectCorrelationId={setActiveCorrelationId} />} />
              <Route path="/tasks" element={<MissionTasksPage />} />
              <Route path="/clocks" element={<ClockSyncPage />} />
              <Route path="/ring-election" element={<RingElectionPage />} />
              <Route path="/mutex" element={<MutexManagerPage />} />
              <Route path="/snapshots" element={<GlobalSnapshotPage />} />
              <Route path="/failure-intelligence" element={<FailureIntelligencePage />} />
              <Route path="/incidents" element={<IncidentConsolePage />} />
              <Route path="/experiments" element={<ExperimentLabPage />} />
              <Route path="/partition" element={<PartitionReconciliationPage />} />

              <Route path="/topology" element={<ConstellationMap satellites={satellites} />} />
              <Route path="/observatory" element={<CommunicationObservatory observatoryStats={observatoryStats} onSelectCorrelationId={setActiveCorrelationId} />} />
              <Route path="/replay" element={<CommunicationReplay />} />
              <Route path="/concepts" element={<DistributedConcepts />} />
              <Route path="/faults" element={<FaultSimulatorPage satellites={satellites} activeFaults={activeFaults} onSelectCorrelationId={setActiveCorrelationId} />} />
              <Route path="/registry" element={<SatelliteRegistryPage satellites={satellites} onRefresh={fetchSatelliteData} onSelectSatellite={setSelectedSatForModal} />} />
              <Route path="/telemetry" element={<LiveTelemetryPage telemetryHistory={telemetryHistory} satellites={satellites} wsConnected={wsConnected} />} />
              <Route path="/multimedia" element={<MultimediaPage />} />
              <Route path="/middleware" element={<MiddlewarePage />} />
              <Route path="/demo-center" element={<SystemHealthDemo />} />
              <Route path="/runtime-observability" element={<RuntimeObservabilityPage />} />
            </Routes>
          </main>
        </div>

        {/* Global Modals & Event Trace Drawer */}
        <SatelliteDetailModal
          isOpen={!!selectedSatForModal}
          onClose={() => setSelectedSatForModal(null)}
          satellite={selectedSatForModal}
        />

        <EventTraceDrawer
          isOpen={!!activeCorrelationId}
          onClose={() => setActiveCorrelationId(null)}
          correlationId={activeCorrelationId}
        />
      </div>
    </Router>
  );
}

