# Architecture

## Local Architecture

```mermaid
flowchart TD
    Operator["Operator"] --> Dashboard["Streamlit dashboard"]
    Client["API client"] --> API["FastAPI"]
    Dashboard --> API
    API --> Keys["Local users and hashed API keys"]
    API --> Ingestion["Document ingestion"]
    API --> Query["Query service"]
    Ingestion --> Parser["Markdown parser"]
    Parser --> Chunks["Chunking"]
    Chunks --> SQLite["SQLite documents and chunks"]
    Query --> RBAC["Role-based candidate filter"]
    RBAC --> Retriever["Lexical retriever"]
    Retriever --> Generator["Mock answer generator"]
    Generator --> Citations["Answer and citations"]
    Query --> Logs["Query logs"]
    Logs --> SQLite
    Eval["Evaluation runner"] --> Query
```

The local architecture intentionally avoids cloud dependencies. Documents are markdown files with metadata front matter, SQLite stores metadata and chunks, and deterministic retrieval keeps validation reproducible. The dashboard is API-backed and does not read the database directly, so the same UI boundary can be retained for container or Azure deployment.

## Azure-Ready Architecture

```mermaid
flowchart TD
    User["Employee"] --> Entra["Microsoft Entra ID"]
    Entra --> App["Container Apps service"]
    App --> Search["Azure AI Search"]
    App --> OpenAI["Azure OpenAI"]
    App --> DB["Azure PostgreSQL or Cosmos DB"]
    App --> Blob["Azure Blob Storage"]
    App --> Insights["Application Insights"]
    KeyVault["Azure Key Vault"] --> App
    Blob --> Indexer["Ingestion worker"]
    Indexer --> Search
```

Cloud services are activated by environment configuration. Local mode remains the default runtime, while Azure OpenAI, Azure AI Search, Azure PostgreSQL, Key Vault, and Entra ID can be enabled for managed deployments.

## Request Flow

```mermaid
sequenceDiagram
    participant User
    participant API
    participant Store as SQLite
    participant Retriever
    participant Generator
    User->>API: POST /query question + user_role
    API->>Store: Load document chunks
    API->>Retriever: Filter chunks by role
    Retriever-->>API: Top accessible chunks
    API->>Generator: Build answer from cited context
    API->>Store: Persist query metrics
    API-->>User: Answer, citations, latency, retrieval metrics
```
