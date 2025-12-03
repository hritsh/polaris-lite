"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Message, ConstellationResponse, ProcessState, StreamEvent, AuditResult, ChatSession } from "@/lib/types";
import { sendMessageStream } from "@/lib/api";

const initialProcessState: ProcessState = {
    drafting: "pending",
    correcting: "pending",
    finalizing: "pending",
    activeAuditors: [],
    auditorStates: {},
    auditorResults: {},
};

const STORAGE_KEY = "constellation_chat_history";

// helper to load sessions from localStorage
function loadSessions(): ChatSession[] {
    if (typeof window === "undefined") return [];
    try {
        const data = localStorage.getItem(STORAGE_KEY);
        if (!data) return [];
        const sessions = JSON.parse(data);
        // parse dates
        return sessions.map((s: ChatSession) => ({
            ...s,
            createdAt: new Date(s.createdAt),
            updatedAt: new Date(s.updatedAt),
            messages: s.messages.map((m: Message) => ({
                ...m,
                timestamp: new Date(m.timestamp),
            })),
        }));
    } catch {
        return [];
    }
}

// helper to save sessions to localStorage
function saveSessions(sessions: ChatSession[]) {
    if (typeof window === "undefined") return;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
}

export function useChat() {
    // initialize sessions from localStorage directly
    const [sessions, setSessions] = useState<ChatSession[]>(() => loadSessions());
    const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [processState, setProcessState] = useState<ProcessState>(initialProcessState);
    const [hitlMode, setHitlMode] = useState(false);
    const [pendingResponse, setPendingResponse] = useState<ConstellationResponse | null>(null);

    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = useCallback(() => {
        setTimeout(() => {
            messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
        }, 100);
    }, []);

    useEffect(() => {
        scrollToBottom();
    }, [messages, scrollToBottom]);

    // also scroll when process state changes
    useEffect(() => {
        if (isLoading) {
            scrollToBottom();
        }
    }, [processState, isLoading, scrollToBottom]);

    const handleStreamEvent = useCallback((event: StreamEvent) => {
        setProcessState((prev) => {
            const next = { ...prev };

            switch (event.step) {
                case "drafting":
                    if (event.status === "started") {
                        next.drafting = "active";
                    } else if (event.status === "complete") {
                        next.drafting = "complete";
                        next.draft = event.draft;
                    }
                    break;

                case "auditing":
                    // received list of active auditors
                    if (event.status === "started" && event.active_auditors) {
                        next.activeAuditors = event.active_auditors;
                        // initialize all auditor states as pending
                        const states: Record<string, "pending" | "active" | "complete"> = {};
                        for (const auditorId of event.active_auditors) {
                            states[auditorId] = "pending";
                        }
                        next.auditorStates = states;
                    }
                    break;

                case "correcting":
                    if (event.status === "started") {
                        next.correcting = "active";
                    } else if (event.status === "complete") {
                        next.correcting = "complete";
                    }
                    break;

                case "finalizing":
                    if (event.status === "started") {
                        next.finalizing = "active";
                        // if we never needed correction, mark it skipped
                        if (next.correcting === "pending") {
                            next.correcting = "skipped";
                        }
                    }
                    break;

                case "complete":
                    next.finalizing = "complete";
                    break;

                default:
                    // handle dynamic auditor events (e.g., "medical_check", "empathy_check")
                    if (event.step.endsWith("_check") && event.auditor_id) {
                        const auditorId = event.auditor_id;
                        if (event.status === "started") {
                            next.auditorStates = {
                                ...next.auditorStates,
                                [auditorId]: "active",
                            };
                        } else if (event.status === "complete") {
                            next.auditorStates = {
                                ...next.auditorStates,
                                [auditorId]: "complete",
                            };
                            if (event.result) {
                                next.auditorResults = {
                                    ...next.auditorResults,
                                    [auditorId]: event.result as AuditResult,
                                };
                            }
                        }
                    }
                    break;
            }

            return next;
        });
    }, []);

    const startNewSession = useCallback(() => {
        const newSession: ChatSession = {
            id: crypto.randomUUID(),
            title: "New Chat",
            messages: [],
            createdAt: new Date(),
            updatedAt: new Date(),
        };
        setSessions((prev) => {
            const updated = [newSession, ...prev];
            saveSessions(updated);
            return updated;
        });
        setCurrentSessionId(newSession.id);
        setMessages([]);
        setProcessState(initialProcessState);
        setPendingResponse(null);
    }, []);

    const loadSession = useCallback((sessionId: string) => {
        const session = sessions.find((s) => s.id === sessionId);
        if (session) {
            setCurrentSessionId(sessionId);
            setMessages(session.messages);
            setProcessState(initialProcessState);
            setPendingResponse(null);
        }
    }, [sessions]);

    const deleteSession = useCallback((sessionId: string) => {
        setSessions((prev) => {
            const updated = prev.filter((s) => s.id !== sessionId);
            saveSessions(updated);
            return updated;
        });
        if (currentSessionId === sessionId) {
            setCurrentSessionId(null);
            setMessages([]);
        }
    }, [currentSessionId]);

    const send = async (content: string) => {
        if (!content.trim() || isLoading) return;

        let sessionId = currentSessionId;

        // create new session if needed
        if (!sessionId) {
            const newSession: ChatSession = {
                id: crypto.randomUUID(),
                title: content.slice(0, 40) + (content.length > 40 ? "..." : ""),
                messages: [],
                createdAt: new Date(),
                updatedAt: new Date(),
            };
            sessionId = newSession.id;
            setSessions((prev) => {
                const updated = [newSession, ...prev];
                saveSessions(updated);
                return updated;
            });
            setCurrentSessionId(sessionId);
        } else {
            // update session title if this is the first message
            setSessions((prev) => {
                const session = prev.find((s) => s.id === sessionId);
                if (session && session.messages.length === 0) {
                    const updated = prev.map((s) =>
                        s.id === sessionId
                            ? { ...s, title: content.slice(0, 40) + (content.length > 40 ? "..." : "") }
                            : s
                    );
                    saveSessions(updated);
                    return updated;
                }
                return prev;
            });
        }

        // add user message
        const userMessage: Message = {
            id: crypto.randomUUID(),
            role: "user",
            content: content.trim(),
            timestamp: new Date(),
        };
        setMessages((prev) => {
            const updated = [...prev, userMessage];
            // sync user message to session too
            setSessions((prevSessions) => {
                const updatedSessions = prevSessions.map((s) =>
                    s.id === sessionId
                        ? { ...s, messages: updated, updatedAt: new Date() }
                        : s
                );
                saveSessions(updatedSessions);
                return updatedSessions;
            });
            return updated;
        });
        setIsLoading(true);
        setProcessState(initialProcessState);

        try {
            // use streaming endpoint to get real-time updates
            // pass current messages as history for context
            const response = await sendMessageStream(content, handleStreamEvent, messages);

            // if hitl mode and there were corrections, wait for approval
            if (hitlMode && response.was_corrected) {
                setPendingResponse(response);
                setIsLoading(false);
            } else {
                // add assistant message right away
                addAssistantMessage(response, sessionId);
                setIsLoading(false);
            }
        } catch (error) {
            console.error("Failed to send message:", error);
            // add error message
            const errorMessage: Message = {
                id: crypto.randomUUID(),
                role: "assistant",
                content: "Sorry, something went wrong. Please try again.",
                timestamp: new Date(),
            };
            setMessages((prev) => [...prev, errorMessage]);
            setIsLoading(false);
        }
    };

    const addAssistantMessage = useCallback((response: ConstellationResponse, sessionId?: string) => {
        const assistantMessage: Message = {
            id: crypto.randomUUID(),
            role: "assistant",
            content: response.final_response,
            constellation: response,
            timestamp: new Date(),
        };
        setMessages((prev) => {
            const updated = [...prev, assistantMessage];
            // sync to session
            const sid = sessionId || currentSessionId;
            if (sid) {
                setSessions((prevSessions) => {
                    const updatedSessions = prevSessions.map((s) =>
                        s.id === sid
                            ? { ...s, messages: updated, updatedAt: new Date() }
                            : s
                    );
                    saveSessions(updatedSessions);
                    return updatedSessions;
                });
            }
            return updated;
        });
        setPendingResponse(null);
        setProcessState(initialProcessState);
    }, [currentSessionId]);

    const approveCorrection = useCallback((editedResponse?: string) => {
        if (pendingResponse) {
            if (editedResponse) {
                // user made edits
                const response = {
                    ...pendingResponse,
                    final_response: editedResponse,
                };
                addAssistantMessage(response);
            } else {
                addAssistantMessage(pendingResponse);
            }
        }
    }, [pendingResponse, addAssistantMessage]);

    const rejectCorrection = useCallback(() => {
        // if rejected, use the original draft instead
        if (pendingResponse) {
            const response = {
                ...pendingResponse,
                final_response: pendingResponse.draft,
                was_corrected: false
            };
            addAssistantMessage(response);
        }
    }, [pendingResponse, addAssistantMessage]);

    return {
        messages,
        isLoading,
        processState,
        hitlMode,
        setHitlMode,
        pendingResponse,
        send,
        approveCorrection,
        rejectCorrection,
        messagesEndRef,
        // chat history
        sessions,
        currentSessionId,
        startNewSession,
        loadSession,
        deleteSession,
    };
}
