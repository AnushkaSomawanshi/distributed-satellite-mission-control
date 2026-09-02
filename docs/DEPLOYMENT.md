# Deployment, Virtualization & Containerization Architecture

A comprehensive operational manual detailing containerization, Docker Compose configuration, bridge network resolution, environment variables, and deployment procedures for the **Distributed Satellite Monitoring System**.

---

## 1. Deployment Overview

The platform is engineered to deploy seamlessly as **9 containerized microservices** using Docker Compose. Containerization eliminates environment configuration discrepancies, guarantees isolated Python runtimes, and provides virtualized bridge networks connecting satellites with Mission Control.

---

## 2. Why Docker Containerization is Used

1. **Microservice Environment Isolation**: Every satellite process (`SAT-01`..`SAT-05`) runs in an isolated Linux container with its own `asyncio` event loop and networking ports.
2. **Reproducible Multi-Service Topology**: Launches PostgreSQL, RabbitMQ, FastAPI Mission Control, React UI, and 5 satellites using a single declarative blueprint ([`docker-compose.yml`](../docker-compose.yml)).
3. **Internal Container DNS**: Docker Compose provides an internal DNS server resolving service names (`http://mission-control:8000`, `amqp://guest:guest@rabbitmq:5672/`).
4. **Controlled Failure Testing**: Allows stopping single containers (`docker compose stop satellite-02`) without affecting host OS processes.

---

## 3. Containers vs Virtual Machines

| Feature / Aspect | Docker Containers (This System) | Hardware Virtual Machines (Hypervisors) |
| :--- | :--- | :--- |
| **Isolation Level** | Operating System OS Kernel level process isolation | Full Hardware hypervisor emulation |
| **Startup Time** | Milliseconds (< 2 seconds) | Minutes (30 - 120 seconds) |
| **Resource Overhead** | Extremely lightweight (~50MB RAM per satellite) | Heavy (~1-2GB RAM per VM OS instance) |
| **Networking** | Virtual bridge networks (`ds-project_default`) | Virtual NICs & virtual switches |
| **Use Case Fit** | Ideal for microservice distributed systems testing | Ideal for running completely different operating systems |

---

## 4. Docker Compose Services Blueprint

The deployment topology consists of **9 services** declared in [`docker-compose.yml`](../docker-compose.yml):

```mermaid
graph TD
    subgraph Infrastructure
        PG["satellite-postgres<br/>(PostgreSQL 15)"]
        RMQ["satellite-rabbitmq<br/>(RabbitMQ 3.9)"]
    end

    subgraph Core Platform
        MC["mission-control-backend<br/>(FastAPI)"]
        UI["mission-control-frontend<br/>(React / Vite)"]
    end

    subgraph Satellites Constellation
        SAT1["satellite-01<br/>SAT_ID=SAT-01"]
        SAT2["satellite-02<br/>SAT_ID=SAT-02"]
        SAT3["satellite-03<br/>SAT_ID=SAT-03"]
        SAT4["satellite-04<br/>SAT_ID=SAT-04"]
        SAT5["satellite-05<br/>SAT_ID=SAT-05"]
    end

    MC -->|depends_on healthy| PG
    MC -->|depends_on healthy| RMQ
    SAT1 -->|depends_on| MC
    SAT2 -->|depends_on| MC
    SAT3 -->|depends_on| MC
    SAT4 -->|depends_on| MC
    SAT5 -->|depends_on| MC
    UI -->|depends_on| MC
```

---

## 5. Network Architecture & Port Mapping

| Service Name | Docker Container Name | Host Port | Container Port | Purpose / Protocol |
| :--- | :--- | :--- | :--- | :--- |
| **frontend** | `mission-control-frontend` | `3000` | `3000` | React UI Observability Dashboard |
| **mission-control** | `mission-control-backend` | `8000` | `8000` | FastAPI REST API & WebSockets `/ws` |
| **satellite-01** | `satellite-01` | `5001`, `6001` | `5001`, `6001` | `5001` gRPC Server \| `6001` P2P Cross-Link |
| **satellite-02** | `satellite-02` | `5002`, `6002` | `5002`, `6002` | `5002` gRPC Server \| `6002` P2P Cross-Link |
| **satellite-03** | `satellite-03` | `5003`, `6003` | `5003`, `6003` | `5003` gRPC Server \| `6003` P2P Cross-Link |
| **satellite-04** | `satellite-04` | `5004`, `6004` | `5004`, `6004` | `5004` gRPC Server \| `6004` P2P Cross-Link |
| **satellite-05** | `satellite-05` | `5005`, `6005` | `5005`, `6005` | `5005` gRPC Server \| `6005` P2P Cross-Link |
| **postgres** | `satellite-postgres` | `5432` | `5432` | PostgreSQL Database Server |
| **rabbitmq** | `satellite-rabbitmq` | `5672`, `15672`| `5672`, `15672`| `5672` AMQP Broker \| `15672` Mgmt Console |

---

## 6. Critical Docker Networking Concept

> ⚠️ **IMPORTANT DISTINCTION**:
> Inside the Docker network, containers communicate using **Docker Compose service names** rather than `localhost`.
> - Inside `frontend` container: Mission Control is `http://mission-control:8000` (NOT `localhost:8000`).
> - Inside `satellite-01` container: Registry URL is `http://mission-control:8000` (NOT `localhost:8000`).
> - On Host Browser: Frontend is accessed at `http://localhost:3000/`.

---

## 7. Environment Variables

| Variable Name | Applied Service | Configured Value | Purpose |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | `mission-control` | `postgresql+asyncpg://postgres:postgrespassword@postgres:5432/satellite_db` | Async SQLAlchemy database URL |
| `RABBITMQ_URL` | `mission-control` | `amqp://guest:guest@rabbitmq:5672/` | AMQP connection string |
| `SAT_ID` | `satellite-01`..`05` | `SAT-01` .. `SAT-05` | Unique satellite identity string |
| `SAT_ADDRESS` | `satellite-01`..`05` | `satellite-01` .. `satellite-05` | Docker DNS container address |
| `GRPC_PORT` | `satellite-01`..`05` | `5001` .. `5005` | gRPC server listening port |
| `P2P_PORT` | `satellite-01`..`05` | `6001` .. `6005` | Direct P2P HTTP listener port |
| `REGISTRY_URL` | `satellite-01`..`05` | `http://mission-control:8000` | Mission Control API address |
| `VITE_BACKEND_TARGET` | `frontend` | `http://mission-control:8000` | Vite proxy backend target |

---

## 8. Service Health Checks & Dependencies

To ensure Mission Control only starts after PostgreSQL and RabbitMQ are fully initialized:

```yaml
# docker-compose.yml dependency contract
mission-control:
  depends_on:
    postgres:
      condition: service_healthy
    rabbitmq:
      condition: service_healthy
```

- **PostgreSQL Healthcheck**: `pg_isready -U postgres` (Interval 5s).
- **RabbitMQ Healthcheck**: `rabbitmq-diagnostics -q ping` (Interval 10s).

---

## 9. Standard System Commands

### 1. Launch Full Stack (Rebuild & Start):
```powershell
docker compose down
docker compose up -d --build
```

### 2. Verify Active Services:
```powershell
docker compose ps
```

### 3. View Live Logs:
```powershell
# Tail Mission Control logs
docker compose logs -f mission-control

# Tail specific satellite logs
docker compose logs -f satellite-01
```

### 4. Failure & Recovery Simulation:
```powershell
# Stop satellite 02 (Simulate Crash)
docker compose stop satellite-02

# Restart satellite 02 (Simulate Autonomous Recovery)
docker compose start satellite-02
```

---

## 10. Troubleshooting Common Deployment Issues

### Issue 1: Port `8000` or `3000` Already Occupied
- **Cause**: Old Python or Node processes running locally outside Docker.
- **Solution**: Execute `docker compose down` and check for host processes using `netstat -ano | findstr :8000`. Stop host processes before running `docker compose up -d`.

### Issue 2: Frontend Displays Empty Tables (`ECONNREFUSED`)
- **Cause**: Vite proxy inside `mission-control-frontend` container attempting to target `localhost:8000`.
- **Solution**: Verify `VITE_BACKEND_TARGET=http://mission-control:8000` is set under `frontend` in `docker-compose.yml`.
