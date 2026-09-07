"""Streamlit audit console for evidence-grounded facts and relationships."""

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
        "green": "#22C55E",
        "red": "#F87171",
        "blue": "#60A5FA",
        "orange": "#FB923C",
    }.get(tone, "#CBD5E1")
    st.markdown(
        f"<span style='display:inline-block;border:1px solid {color};color:{color};"
        f"border-radius:999px;padding:3px 9px;font:500 .76rem Fira Code'>"
        f"{label}: {value:.0%}</span>",
        unsafe_allow_html=True,
    )


def _document_choices() -> dict[str, str]:
    return st.session_state.setdefault("documents", {})


def _fact_label(fact: dict[str, Any]) -> str:
    marker = "VERIFIED" if fact["classification_eligible"] else "REJECTED"
    page = fact["evidence"]["physical_page_number"]
    return f"[{marker}] p.{page} · {fact['subject']} · {fact['predicate']}"


def _render_fact(fact: dict[str, Any], *, heading: str | None = None) -> None:
    if heading:
        st.markdown(f"#### {heading}")
    cols = st.columns([3, 2, 2])
    cols[0].markdown(f"**{fact['subject']} — {fact['predicate']}**")
    cols[1].markdown(f"`{fact['value']}`")
    cols[2].markdown(f"Status: **{fact['evidence']['status'].upper()}**")

    score_cols = st.columns(2)
    with score_cols[0]:
        _badge("Extraction", fact["confidence"]["extraction"]["value"], "blue")
    with score_cols[1]:
        _badge(
            "Evidence",
            fact["confidence"]["evidence_verification"]["value"],
            STATUS_TONES[fact["evidence"]["status"]],
        )

    evidence = fact["evidence"]
    printed = evidence.get("printed_page_label") or "not available"
    offsets = (
        f"{evidence['start_offset']}:{evidence['end_offset']}"
        if evidence.get("start_offset") is not None
        else "not verified"
    )
    st.caption(
        f"PHYSICAL PAGE {evidence['physical_page_number']} · "
        f"PRINTED LABEL {printed} · OFFSETS {offsets}"
    )
    st.code(evidence["quote"], language=None, wrap_lines=True)
    if evidence.get("failure_reason"):
        st.error(f"Evidence rejected: {evidence['failure_reason']}")


def _upload_panel(api: FactKnowledgeApi) -> None:
    st.subheader("Add source documents")
    st.caption("PDFs are hashed before processing, so duplicate uploads reuse existing work.")
    upload = st.file_uploader("Choose a PDF", type=["pdf"], accept_multiple_files=False)
    if st.button("Extract grounded facts", type="primary", disabled=upload is None):
        assert upload is not None
        with st.spinner("Uploading and starting the evidence pipeline…"):
            result = api.upload_document(upload.name, upload.getvalue())
        _document_choices()[result["id"]] = result["file_name"]
        if result["duplicate_reused"]:
            st.info("This exact file was already processed. Existing results were reused.")
        else:
            st.success("Document accepted. Refresh its status below as processing continues.")

    documents = _document_choices()
    if documents:
        selected = st.selectbox(
            "Tracked document",
            list(documents),
            format_func=lambda item: f"{documents[item]} · {item[:8]}",
        )
        if st.button("Refresh processing status"):
            status = api.document_status(selected)
            st.session_state["last_status"] = status
        status = st.session_state.get("last_status")
        if status and status["id"] == selected:
            st.metric("Pipeline status", status["status"].upper())
            if status.get("failure_reason"):
                st.error(status["failure_reason"])


def _facts_panel(api: FactKnowledgeApi) -> None:
    st.subheader("Fact ledger")
    st.caption("Select a fact to inspect its exact source quote and page-local offsets.")
    documents = _document_choices()
    document_id = st.text_input(
        "Document ID",
        value=next(reversed(documents), ""),
        placeholder="Paste a document UUID",
    )
    if not document_id:
        st.info("Upload a PDF or paste a document ID to inspect facts.")
        return
    facts = api.facts(document_id)
    verified = sum(fact["classification_eligible"] for fact in facts)
    metrics = st.columns(3)
    metrics[0].metric("Extracted", len(facts))
    metrics[1].metric("Verified", verified)
    metrics[2].metric("Rejected", len(facts) - verified)
    if not facts:
        st.info("No extracted facts are available yet. Check the processing status.")
        return
    selected_index = st.selectbox(
        "Fact",
        range(len(facts)),
        format_func=lambda index: _fact_label(facts[index]),
    )
    _render_fact(facts[selected_index])


def _relationships_panel(api: FactKnowledgeApi) -> None:
    st.subheader("Relationship explorer")
    st.caption("Every decision is deterministic. Expand its trace to audit each ordered check.")
    col_filter, col_document = st.columns([1, 2])
    label = col_filter.selectbox("Decision type", list(RELATIONSHIP_LABELS))
    document_id = col_document.text_input(
        "Limit to document ID",
        placeholder="Optional document UUID",
    )
    if not st.button("Load decisions"):
        st.info("Choose optional filters, then load deterministic decisions.")
        return
    relationships = api.relationships(
        classification=RELATIONSHIP_LABELS[label],
        document_id=document_id or None,
    )
    st.metric("Matching decisions", len(relationships))
    if not relationships:
        st.info("No relationships match the current filters.")
        return

    for index, relationship in enumerate(relationships, start=1):
        classification = relationship["classification"]
        title = f"{index}. {classification.upper()} · {relationship['fact_a']['subject']}"
        with st.expander(title, expanded=index == 1):
            _badge(
                "Classification",
                relationship["classification_confidence"]["value"],
                STATUS_TONES[classification],
            )
            if relationship["reconciliation_reasons"]:
                st.caption("Explained by: " + ", ".join(relationship["reconciliation_reasons"]))
            pair = st.columns(2)
            with pair[0]:
                _render_fact(relationship["fact_a"], heading="Fact A")
            with pair[1]:
                _render_fact(relationship["fact_b"], heading="Fact B")
            st.markdown("#### Machine-readable reasoning trace")
            st.dataframe(
                relationship["reasoning_trace"],
                use_container_width=True,
                hide_index=True,
                column_order=["order", "check", "outcome", "details"],
            )


def main() -> None:
    st.set_page_config(
        page_title="Fact Knowledge Layer",
        page_icon=None,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        '<p class="eyebrow">Evidence intelligence / audit console</p>', unsafe_allow_html=True
    )
    st.markdown(
        '<h1 class="hero-title">Facts you can trace. Decisions you can audit.</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="hero-copy">Extract claims from PDFs, recover their exact source evidence, '
        "and inspect deterministic cross-document reasoning without hiding uncertainty.</p>",
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("Connection")
        base_url = st.text_input("FastAPI URL", value="http://localhost:8000")
        st.caption("Start the backend first, then use this console as its audit client.")

    try:
        with FactKnowledgeApi(base_url) as api:
            tabs = st.tabs(["Upload", "Facts", "Relationships"])
            with tabs[0]:
                _upload_panel(api)
            with tabs[1]:
                _facts_panel(api)
            with tabs[2]:
                _relationships_panel(api)
    except ApiClientError as exc:
        st.error(str(exc))
        st.caption("Confirm that the FastAPI service is running and the URL is correct.")


if __name__ == "__main__":
    main()
