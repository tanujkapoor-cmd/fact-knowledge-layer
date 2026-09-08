# Frontend Interaction Design

The frontend is a Vite-powered React and TypeScript audit console, not a chat interface. Its three
work areas mirror a reviewer's questions: what was uploaded, which facts are grounded, and why two
facts received a particular relationship label.

Run the API from the repository root with `uvicorn backend.main:app --reload`. In a second terminal,
run `npm install` and `npm run dev` from `frontend/`. Vite serves the interface at
`http://127.0.0.1:5173` and proxies `/api` to FastAPI at `http://127.0.0.1:8000`. A hosted build can
set `VITE_API_BASE_URL` to the deployed API origin.

The interface uses React, TypeScript, Tailwind CSS, locally owned shadcn-style components, Radix
primitives, Lucide icons, and Motion for React. Motion is limited to short state transitions and
respects the user's reduced-motion preference.

The visual system uses dense dashboard spacing, high-contrast dark surfaces, textual labels in
addition to color, visible keyboard focus, responsive desktop/mobile navigation, and semantic
native controls. Document references are saved in browser local storage so an upload can be
revisited without introducing a separate frontend database. All document-derived values are
rendered as React text nodes; the client does not inject source content as HTML.

Uploads provide immediate validation and submission feedback. Active documents poll their status
without moving keyboard focus. Fact review keeps a candidate index beside its evidence inspector.
Relationship review separates the deterministic reasoning trace from the two complete source
facts. Both result sets can be exported as JSON for external review.
