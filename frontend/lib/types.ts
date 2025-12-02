// types for the constellation api response

export interface AuditResult {
    safe: boolean;
    reasoning: string | null;
    suggestion?: string | null;
}

export interface ConstellationResponse {
    draft: string;
    medical_audit: AuditResult;
    legal_audit: AuditResult;
    final_response: string;
    was_corrected: boolean;
}

export interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
    // only for assistant messages
    constellation?: ConstellationResponse;
    timestamp: Date;
}

// streaming event types
export interface StreamEvent {
    step: string;
    status: string;
    draft?: string;
    result?: AuditResult | ConstellationResponse;
    safe?: boolean;
}

export interface ProcessState {
    drafting: "pending" | "active" | "complete";
    medical_check: "pending" | "active" | "complete";
    legal_check: "pending" | "active" | "complete";
    correcting: "pending" | "active" | "complete" | "skipped";
    finalizing: "pending" | "active" | "complete";

    // results as they come in
    draft?: string;
    medicalResult?: AuditResult;
    legalResult?: AuditResult;
}

// chat history for sidebar
export interface ChatSession {
    id: string;
    title: string;
    messages: Message[];
    createdAt: Date;
    updatedAt: Date;
}