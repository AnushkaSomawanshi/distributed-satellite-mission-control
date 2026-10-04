# Cloud & Production Infrastructure Architecture Mapping

This document provides technical mapping of the local **MissionResilience** distributed architecture to production cloud environments, edge security providers, and dedicated interconnect networks.

---

## 1. AWS Cloud Infrastructure Mapping

| Local Component | Production AWS Service | Architectural Mapping & Deployment Strategy |
| :--- | :--- | :--- |
| **Mission Control Backend** | **AWS EKS (Elastic Kubernetes Service)** | FastAPI microservices deployed inside containerized EKS worker nodes across Multi-AZ subnets. |
| **Satellite Services (SAT-01..05)** | **AWS EC2 / EKS Edge** | Distributed nodes hosted on regional EC2 instances or AWS Outposts simulating satellite ground relays. |
| **Database** | **Amazon RDS PostgreSQL** | Multi-AZ relational storage for structured telemetry logs, task ownership, and incident events. |
| **Asynchronous Messaging** | **Amazon SQS / EventBridge** | Decoupled message queues replacing local RabbitMQ for asynchronous event notifications. |
| **Distributed Storage** | **Amazon S3 (Simple Storage Service)** | S3 Standard-IA buckets for historical telemetry archives, snapshots, and incident artifacts. |
| **Serverless Processing** | **AWS Lambda** | Event-driven Lambda triggers executing post-incident processing and report generation asynchronously. |
| **Monitoring & Metrics** | **Amazon CloudWatch** | Unified container logs, custom metrics, and alarm triggers. |

---

## 2. Cloudflare Edge Architecture Mapping

```text
Operator / User Browser
       │
       ▼
Cloudflare Edge Network (WAF + DDoS Protection)
       │
       ├─► Cloudflare CDN (Static React Assets)
       ├─► Cloudflare Access (Zero-Trust OAuth Authentication)
       │
       ▼
AWS ALB (Application Load Balancer)
       │
       ▼
Mission Control Backend Cluster
```

- **Cloudflare WAF**: Shields mission APIs against SQL injection, cross-site scripting, and automated bot attacks.
- **Cloudflare Access (Zero-Trust)**: Restricts access to Mission Control dashboard via OAuth 2.0 / SAML single sign-on.
- **Cloudflare Workers (Edge Compute)**: Evaluates light rate-limiting and GEO-routing before traffic hits origin.

---

## 3. Megaport Dedicated Interconnect Architecture

```text
On-Premises Ground Station / Satellite Gateway
       │
       ▼
Megaport Port (10Gbps Dedicated Direct Cross-Connect)
       │
       ├─► Megaport Cloud Router (MCR)
       │
       ▼
AWS Direct Connect (Private Virtual Interface) ──► VPC (Mission Control Backend)
```

- **Dedicated Private Connectivity**: Bypasses public internet latency for satellite ground station telemetry feeds.
- **Low Jitter & Packet Loss**: Guarantees predictable RTT for real-time beacon monitoring and clock synchronization.
