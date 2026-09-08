"""Streamlit audit console for evidence-grounded facts and relationships."""

import json
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st

from frontend.api_client import ApiClientError, FactKnowledgeApi

RELATIONSHIP_LABELS = {
    "All decisions": None,
    "Corroborated": "corroborates",
    "Contradicted": "contradicts",
    "Reconciled": "reconciled",
    "Uncertain": "uncertain",
}

STATUS_TONES = {
    "verified": "green",
    "failed": "red",
    "corroborates": "green",
    "contradicts": "red",
    "reconciled": "blue",
    "uncertain": "orange",
}

CSS = f"<style>{(Path(__file__).parent / 'styles.css').read_text(encoding='utf-8')}</style>"


def _badge(label: str, value: float, tone: str) -> None:
    color = {
        "green": "#4ADE80",
        "red": "#FB7185",
        "blue": "#60A5FA",
        "orange": "#FBBF24",
    }.get(tone, "#CBD5E1")
    st.markdown(
        f"<span class='score-badge' style='--badge-color:{color}'>"
        f"{escape(label)} <strong>{value:.0%}</strong></span>",
        unsafe_allow_html=True,
    )


def _document_choices() -> dict[str, str]:
    return st.session_state.setdefault("documents", {})


def _fact_label(fact: dict[str, Any]) -> str:
    marker = "VERIFIED" if fact["classification_eligible"] else "REJECTED"
    page = fact["evidence"]["physical_page_number"]
    return f"[{marker}] p.{page} · {fact['subject']} · {fact['predicate']}"


def _render_header() -> None:
    st.markdown(
        """
        <section class="product-header">
          <div class="brand-lockup">
            <div class="brand-mark" aria-hidden="true">FKL</div>
            <div>
              <p class="product-kicker">EVIDENCE INTELLIGENCE</p>
              <h1>Fact Knowledge Layer</h1>
            </div>
          </div>
          <p class="product-copy">
            Convert financial PDFs into facts that reviewers can locate, verify,
            and compare across documents.
          </p>
          <div class="assurance-row" aria-label="System guarantees">
            <span><i></i> Verbatim evidence</span>
            <span><i></i> Deterministic decisions</span>
            <span><i></i> Visible uncertainty</span>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_empty_state(title: str, description: str, action: str) -> None:
    st.markdown(
        f"""
        <div class="empty-state">
          <span class="empty-state-index">READY</span>
          <h3>{escape(title)}</h3>
          <p>{escape(description)}</p>
          <small>{escape(action)}</small>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_process_strip() -> None:
    st.markdown(
        """
        <div class="process-strip" aria-label="Processing pipeline">
          <div class="process-step">
            <b>01</b><span>INGEST</span><small>Parse every page</small>
          </div>
          <div class="process-step">
            <b>02</b><span>EXTRACT</span><small>Structure candidate facts</small>
          </div>
          <div class="process-step">
            <b>03</b><span>VERIFY</span><small>Recover exact evidence</small>
          </div>
          <div class="process-step">
            <b>04</b><span>REASON</span><small>Compare deterministically</small>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_fact(fact: dict[str, Any], *, heading: str | None = None) -> None:
    if heading:
        st.markdown(f"#### {heading}")

    claim = st.columns([1.4, 1.4, 1])
    claim[0].caption("SUBJECT")
    claim[0].markdown(f"**{fact['subject']}**")
    claim[1].caption("PREDICATE")
    claim[1].markdown(f"**{fact['predicate']}**")
    claim[2].caption("VALUE")
    claim[2].code(str(fact["value"]), language=None)

    evidence = fact["evidence"]
    scores = st.columns([1, 1, 1.4])
    with scores[0]:
        _badge("Extraction", fact["confidence"]["extraction"]["value"], "blue")
    with scores[1]:
        _badge(
            "Evidence",
            fact["confidence"]["evidence_verification"]["value"],
            STATUS_TONES[evidence["status"]],
        )
    scores[2].caption(
        "ELIGIBLE FOR COMPARISON" if fact["classification_eligible"] else "EXCLUDED FROM COMPARISON"
    )

    printed = evidence.get("printed_page_label") or "not available"
    offsets = (
        f"{evidence['start_offset']}:{evidence['end_offset']}"
        if evidence.get("start_offset") is not None
        else "not verified"
    )
    st.markdown("##### Source evidence")
    st.caption(
        f"PHYSICAL PAGE {evidence['physical_page_number']} · "
        f"PRINTED LABEL {printed} · OFFSETS {offsets}"
    )
    st.code(evidence["quote"], language=None, wrap_lines=True)
    if evidence.get("failure_reason"):
        st.error(f"Evidence rejected: {evidence['failure_reason']}")


def _upload_panel(api: FactKnowledgeApi) -> None:
    st.markdown('<p class="section-kicker">01 / DOCUMENT INTAKE</p>', unsafe_allow_html=True)
    st.subheader("Start with a source PDF")
    st.caption(
        "Each upload is hashed before processing. Exact duplicates reuse their existing facts."
    )

    upload_column, contract_column = st.columns([1.65, 1], gap="large")
    with upload_column:
        with st.container(border=True):
            upload = st.file_uploader(
                "Upload one PDF",
                type=["pdf"],
                accept_multiple_files=False,
                help=(
                    "Upload any text-based PDF. The pipeline does not depend on a fixed "
                    "filename or schema."
                ),
            )
            if upload is None:
                st.caption("PDF only · up to 100 MB · source is processed page by page")
            if st.button(
                "Extract grounded facts",
                type="primary",
                disabled=upload is None,
                use_container_width=True,
            ):
                assert upload is not None
                with st.spinner("Starting the evidence pipeline…"):
                    result = api.upload_document(upload.name, upload.getvalue())
                _document_choices()[result["id"]] = result["file_name"]
                if result["duplicate_reused"]:
                    st.info("This exact file already exists. Its previous results were reused.")
                else:
                    st.success("Document accepted. Track processing below while the pipeline runs.")

    with contract_column:
        st.markdown(
            """
            <aside class="evidence-contract">
              <p class="card-kicker">EVIDENCE CONTRACT</p>
              <h3>No claim without a trail.</h3>
              <ul>
                <li><b>Locate</b><span>Physical page and page-local offsets</span></li>
                <li><b>Quote</b><span>Actual substring recovered from the PDF</span></li>
                <li><b>Audit</b><span>Ordered checks behind every relationship</span></li>
              </ul>
            </aside>
            """,
            unsafe_allow_html=True,
        )

    _render_process_strip()

    documents = _document_choices()
    st.markdown(
        '<p class="section-kicker workspace-kicker">ACTIVE WORKSPACE</p>',
        unsafe_allow_html=True,
    )
    if not documents:
        _render_empty_state(
            "No documents tracked yet",
            "Upload a PDF to create the first auditable fact ledger in this browser session.",
            "Your source document is the starting point.",
        )
        return

    status_column, action_column = st.columns([2.2, 1])
    selected = status_column.selectbox(
        "Tracked document",
        list(documents),
        format_func=lambda item: f"{documents[item]} · {item[:8]}",
    )
    if action_column.button("Refresh status", use_container_width=True):
        st.session_state["last_status"] = api.document_status(selected)
    status = st.session_state.get("last_status")
    if status and status["id"] == selected:
        metrics = st.columns(3)
        metrics[0].metric("Pipeline", status["status"].upper())
        metrics[1].metric("Document", documents[selected])
        metrics[2].metric("Reference", selected[:8].upper())
        if status.get("failure_reason"):
            st.error(status["failure_reason"])


def _facts_panel(api: FactKnowledgeApi) -> None:
    st.markdown('<p class="section-kicker">02 / FACT REVIEW</p>', unsafe_allow_html=True)
    st.subheader("Fact ledger")
    st.caption("Inspect a structured claim beside its exact source quote and page-local offsets.")
    documents = _document_choices()
    document_id = st.text_input(
        "Document ID",
        value=next(reversed(documents), ""),
        placeholder="Paste a document UUID",
    )
    if not document_id:
        _render_empty_state(
            "Choose a fact source",
            "Upload a PDF first, or paste a document ID from the API.",
            "Verified and rejected facts remain visibly separate.",
        )
        return

    facts = api.facts(document_id)
    verified = sum(fact["classification_eligible"] for fact in facts)
    metrics = st.columns(3)
    metrics[0].metric("Extracted", len(facts), help="All candidate facts returned by extraction")
    metrics[1].metric("Evidence verified", verified, help="Quote recovered from its source page")
    metrics[2].metric(
        "Rejected",
        len(facts) - verified,
        help="Retained for audit but excluded from relationship classification",
    )
    if not facts:
        _render_empty_state(
            "Facts are not ready",
            "The document may still be processing, or extraction produced no candidate facts.",
            "Check its status on the upload tab.",
        )
        return

    toolbar = st.columns([2.2, 1])
    selected_index = toolbar[0].selectbox(
        "Select a fact",
        range(len(facts)),
        format_func=lambda index: _fact_label(facts[index]),
    )
    toolbar[1].download_button(
        "Export fact ledger",
        data=json.dumps(facts, indent=2),
        file_name=f"facts-{document_id[:8]}.json",
        mime="application/json",
        use_container_width=True,
    )
    with st.container(border=True):
        _render_fact(facts[selected_index])


def _relationships_panel(api: FactKnowledgeApi) -> None:
    st.markdown('<p class="section-kicker">03 / DECISION AUDIT</p>', unsafe_allow_html=True)
    st.subheader("Relationship explorer")
    st.caption("Filter deterministic decisions, then open the ordered reasoning trace.")
    col_filter, col_document, col_action = st.columns([1, 1.6, 0.8])
    label = col_filter.selectbox("Decision type", list(RELATIONSHIP_LABELS))
    document_id = col_document.text_input(
        "Limit to document ID",
        placeholder="Optional document UUID",
    )
    query_key = (RELATIONSHIP_LABELS[label], document_id or None)
    if col_action.button("Load decisions", type="primary", use_container_width=True):
        st.session_state["relationship_results"] = {
            "query": query_key,
            "items": api.relationships(
                classification=query_key[0],
                document_id=query_key[1],
            ),
        }

    cached = st.session_state.get("relationship_results")
    if not cached or cached["query"] != query_key:
        _render_empty_state(
            "No decision set loaded",
            "Choose a classification or document filter, then load matching relationships.",
            "Each result includes both facts, confidence, and an ordered trace.",
        )
        return

    relationships = cached["items"]
    metric_column, export_column = st.columns([2, 1])
    metric_column.metric("Matching decisions", len(relationships))
    export_column.download_button(
        "Export decisions",
        data=json.dumps(relationships, indent=2),
        file_name="relationship-decisions.json",
        mime="application/json",
        use_container_width=True,
    )
    if not relationships:
        st.info("No relationships match the current filters.")
        return

    for index, relationship in enumerate(relationships, start=1):
        classification = relationship["classification"]
        subject = relationship["fact_a"]["subject"]
        title = f"{index:02d} · {classification.upper()} · {subject}"
        with st.expander(title, expanded=index == 1):
            _badge(
                "Classification confidence",
                relationship["classification_confidence"]["value"],
                STATUS_TONES[classification],
            )
            if relationship["reconciliation_reasons"]:
                st.caption("Explained by: " + ", ".join(relationship["reconciliation_reasons"]))
            pair = st.columns(2, gap="large")
            with pair[0]:
                _render_fact(relationship["fact_a"], heading="Fact A")
            with pair[1]:
                _render_fact(relationship["fact_b"], heading="Fact B")
            st.markdown("#### Deterministic reasoning trace")
            st.dataframe(
                relationship["reasoning_trace"],
                use_container_width=True,
                hide_index=True,
                column_order=["order", "check", "outcome", "details"],
            )


def _runtime_sidebar() -> str:
    with st.sidebar:
        st.markdown(
            '<div class="sidebar-brand">FKL <span>CONSOLE</span></div>',
            unsafe_allow_html=True,
        )
        st.subheader("Runtime connection")
        base_url = st.text_input("FastAPI URL", value="http://localhost:8000")
        if st.button("Check API health", use_container_width=True):
            try:
                with FactKnowledgeApi(base_url, timeout=3.0) as probe:
                    health = probe.health()
                st.session_state["api_health"] = health
            except ApiClientError as exc:
                st.session_state["api_health"] = {"error": str(exc)}
        health = st.session_state.get("api_health")
        if health:
            if health.get("error"):
                st.error(health["error"])
            else:
                st.success("API and database are ready")
        st.divider()
        st.caption(
            "The console calls the FastAPI service. LLM credentials remain server-side "
            "and are never sent to this UI."
        )
        st.link_button(
            "Open API documentation",
            f"{base_url.rstrip('/')}/docs",
            use_container_width=True,
        )
    return base_url


def main() -> None:
    st.set_page_config(
        page_title="Fact Knowledge Layer",
        page_icon=None,
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(CSS, unsafe_allow_html=True)
    _render_header()
    base_url = _runtime_sidebar()

    try:
        with FactKnowledgeApi(base_url) as api:
            tabs = st.tabs(["Overview & upload", "Fact ledger", "Relationship explorer"])
            with tabs[0]:
                _upload_panel(api)
            with tabs[1]:
                _facts_panel(api)
            with tabs[2]:
                _relationships_panel(api)
    except ApiClientError as exc:
        st.error(str(exc))
        st.caption("Open runtime settings and confirm that the FastAPI service is running.")

    st.markdown(
        '<footer class="product-footer">FACT KNOWLEDGE LAYER · EVIDENCE BEFORE INFERENCE</footer>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
