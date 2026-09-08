import type {
  DocumentStatusResponse,
  DocumentUploadResponse,
  Fact,
  HealthResponse,
  Relationship,
  RelationshipType,
} from "@/lib/types"

const configuredBase = import.meta.env.VITE_API_BASE_URL?.trim()
export const API_BASE_URL = (configuredBase || "/api").replace(/\/$/, "")

export const API_DOCS_URL = `${API_BASE_URL}/docs`

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message)
    this.name = "ApiError"
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, init)
  } catch {
    throw new ApiError(`Cannot reach the FastAPI service at ${API_BASE_URL}`)
  }

  if (!response.ok) {
    let detail = response.statusText || "Request failed"
    try {
      const payload = (await response.json()) as { detail?: string }
      detail = payload.detail || detail
    } catch {
      // The status text is the safest fallback for a non-JSON error.
    }
    throw new ApiError(`Backend returned ${response.status}: ${detail}`, response.status)
  }

  try {
    return (await response.json()) as T
  } catch {
    throw new ApiError("Backend returned an invalid JSON response", response.status)
  }
}

export const api = {
  health: () => request<HealthResponse>("/health"),

  uploadDocument: (file: File, retryFailed = false) => {
    const body = new FormData()
    body.append("file", file)
    const query = retryFailed ? "?retry_failed=true" : ""
    return request<DocumentUploadResponse>(`/documents${query}`, { method: "POST", body })
  },

  documentStatus: (documentId: string) =>
    request<DocumentStatusResponse>(`/documents/${encodeURIComponent(documentId)}`),

  facts: (documentId: string) =>
    request<Fact[]>(`/documents/${encodeURIComponent(documentId)}/facts`),

  relationships: (filters: {
    classification?: RelationshipType
    documentId?: string
  }) => {
    const search = new URLSearchParams()
    if (filters.classification) search.set("classification", filters.classification)
    if (filters.documentId) search.set("document_id", filters.documentId)
    const query = search.size ? `?${search.toString()}` : ""
    return request<Relationship[]>(`/relationships${query}`)
  },
}
