# System Design Roadmap

## 1. Foundations
- What is system design (HLD vs LLD)
- Client-server model
- IP, DNS, HTTP/HTTPS basics
- OSI model (brief, practical relevance)
- APIs: REST, gRPC, GraphQL, WebSockets
- Latency vs throughput
- Reading and drawing basic architecture diagrams

## 2. Networking Basics
- TCP vs UDP
- DNS resolution flow
- CDN (Content Delivery Network)
- Load balancers (L4 vs L7)
- Reverse proxy vs forward proxy
- SSL/TLS handshake basics

## 3. Scalability Concepts
- Vertical vs horizontal scaling
- Stateless vs stateful services
- Load balancing algorithms (round robin, least connections, consistent hashing)
- Horizontal partitioning basics
- Auto-scaling

## 4. Databases
- SQL vs NoSQL — when to use which
- Types of NoSQL: key-value, document, column-family, graph
- Indexing (B-tree, hash index)
- Normalization vs denormalization
- ACID properties
- Transactions and isolation levels
- Database replication (master-slave, master-master)
- Sharding / partitioning strategies (range, hash, geo-based)
- Read/write replicas
- CAP theorem
- PACELC theorem

## 5. Caching
- Why and when to cache
- Cache placement (client, CDN, server, database)
- Caching strategies: write-through, write-back, write-around, cache-aside
- Cache eviction policies (LRU, LFU, FIFO)
- Distributed caching (Redis, Memcached)
- Cache invalidation strategies

## 6. Load Balancing & Proxies
- Load balancer types and placement
- Health checks
- Sticky sessions
- API Gateway concept

## 7. Data Consistency & Replication
- Strong vs eventual consistency
- Quorum-based consistency (read/write quorum)
- Conflict resolution (vector clocks, last-write-wins)
- Leader election basics

## 8. Message Queues & Asynchronous Processing
- Why async processing matters
- Message queue vs pub-sub
- Popular tools: Kafka, RabbitMQ, SQS (concepts, not just tool names)
- At-least-once vs at-most-once vs exactly-once delivery
- Dead-letter queues
- Event-driven architecture

## 9. Microservices & Architecture Patterns
- Monolith vs microservices vs modular monolith
- Service discovery
- Configuration & coordination services (Zookeeper, etcd, Consul)
- API Gateway pattern
- Circuit breaker pattern
- Saga pattern (distributed transactions)
- Event sourcing
- CQRS (Command Query Responsibility Segregation)
- Backend-for-frontend (BFF)
- Service mesh (sidecar pattern, Istio/Linkerd concepts)
- Serialization formats (Protobuf, Avro, Thrift) and why they matter for gRPC/Kafka
- Multi-tenancy (designing systems that serve multiple tenants/customers)

## 10. Storage Systems
- File storage vs block storage vs object storage
- Distributed file systems (concepts: GFS, HDFS)
- Blob storage (S3-like systems)
- CDN storage and caching for static assets

## 11. Scalability Building Blocks (Deep Dive)
- Consistent hashing (in depth)
- Bloom filters
- Rate limiting algorithms (token bucket, leaky bucket, sliding window)
- Idempotency and idempotency keys
- Data partitioning/sharding strategies revisited
- Hot key / hot partition problems

## 12. Distributed Systems Concepts
- Distributed consensus (Paxos, Raft — conceptual understanding)
- Leader election
- Heartbeats and failure detection
- Distributed locks
- Clock synchronization issues (logical clocks, vector clocks)
- Split-brain problem

## 13. Security in System Design
- Authentication vs authorization
- OAuth2 / JWT basics
- API rate limiting & throttling
- DDoS protection basics
- Data encryption (at rest, in transit)

## 14. API Design Deep Dive
- API versioning strategies
- Pagination (offset-based, cursor-based)
- Idempotency in APIs (idempotency keys)
- Rate-limit headers and client-facing throttling contracts

## 15. Monitoring & Reliability
- Logging, metrics, tracing (observability triad)
- Health checks and alerting
- SLA, SLO, SLI concepts
- Redundancy and failover
- Disaster recovery, backups
- Chaos engineering (basic concept)

## 16. Capacity Estimation & Back-of-envelope Math
- Estimating QPS, storage, bandwidth
- Reads vs writes ratio estimation
- Napkin math practice problems

## 17. Trade-off Thinking (Core Skill)
- Consistency vs availability trade-offs
- Latency vs cost trade-offs
- Push vs pull models
- Synchronous vs asynchronous communication
- Batch vs stream processing

## 18. Deployment, Infrastructure & Rollout Strategies
- Containers (Docker basics)
- Container orchestration (Kubernetes concepts)
- Feature flags
- Rollout strategies: canary release, blue-green deployment, A/B testing infrastructure
- Cost optimization at scale (storage tiering, compute cost trade-offs)

## 19. Multi-Region & Geo-Distributed Systems
- Active-active vs active-passive architectures
- Geo-replication
- Latency-based routing
- Backpressure handling in streaming/queue systems

## 20. Data Pipelines & Large-Scale Data Processing
- ETL basics (extract, transform, load)
- Batch processing frameworks (Spark-like concepts)
- Data lakes vs data warehouses

## 21. Testing at Scale
- Load testing
- Stress testing
- Chaos testing tools (distinct from chaos engineering concept in Monitoring & Reliability)

## 22. Classic System Design Case Studies (Practice After Fundamentals)
- URL shortener
- Rate limiter
- Design a chat application (WhatsApp-like)
- Design a news feed (Facebook/Twitter-like)
- Design a notification system
- Design a distributed cache
- Design an e-commerce checkout system
- Design a ride-sharing service (Uber-like)
- Design a video streaming service (YouTube/Netflix-like)
- Design a search autocomplete system
- Design a distributed job scheduler
- Design a payment system
- Design a web crawler

## 23. Low-Level Design (LLD) — Optional but Valuable
- OOP principles and SOLID principles
- Design patterns (Factory, Singleton, Observer, Strategy, etc.)
- UML basics (class diagrams, sequence diagrams)
- Designing classes for real-world systems (parking lot, elevator, library system)

## Suggested Learning Order
1. Foundations → Networking → Databases → Caching
2. Load balancing → Message queues → Microservices patterns
3. Distributed systems concepts → Security → API design → Monitoring
4. Capacity estimation → Trade-off thinking
5. Deployment & rollout strategies → Multi-region systems → Data pipelines → Testing at scale
6. Practice case studies (apply everything together)
7. LLD (parallel or after, depending on your goal — interviews often need both)