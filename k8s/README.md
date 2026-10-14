# Running OrbitTrack on Kubernetes (kind or minikube)

| File | What it creates |
|---|---|
| `00-namespace-config.yaml` | Namespace `orbital-mission`, shared configuration |
| `10-rabbitmq.yaml` | RabbitMQ broker |
| `20-mission-control.yaml` | Mission Control primary + warm standby, shared volume for OrbitFS metadata |
| `30-gateway.yaml` | Nginx gateway (frontend + API), NodePort 30080 |
| `40-satellites.yaml` | The 5 satellites as a **StatefulSet** with a headless service |

## Build images and deploy (kind)

```powershell
kind create cluster --name orbit
docker build -t orbittrack-backend:latest   -f docker/Dockerfile.backend .
docker build -t orbittrack-satellite:latest -f docker/Dockerfile.satellite .
docker build -t orbittrack-gateway:latest   -f docker/Dockerfile.gateway .
kind load docker-image orbittrack-backend:latest orbittrack-satellite:latest orbittrack-gateway:latest --name orbit
kubectl apply -f k8s/
kubectl -n orbital-mission get pods -w
kubectl -n orbital-mission port-forward svc/gateway 8080:80     # then open http://localhost:8080
```

## Demo: infrastructure recovery vs application recovery

```powershell
kubectl -n orbital-mission get pods -l app=satellite -o wide
kubectl -n orbital-mission delete pod satellite-4          # SAT-05, usually the leader
kubectl -n orbital-mission get pods -l app=satellite -w      # Kubernetes recreates satellite-4 with the same name
```

- **Kubernetes** (infrastructure level): the StatefulSet recreates `satellite-4` with the same name, DNS
  name and therefore the same satellite identity `SAT-05`. The liveness probe restarts a hung process.
- **The application** (Unit 3 level): while the pod is gone, the other satellites' beacons declare
  SAT-05 dead, they elect a new leader and the new leader takes over SAT-05's tasks; OrbitFS copies its
  chunks to other satellites. When SAT-05 is back it is a new process: it registers again, holds a Bully
  election and receives no stale tasks.

Kubernetes keeps the right number of processes running; the distributed algorithms keep the system
correct while one is missing.

## Notes

- Satellites register their stable DNS name (`satellite-N.satellite.orbital-mission.svc.cluster.local`),
  so peers and Mission Control reach them directly for P2P, OrbitFS and Pyro calls.
- Mission Control uses SQLite inside the pod here (the task table only mirrors satellite state).
- Validate the manifests offline: `pip install kubernetes-validate` then
  `kubernetes-validate -k 1.29.0 --strict k8s/*.yaml`.
