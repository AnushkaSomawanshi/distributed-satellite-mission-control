import sys
import os
import time
import subprocess
import signal
import atexit
import socket

processes = []

def free_target_ports(ports):
    """Pre-flight check: Frees any stale lingering processes occupying project ports."""
    for port in ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                if s.connect_ex(('127.0.0.1', port)) == 0:
                    print(f"⚠️ Port {port} is occupied. Cleaning lingering stale process...")
                    if os.name == 'nt':
                        cmd = f'for /f "tokens=5" %a in (\'netstat -aon ^| findstr :{port}\') do taskkill /F /PID %a'
                        subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    time.sleep(0.5)
        except Exception:
            pass

def cleanup():
    """Guarantees forceful process-tree termination of all spawned child processes."""
    if not processes:
        return
    print("\n" + "=" * 70)
    print("🧹 CLEANING UP DISTRIBUTED SYSTEM PROCESSES...")
    print("=" * 70)
    
    for proc in processes:
        if proc.poll() is None:
            pid = proc.pid
            try:
                if os.name == 'nt':
                    # On Windows, taskkill /F /T /PID kills the process and all child threads/subprocesses
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    proc.terminate()
                    try:
                        proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        proc.kill()
            except Exception as e:
                print(f"Error terminating PID {pid}: {e}")

    time.sleep(1)
    print("✅ All satellite microservices & Mission Control stopped cleanly.")
    print("   Ports 8000, 5001-5005, and 6001-6005 released.")
    print("=" * 70 + "\n")

# Register cleanup on python exit and OS signals
atexit.register(cleanup)

def signal_handler(sig, frame):
    cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
if hasattr(signal, 'SIGTERM'):
    signal.signal(signal.SIGTERM, signal_handler)

def main():
    print("=" * 70)
    print("[DISTRIBUTED SATELLITE CONSTELLATION - LOCAL PROCESS LAUNCHER]")
    print("=" * 70)
    print("Starting Mission Control Backend & 5 Independent Satellite Nodes...")

    python_exe = sys.executable
    target_ports = [8000, 5001, 5002, 5003, 5004, 5005, 6001, 6002, 6003, 6004, 6005]
    
    # 0. Pre-flight check: ensure clean ports
    free_target_ports(target_ports)

    try:
        # 1. Launch Mission Control Backend
        print("[1/6] Launching Mission Control Backend (Port 8000)...")
        mc_proc = subprocess.Popen([
            python_exe, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"
        ])
        processes.append(mc_proc)
        time.sleep(3) # Wait for backend startup

        # 2. Launch 5 Independent Satellite Nodes
        satellites_config = [
            {"id": "SAT-01", "grpc": 5001, "p2p": 6001},
            {"id": "SAT-02", "grpc": 5002, "p2p": 6002},
            {"id": "SAT-03", "grpc": 5003, "p2p": 6003},
            {"id": "SAT-04", "grpc": 5004, "p2p": 6004},
            {"id": "SAT-05", "grpc": 5005, "p2p": 6005},
        ]

        for i, sat in enumerate(satellites_config, start=2):
            print(f"[{i}/6] Launching {sat['id']} (gRPC: {sat['grpc']}, P2P: {sat['p2p']})...")
            sat_proc = subprocess.Popen([
                python_exe, "satellites/satellite_node.py",
                "--id", sat["id"],
                "--grpc-port", str(sat["grpc"]),
                "--p2p-port", str(sat["p2p"]),
                "--registry", "http://127.0.0.1:8000"
            ])
            processes.append(sat_proc)

        print("\n" + "=" * 70)
        print("[SUCCESS] ALL 5 SATELLITES & MISSION CONTROL RUNNING!")
        print("   Mission Control REST API: http://127.0.0.1:8000/api/satellites")
        print("   Mission Control Swagger:  http://127.0.0.1:8000/docs")
        print("   React Frontend (Dev):     http://localhost:3000")
        print("   [NOTE: Do NOT run 'docker compose up' while run_local.py is active]")
        print("Press Ctrl+C to terminate all processes cleanly.")
        print("=" * 70 + "\n")

        while True:
            time.sleep(1)

    except (KeyboardInterrupt, SystemExit):
        cleanup()

if __name__ == "__main__":
    main()
