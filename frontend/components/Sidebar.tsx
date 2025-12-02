"use client";

import { ChatSession } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageSquarePlus, Trash2, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";

interface SidebarProps {
    sessions: ChatSession[];
    currentSessionId: string | null;
    onNewChat: () => void;
    onLoadSession: (id: string) => void;
    onDeleteSession: (id: string) => void;
}

export function Sidebar({
    sessions,
    currentSessionId,
    onNewChat,
    onLoadSession,
    onDeleteSession,
}: SidebarProps) {
    const formatDate = (date: Date) => {
        const now = new Date();
        const diff = now.getTime() - date.getTime();
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));

        if (days === 0) return "Today";
        if (days === 1) return "Yesterday";
        if (days < 7) return `${days} days ago`;
        return date.toLocaleDateString();
    };

    return (
        <div className="w-64 h-full bg-muted/30 border-r border-border flex flex-col shrink-0">
            <div className="p-3 border-b border-border">
                <Button
                    onClick={onNewChat}
                    variant="outline"
                    className="w-full justify-start gap-2"
                >
                    <MessageSquarePlus className="h-4 w-4" />
                    New Chat
                </Button>
            </div>

            <ScrollArea className="flex-1">
                <div className="p-2 space-y-1">
                    {sessions.length === 0 ? (
                        <p className="text-sm text-muted-foreground text-center py-4">
                            No chat history yet
                        </p>
                    ) : (
                        sessions.map((session) => (
                            <div
                                key={session.id}
                                className={cn(
                                    "group flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-colors",
                                    currentSessionId === session.id
                                        ? "bg-accent"
                                        : "hover:bg-accent/50"
                                )}
                                onClick={() => onLoadSession(session.id)}
                            >
                                <MessageSquare className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm line-clamp-2 leading-tight">
                                        {session.title}
                                    </p>
                                    <p className="text-xs text-muted-foreground mt-0.5">
                                        {formatDate(session.updatedAt)}
                                    </p>
                                </div>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        onDeleteSession(session.id);
                                    }}
                                >
                                    <Trash2 className="h-3 w-3 text-muted-foreground hover:text-destructive" />
                                </Button>
                            </div>
                        ))
                    )}
                </div>
            </ScrollArea>
        </div>
    );
}
