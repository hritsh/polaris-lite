// types for the constellation api response

export interface AuditResult {
    safe: boolean;
    reasoning: string | null;
    suggestion?: string | null;
    name?: string;  // auditor display name
}

export interface ConstellationResponse {
    draft: string;
    audits: Record<string, AuditResult>;  // dynamic auditors
    active_auditors: string[];  // which auditors ran
    final_response: string;
    was_corrected: boolean;
    // legacy fields for backwards compatibility
    medical_audit?: AuditResult;
    legal_audit?: AuditResult;
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
    active_auditors?: string[];  // list of auditors that will run
    auditor_id?: string;  // which auditor this event is for
}

// auditor metadata for UI
export interface AuditorInfo {
    id: string;
    name: string;
    icon: string;  // icon name
    color: string;  // tailwind color class
}

// map of auditor ids to their UI info
export const AUDITOR_UI_INFO: Record<string, AuditorInfo> = {
    medical: {
        id: "medical",
        name: "Medical Auditor",
        icon: "Stethoscope",
        color: "text-rose-400",
    },
    legal: {
        id: "legal",
        name: "Legal Auditor",
        icon: "Scale",
        color: "text-purple-400",
    },
    empathy: {
        id: "empathy",
        name: "Empathy Auditor",
        icon: "Heart",
        color: "text-pink-400",
    },
    pediatric: {
        id: "pediatric",
        name: "Pediatric Auditor",
        icon: "Baby",
        color: "text-sky-400",
    },
    drug_interaction: {
        id: "drug_interaction",
        name: "Drug Interaction Auditor",
        icon: "Pill",
        color: "text-amber-400",
    },
};

export interface ProcessState {
    drafting: "pending" | "active" | "complete";
    correcting: "pending" | "active" | "complete" | "skipped";
    finalizing: "pending" | "active" | "complete";

    // dynamic auditor states
    activeAuditors: string[];  // which auditors are running
    auditorStates: Record<string, "pending" | "active" | "complete">;
    auditorResults: Record<string, AuditResult>;

    // results as they come in
    draft?: string;

    // legacy fields for backwards compatibility
    medical_check?: "pending" | "active" | "complete";
    legal_check?: "pending" | "active" | "complete";
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