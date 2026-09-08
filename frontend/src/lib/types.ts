export type DocumentStatus =
  | "queued"
  | "ingesting"
  | "extracting"
  | "verifying"
  | "normalizing"
  | "classifying"
  | "completed"
  | "failed"

export type EvidenceStatus = "verified" | "failed"

export type RelationshipType =
  | "corroborates"
  | "contradicts"
  | "reconciled"
  | "uncertain"

export type CheckOutcome = "passed" | "failed" | "skipped" | "judgment_required"

export interface ConfidenceScore {
  value: number
  method: string
  reasons: string[]
}

export interface FactConfidence {
  extraction: ConfidenceScore
  evidence_verification: ConfidenceScore
}

export interface EvidenceReference {
  physical_page_number: number
  printed_page_label: string | null
  quote: string
  start_offset: number | null
  end_offset: number | null
  status: EvidenceStatus
  failure_reason: string | null
}

export interface Fact {
  id: string
  document_id: string
  subject: string
  predicate: string
  value: string
  unit: string | null
  currency: string | null
  temporal_scope: string | null
  scope: string | null
  data_vintage: string | null
  evidence: EvidenceReference
  verification: {
    method: string
    similarity_score: number
  }
  confidence: FactConfidence
  classification_eligible: boolean
}

export interface ReasoningStep {
  order: number
  check: string
  outcome: CheckOutcome
  details: Record<string, string | number | boolean | null>
}

export interface Relationship {
  id: string
  classification: RelationshipType
  reconciliation_reasons: string[]
  classification_confidence: ConfidenceScore
  reasoning_trace: ReasoningStep[]
  fact_a: Fact
  fact_b: Fact
}

export interface DocumentUploadResponse {
  id: string
  file_name: string
  sha256: string
  status: DocumentStatus
  duplicate_reused: boolean
  retry_started: boolean
}

export interface DocumentStatusResponse {
  id: string
  file_name: string
  sha256: string
  status: DocumentStatus
  created_at: string
  page_count: number | null
  failure_reason: string | null
  processed_page_count: number
  extraction_batch_count: number
  provider_attempt_count: number
  retry_count: number
  last_checkpoint_at: string | null
}

export type TrackedDocument = DocumentUploadResponse &
  Partial<Omit<DocumentStatusResponse, "id" | "file_name" | "sha256" | "status">>

export interface HealthResponse {
  status: "ok"
  database: "ok"
  version: string
}
