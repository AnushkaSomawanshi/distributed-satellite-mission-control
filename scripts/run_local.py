import sys
import os
import time
import subprocess
import signal

def main():
    print("=" * 70)
    print("🚀 DISTRIBUTED SATELLITE CONSTELLATION - LOCAL PROCESS LAUNCHER")
    print("=" * 70)
    print("Starting Mission Control Backend & 5 Independent Satellite Nodes...")

    python_exe = sys.executable
    processes = []

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
        print("✅ ALL 5 SATELLITES & MISSION CONTROL RUNNING!")
        print("   Mission Control REST API: http://127.0.0.1:8000/api/satellites")
        print("   Mission Control Swagger:  http://127.0.0.1:8000/docs")
        print("   React Frontend (Dev):     http://localhost:3000")
        print("Press Ctrl+C to terminate all processes.")
        print("=" * 70 + "\n")

        for proc in processes:
            proc.wait()

    except KeyboardInterrupt:
        print("\nTerminating all distributed satellite processes...")
        for proc in processes:
            proc.terminate()
        print("All processes stopped safely.")

if __name__ == "__main__":
    main()
