<post>
Out of AWS's 200+ services, maybe 12 actually show up in the work. Lambda, S3, DynamoDB, RDS/Aurora, SQS, SNS, VPC, API Gateway, CloudFront, IAM, ElastiCache, CloudWatch. That's it. The rest are either niche, situational, or just the same problem with a different name.

This isn't a hot take, it's just what happens when you look at what gets used across most backend and full-stack systems. An event-driven API? Lambda behind API Gateway, DynamoDB or Aurora depending on your query complexity, SQS if you need decoupling, CloudFront if you're caching at the edge. Add IAM to tie permissions together and CloudWatch so you know when things break. That covers an enormous amount of ground.

The services people spend the most time agonizing over — EKS, Kinesis, Redshift, Glue — they matter, but they matter in context. You reach for Kinesis when you genuinely need ordered, high-volume streaming with replay. You reach for EKS when your team already knows Kubernetes and the complexity tradeoff is worth it. Most of the time, those conditions don't apply.

What actually takes time isn't learning the services, it's learning the decision layer underneath them. When does DynamoDB make you pay later for choices you made on day one? When does Lambda's 15-minute ceiling become a real constraint versus a theoretical one? When is the SNS-to-multiple-SQS fan-out pattern the right call versus just wiring things directly?

That part doesn't compress into a list. But starting with the 12 services that actually matter gets you 80% of the way to being useful in a system design conversation, and that's a reasonable place to start.

## AWS Core Services Architecture Diagram

```mermaid
graph TB
    %% Client Layer
    Client[Client Applications] --> CF[CloudFront CDN]
    
    %% API Layer
    CF --> GW[API Gateway]
    GW --> Lambda[AWS Lambda Functions]
    
    %% Processing Layer
    Lambda --> DB[(Database Layer)]
    Lambda --> SQS[SQS Queue]
    Lambda --> Cache[ElastiCache]
    
    %% Database Layer
    subgraph "Database Choice"
        DB --> DynamoDB[(DynamoDB)]
        DB --> RDS[(RDS/Aurora)]
    end
    
    %% Messaging Layer
    SQS --> SNS[SNS Topics]
    SNS --> SQS2[Multiple SQS Queues]
    
    %% Infrastructure Layer
    subgraph "Network Infrastructure"
        VPC[VPC Networking]
        IAM[IAM Permissions]
    end
    
    %% Monitoring
    subgraph "Monitoring & Observability"
        CW[CloudWatch]
    end
    
    %% Connections
    VPC -.-> Lambda
    VPC -.-> GW
    VPC -.-> DB
    VPC -.-> SQS
    VPC -.-> Cache
    
    IAM -.-> Lambda
    IAM -.-> GW
    IAM -.-> DB
    IAM -.-> SQS
    IAM -.-> SNS
    IAM -.-> CF
    
    CW -.-> Lambda
    CW -.-> GW
    CW -.-> DB
    CW -.-> SQS
    CW -.-> SNS
    CW -.-> CF
    
    %% Styling
    classDef coreServices fill:#ff6b6b,stroke:#c92a2a,color:#fff
    classDef infrastructure fill:#4dabf7,stroke:#1864ab,color:#fff
    classDef monitoring fill:#51cf66,stroke:#2f9e44,color:#fff
    classDef database fill:#ff922b,stroke:#e8590c,color:#fff
    
    class Lambda,GW,SQS,SNS,CF,Cache coreServices
    class DynamoDB,RDS database
    class VPC,IAM infrastructure
    class CW monitoring
```

</post>