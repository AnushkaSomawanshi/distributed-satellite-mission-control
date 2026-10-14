# Unit 4 case studies mapped onto OrbitTrack

Two case studies are implemented in this repository (Apache Hadoop, Kubernetes); the other three are
mapped onto the architecture so it is clear how the system would run on those platforms.

| Case study | What it is | Implemented / mapped here |
|---|---|---|
| **Apache Hadoop** | HDFS: a NameNode holds metadata, DataNodes hold 3 replicas of every block, pipeline writes, re-replication. MapReduce: data-local map tasks, combiner, shuffle, reduce, task re-execution | **Implemented.** OrbitFS = NameNode in Mission Control + DataNodes on the satellites (`backend/fa2/orbitfs.py`, `satellites/dsync/datanode.py`); MapReduce JobTracker schedules map tasks on satellites that hold the chunk, reducers are satellites, failed attempts re-run on another replica (`backend/fa2/mapreduce.py`) |
| **Kubernetes** | Declarative deployments, StatefulSets with stable identity, services, liveness/readiness probes, self-healing | **Implemented.** `k8s/`: satellites as a StatefulSet (pod `satellite-N` → `SAT-0N+1`, stable DNS), Mission Control primary + standby, Nginx gateway (NodePort 30080), RabbitMQ. Demo contrasts Kubernetes recreating a pod with the satellites' own election and task takeover |
| **AWS** | AWS Ground Station (antenna time as a service), IoT Core (device telemetry), Lambda (functions), S3 (objects), DynamoDB (key-value), ELB | **Mapped.** Ground Station ≈ the satellite→ground link; IoT Core ≈ RabbitMQ telemetry ingestion; Lambda ≈ the serverless runtime; S3 ≈ OrbitFS; DynamoDB ≈ the task table / status board; ELB ≈ the Nginx gateway |
| **Cloudflare** | Anycast edge network, edge caching, Workers (functions at 300+ locations) | **Mapped.** Ground stations as edge points of presence: the gateway's micro-cache and the serverless functions would run at the edge, close to operators and ground antennas |
| **Megaport** | Software-defined network-as-a-service: private virtual cross-connects between data centres and clouds on demand | **Mapped.** Private links between ground stations and cloud regions, so telemetry and commands never cross the public internet; capacity provisioned per contact window |
