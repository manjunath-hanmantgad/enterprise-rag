import os

import httpx
import streamlit as st


API_URL = os.getenv("DASHBOARD_API_URL", "http://127.0.0.1:8002").rstrip("/")
ADMIN_TOKEN = os.getenv("DASHBOARD_ADMIN_TOKEN", "")


def headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    output = {"X-Request-ID": "dashboard"}
    if ADMIN_TOKEN:
        output["X-Admin-Token"] = ADMIN_TOKEN
    if extra:
        output.update(extra)
    return output


def api_request(method: str, path: str, **kwargs):
    response = httpx.request(method, f"{API_URL}{path}", headers=headers(kwargs.pop("headers", None)), timeout=10, **kwargs)
    if response.status_code >= 400:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        raise RuntimeError(f"{response.status_code}: {detail}")
    if response.headers.get("content-type", "").startswith("application/json"):
        return response.json()
    return response.text


st.set_page_config(page_title="Enterprise RAG", layout="wide")
st.title("Enterprise RAG")
st.caption("Secure document question answering with citations, API-backed dashboard controls, and retrieval evaluation.")

try:
    ready = api_request("GET", "/ready")
    metrics = api_request("GET", "/metrics")
except Exception as exc:
    st.error(f"API unavailable: {exc}")
    st.stop()

col_a, col_b, col_c, col_d = st.columns(4)
col_a.metric("Documents", metrics["document_count"])
col_b.metric("Chunks", metrics["chunk_count"])
col_c.metric("Queries", metrics["query_count"])
col_d.metric("Avg latency", f"{metrics['average_latency_ms']:.0f} ms")

st.caption(f"API: {API_URL} · readiness: {ready['status']} · retrieval: {metrics['retrieval_provider']}")

if metrics["document_count"] == 0:
    st.info("Ingest the reference documents to load the local knowledge base.")

query_tab, access_tab, eval_tab, activity_tab = st.tabs(["Query", "Access Control", "Evaluation", "Activity"])

with query_tab:
    left, right = st.columns([2, 1])
    with left:
        question = st.text_input("Question", "What is the triage target for security incidents?")
        role = st.selectbox("Role", ["employee", "engineer", "finance", "admin"])
        if st.button("Ask", type="primary"):
            try:
                response = api_request(
                    "POST",
                    "/query",
                    json={"question": question, "user_role": role, "top_k": 4},
                )
                st.subheader("Answer")
                st.write(response["answer"])
                metric_a, metric_b, metric_c = st.columns(3)
                metric_a.metric("Latency", f"{response['latency_ms']} ms")
                metric_b.metric("Citations", len(response["citations"]))
                metric_c.metric("Blocked chunks", int(response["metrics"]["blocked_count"]))
                st.subheader("Citations")
                for citation in response["citations"]:
                    st.markdown(
                        f"**{citation['title']}** · `{citation['document_id']}` · score `{citation['score']}`"
                    )
                    st.write(citation["excerpt"])
            except Exception as exc:
                st.warning(str(exc))
    with right:
        if st.button("Ingest reference documents"):
            try:
                result = api_request("POST", "/ingest")
                st.success(f"Ingested {result['documents']} documents and {result['chunks']} chunks.")
            except Exception as exc:
                st.warning(str(exc))
        st.markdown("**Reference questions**")
        st.write("What is the triage target for security incidents?")
        st.write("What forecast variance requires a written explanation?")
        st.write("How many days per week can employees work remotely?")

with access_tab:
    compare_question = st.text_input(
        "Permission test question",
        "What forecast variance requires a written explanation?",
        key="compare_question",
    )
    if st.button("Compare employee and finance access"):
        try:
            employee_response = api_request(
                "POST", "/query", json={"question": compare_question, "user_role": "employee", "top_k": 4}
            )
            finance_response = api_request(
                "POST", "/query", json={"question": compare_question, "user_role": "finance", "top_k": 4}
            )
            col_left, col_right = st.columns(2)
            with col_left:
                st.subheader("Employee")
                st.write(employee_response["answer"])
                st.write([citation["document_id"] for citation in employee_response["citations"]])
            with col_right:
                st.subheader("Finance")
                st.write(finance_response["answer"])
                st.write([citation["document_id"] for citation in finance_response["citations"]])
        except Exception as exc:
            st.warning(str(exc))

    st.subheader("Local access")
    create_col, key_col = st.columns(2)
    with create_col:
        with st.form("create_user"):
            username = st.text_input("Username", "analyst.employee")
            full_name = st.text_input("Full name", "Analyst Employee")
            new_role = st.selectbox("User role", ["employee", "engineer", "finance", "admin"])
            password = st.text_input("Password", "change-me-local-password", type="password")
            if st.form_submit_button("Create user"):
                try:
                    st.json(
                        api_request(
                            "POST",
                            "/auth/register",
                            json={
                                "username": username,
                                "full_name": full_name,
                                "role": new_role,
                                "password": password,
                            },
                        )
                    )
                except Exception as exc:
                    st.warning(str(exc))
    with key_col:
        with st.form("create_api_key"):
            key_username = st.text_input("Key username", "fatima.finance")
            key_name = st.text_input("Key name", "finance-access-key")
            if st.form_submit_button("Create API key"):
                try:
                    created = api_request("POST", "/api-keys", json={"username": key_username, "name": key_name})
                    st.code(created["api_key"])
                except Exception as exc:
                    st.warning(str(exc))

    try:
        st.dataframe(api_request("GET", "/api-keys"), use_container_width=True)
    except Exception as exc:
        st.warning(str(exc))
    revoke_id = st.number_input("Revoke key id", min_value=1, step=1)
    if st.button("Revoke API key"):
        try:
            st.json(api_request("POST", f"/api-keys/{int(revoke_id)}/revoke"))
        except Exception as exc:
            st.warning(str(exc))

with eval_tab:
    if st.button("Run retrieval evaluation", type="primary"):
        try:
            st.json(api_request("POST", "/eval/run"))
        except Exception as exc:
            st.warning(str(exc))
    if metrics["last_eval"]:
        last_eval = metrics["last_eval"]
        col_1, col_2, col_3, col_4 = st.columns(4)
        col_1.metric("Cases", last_eval["total_cases"])
        col_2.metric("Passed", last_eval["pass_count"])
        col_3.metric("Restricted leaks", last_eval["restricted_leak_count"])
        col_4.metric("Citation coverage", f"{last_eval['citation_coverage']:.2f}")

with activity_tab:
    query_col, audit_col = st.columns(2)
    with query_col:
        st.subheader("Recent queries")
        try:
            st.dataframe(api_request("GET", "/query-logs"), use_container_width=True)
        except Exception as exc:
            st.warning(str(exc))
    with audit_col:
        st.subheader("Audit logs")
        try:
            st.dataframe(api_request("GET", "/audit-logs"), use_container_width=True)
        except Exception as exc:
            st.warning(str(exc))
