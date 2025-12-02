"use client";

import { useChat } from "@/hooks/useChat";
import { Header } from "@/components/Header";
import { Sidebar } from "@/components/Sidebar";
import { ChatMessage } from "@/components/ChatMessage";
import { ChatInput } from "@/components/ChatInput";
import { ProcessLog } from "@/components/ProcessLog";
import { HitlApproval } from "@/components/HitlApproval";
import { Bot, MessageCircle, AlertTriangle, PanelLeftClose, PanelLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useState, useEffect } from "react";

// example queries that will trigger safety corrections
const EXAMPLE_QUERIES = [
    "What can I do for a headache?",
    "Can I take 1000mg of ibuprofen for pain?",  // will trigger medical flag - dangerous dosage
    "I have chest pain, what should I do?",  // might trigger urgency flags
];

export function Chat() {
    const {
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
        sessions,
        currentSessionId,
        startNewSession,
        loadSession,
        deleteSession,
    } = useChat();

    // responsive: default sidebar closed on mobile
    const [sidebarOpen, setSidebarOpen] = useState(false);

    useEffect(() => {
        // check if we're on desktop
        const checkWidth = () => {
            setSidebarOpen(window.innerWidth >= 768);
        };
        checkWidth();
        window.addEventListener("resize", checkWidth);
        return () => window.removeEventListener("resize", checkWidth);
    }, []);

    // close sidebar when selecting a chat on mobile
    const handleLoadSession = (id: string) => {
        loadSession(id);
        if (window.innerWidth < 768) {
            setSidebarOpen(false);
        }
    };

    return (
        <div className="flex h-screen bg-background overflow-hidden">
            {/* Sidebar - overlay on mobile */}
            {sidebarOpen && (
                <>
                    {/* Backdrop on mobile */}
                    <div
                        className="fixed inset-0 bg-black/50 z-30 md:hidden"
                        onClick={() => setSidebarOpen(false)}
                    />
                    <div className="fixed md:relative z-40 h-full">
                        <Sidebar
                            sessions={sessions}
                            currentSessionId={currentSessionId}
                            onNewChat={startNewSession}
                            onLoadSession={handleLoadSession}
                            onDeleteSession={deleteSession}
                        />
                    </div>
                </>
            )}

            <div className="flex flex-col flex-1 min-w-0">
                <Header hitlMode={hitlMode} onHitlChange={setHitlMode} />

                {/* Toggle sidebar button */}
                <Button
                    variant="ghost"
                    size="icon"
                    className="fixed top-3 left-3 z-50 h-8 w-8 md:top-4 md:left-4"
                    onClick={() => setSidebarOpen(!sidebarOpen)}
                >
                    {sidebarOpen ? (
                        <PanelLeftClose className="h-4 w-4" />
                    ) : (
                        <PanelLeft className="h-4 w-4" />
                    )}
                </Button>

                <main className="flex-1 overflow-y-auto">
                    <div className="max-w-4xl mx-auto px-3 py-4 md:px-4 md:py-6">
                        {messages.length === 0 ? (
                            // Empty state
                            <div className="h-[60vh] flex flex-col items-center justify-center text-center px-2 md:px-4">
                                <div className="w-14 h-14 md:w-16 md:h-16 rounded-full bg-muted flex items-center justify-center mb-4">
                                    <Bot className="h-7 w-7 md:h-8 md:w-8 text-muted-foreground" />
                                </div>
                                <h2 className="text-lg md:text-xl font-medium mb-2">Welcome to Polaris Lite</h2>
                                <p className="text-sm md:text-base text-muted-foreground max-w-md mb-6">
                                    Ask me any health-related question. Every response is checked by
                                    multiple safety auditors before reaching you.
                                </p>
                                <div className="space-y-3 w-full max-w-md">
                                    <p className="text-xs text-muted-foreground">Try these examples:</p>
                                    <div className="flex flex-col gap-2">
                                        {EXAMPLE_QUERIES.map((suggestion, idx) => (
                                            <button
                                                key={suggestion}
                                                onClick={() => send(suggestion)}
                                                className="px-3 py-2 md:px-4 md:py-2.5 text-sm bg-muted hover:bg-muted/80 rounded-lg transition-colors text-left flex items-center gap-2"
                                            >
                                                <span className="flex-1">{suggestion}</span>
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        ) : (
                            // Messages
                            <div className="space-y-4 md:space-y-6 pb-32">
                                {messages.map((message) => (
                                    <ChatMessage key={message.id} message={message} />
                                ))}

                                {/* Process log - show during loading OR for HITL pending */}
                                {(isLoading || pendingResponse) && (
                                    <ProcessLog
                                        processState={processState}
                                        isLoading={isLoading}
                                    />
                                )}

                                {/* HITL approval panel */}
                                {pendingResponse && !isLoading && (
                                    <HitlApproval
                                        response={pendingResponse}
                                        onApprove={approveCorrection}
                                        onReject={rejectCorrection}
                                    />
                                )}

                                <div ref={messagesEndRef} />
                            </div>
                        )}
                    </div>
                </main>

                {/* Input area - fixed at bottom */}
                <div className="sticky bottom-0 border-t border-border/50 p-3 md:p-4 bg-background/95 backdrop-blur-sm">
                    <div className="max-w-4xl mx-auto">
                        <ChatInput onSend={send} disabled={isLoading || !!pendingResponse} />
                        <p className="text-xs text-muted-foreground text-center mt-2 hidden sm:block">
                            <MessageCircle className="h-3 w-3 inline mr-1" />
                            Responses verified by Medical & Legal auditors
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
