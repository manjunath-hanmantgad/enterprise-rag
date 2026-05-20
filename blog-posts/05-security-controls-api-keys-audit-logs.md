# Security Controls in Enterprise RAG: Keys, Audit Logs, and the Hierarchy That Prevents Role Elevation

*Enterprise RAG — A practitioner's build log | Post 5 of 6*

---

A knowledge search system for internal documents carries a specific security obligation: it must not make it easier to access restricted information than going to the document source directly. If an employee can ask a question and receive an answer that reflects finance data they are not authorized to see, the system has introduced a new attack surface that did not exist before.

The security design in Enterprise RAG addresses this through a hierarchy of controls — not a single mechanism, but a layered set that each address a distinct failure point. This post documents what each control does, the tradeoff it accepts, and what remains explicitly unimplemented.

---

## Control 1: API key role binding — preventing request-body role elevation

The query endpoint accepts a `user_role` parameter in the request body. For unauthenticated local use, this is acceptable. In any shared or externally accessible environment, it is a security problem: a caller who knows the role parameter name can claim any role and retrieve documents outside their authorization.

The control is API key role binding. When a request includes an `X-API-Key` header, the role context for retrieval is derived from the key holder's registered role — not from the request body. The request body role is ignored entirely.

```
User registers → POST /auth/register (role assigned at registration)
Admin creates key → POST /api-keys (key is bound to user's role)
Query with key → POST /query + X-API-Key: <key>
Role used for retrieval: key holder's registered role (request body role ignored)
```

This closes the role elevation path for authenticated callers. A key issued to a user with `role: employee` cannot retrieve finance documents even if the caller submits `user_role: finance` in the request body.

API keys are stored as SHA-256 hashes. The raw key is returned once at creation and never again. If a key is lost, it must be revoked and reissued — the stored hash cannot be reversed to recover the original value.

---

## Control 2: Key revocation — making access removal immediate

API key revocation (`POST /api-keys/{api_key_id}/revoke`) removes the stored hash. A revoked key is rejected by `POST /query` on the next request — there is no grace period, no cache to drain, no session to expire.

This is operationally important for two scenarios: an employee departure and a compromised credential. In both cases, the recovery action is immediate revocation rather than waiting for a session timeout or token expiry.

The revocation endpoint requires the `ADMIN_TOKEN` when management protection is enabled, which means the revocation action itself is authenticated. An unauthorized caller cannot revoke another user's key.

---

## Control 3: Management endpoint protection — separating operational from query access

A class of endpoints — ingestion, user registration, key creation, key listing, audit log access, and evaluation runs — are administrative by nature. In any shared or hosted environment, these endpoints must not be accessible without authentication.

When `ADMIN_TOKEN` is set, these endpoints require `X-Admin-Token` in the request header:

- `POST /ingest`
- `POST /auth/register`
- `POST /api-keys`, `GET /api-keys`, `POST /api-keys/{api_key_id}/revoke`
- `GET /audit-logs`
- `POST /eval/run`

The query endpoint (`POST /query`) is governed separately by API key authentication. Query access and management access use different credentials with different scopes. A leaked query key does not grant management access. A leaked admin token does not include the role context of any specific user.

---

## Control 4: Audit logging — making every administrative action traceable

Every management action writes a record to `audit_logs`: which action was taken, when, and by which admin credential. The audit log is readable through `GET /audit-logs` with admin authentication.

The current scope of audit logging covers administrative actions. Query logs — which record the question asked, the role used, the citations returned, and the RBAC-blocked chunk count — are stored separately in the query log table and accessible through the dashboard.

Together, these two logs answer the questions a security review will ask: who ingested documents, when were keys created or revoked, what was queried by which role, and what was blocked.

---

## Control 5: Security headers and CORS — default-on, not opt-in

Security headers are enabled by default (`SECURITY_HEADERS_ENABLED=true` in the base configuration). CORS origins are configured explicitly through `CORS_ORIGINS` — no wildcard default.

These are baseline controls that cost nothing and prevent a class of browser-based attacks. An API that stores internal document citations should not allow cross-origin requests from arbitrary origins.

For Azure deployment, the CORS origin list should enumerate only the dashboard Container App URL and any internal tools that call the query API directly.

---

## What is not yet implemented

**Entra ID and OIDC role derivation from token claims.** The `AUTH_PROVIDER=entra` and `AUTH_PROVIDER=oidc` configuration paths are implemented and validate bearer JWTs against issuer, audience, expiration, and JWKS signing keys. Role mapping reads from `roles`, `groups`, or `role` token claims and defaults to `employee` when no role claim is present. End-to-end validation requires a live Azure tenant — it is not testable in the local environment.

**Tenant isolation for multi-organization deployments.** The current implementation assumes a single organization. Multi-tenant deployment — where organization A's documents are completely isolated from organization B — requires additional data model work and is a documented production consideration.

**PII classification for ingested documents.** The included reference documents are synthetic. Production ingestion should classify documents for PII content and apply explicit retention policies for prompts and generated answers before storing them.

**Distributed rate limiting.** The current in-memory rate limiter (`RATE_LIMIT_PER_MINUTE`) works correctly for single-instance deployments. Multi-instance production deployments require Redis-backed or API gateway rate limiting.

---

## The security posture in plain terms

Enterprise RAG is designed for internal deployment by an engineering team with control over the document corpus, the user registry, and the infrastructure. The controls are appropriate for that context. The gaps — multi-tenant isolation, production-grade PII classification, distributed rate limiting — are appropriate for a larger managed deployment and are documented rather than hidden.

Deploying this system to a shared or externally accessible environment without setting `ADMIN_TOKEN` is a configuration error, not an implementation gap. The controls are present. The operator must activate them.

---

## Next engineering step

Enable `ADMIN_TOKEN` in your local `.env`, attempt to call `POST /ingest` without the token, and verify the endpoint returns a 401. Then call `GET /audit-logs` with the admin token and confirm the rejected attempt was logged. That sequence validates that management protection is enforced and that audit logging is capturing the right events.

---

## One question for you

For internal tools that handle restricted documents, do you separate query credentials from management credentials? If a query key were compromised, could an attacker use it to ingest new documents or access the audit log?

---

*Final post in this series: Deployment readiness — what is running locally, what the Azure path requires, and an honest list of what needs to be in place before this system handles real internal documents in production.*
