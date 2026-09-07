# Frontend Interaction Design

The Streamlit app is an audit console, not a chat interface. Its three work areas mirror the
reviewer's questions: what was uploaded, which facts are grounded, and why two facts received a
particular relationship label.

Run the API with `uvicorn backend.main:app --reload`, then run the interface from the repository
root with `streamlit run frontend/app.py`. The API URL remains editable in the sidebar for hosted
environments.

The visual system uses dense dashboard spacing, high-contrast dark surfaces, textual status labels
in addition to color, visible keyboard focus, a responsive single-column fallback, and reduced-
motion handling. Evidence is rendered as inert code text so PDF content cannot inject HTML into the
page. Relationship calls are user-triggered, preventing inactive Streamlit tabs from repeatedly
querying the backend.
