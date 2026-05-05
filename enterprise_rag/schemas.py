from pydantic import BaseModel, Field


class Citation(BaseModel):
    document_id: str
    title: str
    chunk_id: str
    excerpt: str
    score: float


class QueryRequest(BaseModel):
    question: str = Field(min_length=3)
    user_role: str = Field(default="employee", min_length=2)
    top_k: int = Field(default=4, ge=1, le=10)


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    user_role: str
    latency_ms: int
    metrics: dict[str, float | int | str]


class DocumentRead(BaseModel):
    id: str
    title: str
    department: str
    allowed_roles: list[str]
    source_path: str


class IngestResponse(BaseModel):
    documents: int
    chunks: int


class MetricsResponse(BaseModel):
    document_count: int
    chunk_count: int
    query_count: int
    average_latency_ms: float
    retrieval_provider: str
    last_eval: dict | None


class UserCreate(BaseModel):
    username: str = Field(min_length=3)
    full_name: str = Field(min_length=2)
    role: str = Field(default="employee", min_length=2)
    password: str = Field(min_length=8)


class UserRead(BaseModel):
    id: int
    username: str
    full_name: str
    role: str


class ApiKeyCreate(BaseModel):
    username: str = Field(min_length=3)
    name: str = Field(default="local-access-key", min_length=2)


class ApiKeyCreateResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    api_key: str
    username: str
    role: str


class ApiKeyRead(BaseModel):
    id: int
    name: str
    key_prefix: str
    username: str
    full_name: str
    role: str
    revoked_at: str | None
    created_at: str


class AuditLogRead(BaseModel):
    id: int
    action: str
    actor: str
    detail: str
    created_at: str


class QueryLogRead(BaseModel):
    id: int
    question: str
    user_role: str
    retrieved_count: int
    blocked_count: int
    latency_ms: int
    created_at: str
