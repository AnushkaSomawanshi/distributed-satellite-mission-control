import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Header from './components/Header';
import Sidebar from './components/Sidebar';

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
import TeacherQuestionsPage from './pages/TeacherQuestionsPage';

export default function App() {
  const [satellites, setSatellites] = useState([]);
  const [systemHealth, setSystemHealth] = useState({});
  const [observatoryStats, setObservatoryStats] = useState({});
  const [activeFaults, setActiveFaults] = useState([]);
  const [telemetryHistory, setTelemetryHistory] = useState([]);
  const [wsConnected, setWsConnected] = useState(false);

  // Fetch initial satellite data & health
  const fetchSatelliteData = async () => {
    try {
      const res = await fetch('/api/satellites');
      const data = await res.json();
      const satList = data.satellites || [];
      setSatellites(satList);

      // Seed initial baseline telemetry points if history is empty
      setTelemetryHistory((prev) => {
        if (prev.length < 3 && satList.length > 0) {
          const now = new Date();
          const basePoints = [];
          for (let i = 4; i >= 0; i--) {
            const pointTime = new Date(now.getTime() - i * 3000).toLocaleTimeString();
            const pt = { time: pointTime };
            satList.forEach((s) => {
              pt[`${s.satellite_id}_battery`] = Number(s.battery || 95);
              pt[`${s.satellite_id}_temp`] = Number(s.temperature || 25);
              pt[`${s.satellite_id}_cpu`] = Number(s.cpu_usage || 15);
              pt[`${s.satellite_id}_health`] = Number(s.health_score || 100);
            });
            basePoints.push(pt);
          }
          return basePoints;
        }
        return prev;
      });
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
    const connectWS = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws`;
      ws = new WebSocket(wsUrl);

      ws.onopen = () => setWsConnected(true);
      ws.onclose = () => {
        setWsConnected(false);
        setTimeout(connectWS, 3000);
      };
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          
          // Instantly sync satellite state across all pages on event broadcasts
          if (['FAULT_INJECTED', 'FAULTS_CLEARED', 'SATELLITE_STATUS_CHANGED', 'LEADER_ELECTION_COMPLETED', 'HEARTBEAT_TIMEOUT'].includes(msg.event_type)) {
            fetchSatelliteData();
          }

          if (msg.event_type === 'TELEMETRY_UPDATED') {
            const telemetry = msg.telemetry?.data || msg.telemetry || {};
            const satId = telemetry.satellite_id;
            if (satId) {
              const timeStr = new Date().toLocaleTimeString();
              setTelemetryHistory((prev) => {
                const lastPoint = prev.length > 0 ? { ...prev[prev.length - 1] } : {};
                const newPoint = {
                  ...lastPoint,
                  time: timeStr,
                  [`${satId}_battery`]: Number(telemetry.battery),
                  [`${satId}_temp`]: Number(telemetry.temperature),
                  [`${satId}_cpu`]: Number(telemetry.cpu_usage),
                  [`${satId}_health`]: Number(telemetry.health_score || 100)
                };
                const next = [...prev, newPoint];
                if (next.length > 35) next.shift(); // 35 sample rolling window
                return next;
              });
            }
          }
        } catch (e) {}
      };
    };

    connectWS();
    return () => ws && ws.close();
  }, []);

  return (
    <Router>
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
        <Header systemHealth={systemHealth} wsConnected={wsConnected} />
        <div className="flex flex-1">
          <Sidebar />
          <main className="flex-1 p-6 overflow-y-auto">
            <Routes>
              <Route path="/" element={<MissionOverview satellites={satellites} observatoryStats={observatoryStats} />} />
              <Route path="/topology" element={<ConstellationMap satellites={satellites} />} />
              <Route path="/observatory" element={<CommunicationObservatory observatoryStats={observatoryStats} />} />
              <Route path="/replay" element={<CommunicationReplay />} />
              <Route path="/concepts" element={<DistributedConcepts />} />
              <Route path="/faults" element={<FaultSimulatorPage satellites={satellites} activeFaults={activeFaults} />} />
              <Route path="/registry" element={<SatelliteRegistryPage satellites={satellites} onRefresh={fetchSatelliteData} />} />
              <Route path="/telemetry" element={<LiveTelemetryPage telemetryHistory={telemetryHistory} satellites={satellites} />} />
              <Route path="/multimedia" element={<MultimediaPage />} />
              <Route path="/middleware" element={<MiddlewarePage />} />
              <Route path="/demo-center" element={<SystemHealthDemo />} />
              <Route path="/teacher-questions" element={<TeacherQuestionsPage />} />
            </Routes>
          </main>
        </div>
      </div>
    </Router>
  );
}
