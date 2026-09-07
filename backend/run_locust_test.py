"""
FarCast DB v2 — Automated Locust Load Test & Performance Reporter
Launches live server, executes headless Locust benchmark, and outputs performance metrics.
"""
import sys
import time
import subprocess
import threading
from app import app
import uvicorn

def run_benchmark():
    print("\n======================================================================")
    print("[LOCUST BENCHMARK] FARCAST DB v2 HIGH-CONCURRENCY LOAD TEST")
    print("======================================================================\n")

    # Start FastAPI server in background thread
    server_thread = threading.Thread(
        target=uvicorn.run,
        args=(app,),
        kwargs={"host": "127.0.0.1", "port": 5052, "log_level": "error"},
        daemon=True
    )
    # Wait for server readiness probe
    print("  Waiting for server initialization and cache readiness at http://127.0.0.1:5052/health/ready...")
    import requests
    ready = False
    for _ in range(60):
        try:
            r = requests.get("http://127.0.0.1:5052/health/ready", timeout=2)
            if r.status_code == 200 and r.json().get("status") == "ready":
                ready = True
                break
        except Exception:
            pass
        time.sleep(1)

    if not ready:
        print("  [ERROR] Server failed readiness check within timeout.")
        return

    print("  Server active and ready on http://127.0.0.1:5052. Launching Locust benchmark...")
    print("  Simulating 50 Concurrent Users (Hatch Rate: 10 users/sec, Duration: 20s)\n")


    # Run Locust CLI
    cmd = [
        sys.executable, "-m", "locust",
        "-f", "locustfile.py",
        "--headless",
        "-u", "50",
        "-r", "10",
        "--run-time", "20s",
        "--host", "http://127.0.0.1:5052",
        "--csv", "locust_results"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)

if __name__ == "__main__":
    run_benchmark()
