"use client";

import { Message } from "@/lib/types";
import { SafetyReport } from "./SafetyReport";
import { User, Bot } from "lucide-react";
import { useMemo } from "react";

interface ChatMessageProps {
    message: Message;
}

// simple markdown parser for bold, italic, lists
function formatMarkdown(text: string) {
    const lines = text.split('\n');
    const elements: React.ReactNode[] = [];

    lines.forEach((line, lineIdx) => {
        // process inline formatting
        const processInline = (str: string): React.ReactNode[] => {
            const parts: React.ReactNode[] = [];
            let remaining = str;
            let keyIdx = 0;

            while (remaining.length > 0) {
                // bold **text**
                const boldMatch = remaining.match(/\*\*(.+?)\*\*/);
                if (boldMatch && boldMatch.index !== undefined) {
                    if (boldMatch.index > 0) {
                        parts.push(remaining.slice(0, boldMatch.index));
                    }
                    parts.push(<strong key={`b-${keyIdx++}`}>{boldMatch[1]}</strong>);
                    remaining = remaining.slice(boldMatch.index + boldMatch[0].length);
                    continue;
                }

                // italic *text*
                const italicMatch = remaining.match(/\*(.+?)\*/);
                if (italicMatch && italicMatch.index !== undefined) {
                    if (italicMatch.index > 0) {
                        parts.push(remaining.slice(0, italicMatch.index));
                    }
                    parts.push(<em key={`i-${keyIdx++}`}>{italicMatch[1]}</em>);
                    remaining = remaining.slice(italicMatch.index + italicMatch[0].length);
                    continue;
                }

                parts.push(remaining);
                break;
            }

            return parts;
        };

        // check for numbered list (1. item)
        const numberedMatch = line.match(/^(\d+)\.\s+(.+)$/);
        if (numberedMatch) {
            elements.push(
                <div key={lineIdx} className="flex gap-2 ml-1">
                    <span className="text-muted-foreground shrink-0">{numberedMatch[1]}.</span>
                    <span>{processInline(numberedMatch[2])}</span>
                </div>
            );
            return;
        }

        // check for bullet list (- item or * item)
        const bulletMatch = line.match(/^[-*]\s+(.+)$/);
        if (bulletMatch) {
            elements.push(
                <div key={lineIdx} className="flex gap-2 ml-1">
                    <span className="text-muted-foreground">•</span>
                    <span>{processInline(bulletMatch[1])}</span>
                </div>
            );
            return;
        }

        // empty line = paragraph break
        if (line.trim() === '') {
            elements.push(<div key={lineIdx} className="h-2" />);
            return;
        }

        // regular line
        elements.push(<div key={lineIdx}>{processInline(line)}</div>);
    });

    return elements;
}

export function ChatMessage({ message }: ChatMessageProps) {
    const isUser = message.role === "user";

    const formattedContent = useMemo(() => {
        if (isUser) return message.content;
        return formatMarkdown(message.content);
    }, [message.content, isUser]);

    return (
        <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
            {/* Avatar */}
            <div
                className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${isUser ? "bg-primary text-primary-foreground" : "bg-muted"
                    }`}
            >
                {isUser ? (
                    <User className="h-4 w-4" />
                ) : (
                    <Bot className="h-4 w-4" />
                )}
            </div>

            {/* Message Content */}
            <div className={`flex-1 max-w-[80%] ${isUser ? "text-right" : ""}`}>
                {/* Safety Report for assistant messages - show FIRST */}
                {!isUser && message.constellation && (
                    <SafetyReport constellation={message.constellation} />
                )}

                {/* Response with title */}
                {!isUser && (
                    <p className="text-xs font-medium text-muted-foreground mt-3 mb-1 flex items-center gap-1.5">
                        <Bot className="h-3 w-3" />
                        Nurse Response
                    </p>
                )}

                <div
                    className={`inline-block p-3 rounded-lg ${isUser
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted"
                        }`}
                >
                    <div className="text-sm">{formattedContent}</div>
                </div>

                {/* Timestamp */}
                <p className="text-xs text-muted-foreground mt-1">
                    {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </p>
            </div>
        </div>
    );
}
