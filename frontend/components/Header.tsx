"use client";

import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/components/ui/tooltip";
import { Shield, Github, Moon, Sun, Loader2, BookOpen } from "lucide-react";
import { useEffect, useState } from "react";
import Image from "next/image";
import { checkHealth, API_URL } from "@/lib/api";

interface HeaderProps {
    hitlMode: boolean;
    onHitlChange: (value: boolean) => void;
    ragMode?: boolean;
    onRagChange?: (value: boolean) => void;
}

export function Header({ hitlMode, onHitlChange, ragMode = false, onRagChange }: HeaderProps) {
    const [darkMode, setDarkMode] = useState(() => {
        if (typeof window !== "undefined") {
            const saved = localStorage.getItem("theme");
            if (saved) {
                return saved === "dark";
            } else {
                return window.matchMedia("(prefers-color-scheme: dark)").matches;
            }
        }
        return true;
    });
    const [backendStatus, setBackendStatus] = useState<"connecting" | "online" | "offline">("connecting");

    useEffect(() => {
        if (darkMode) {
            document.documentElement.classList.add("dark");
            localStorage.setItem("theme", "dark");
        } else {
            document.documentElement.classList.remove("dark");
            localStorage.setItem("theme", "light");
        }
    }, [darkMode]);

    // check backend health on mount
    useEffect(() => {
        const checkBackend = async () => {
            setBackendStatus("connecting");
            const isHealthy = await checkHealth();
            setBackendStatus(isHealthy ? "online" : "offline");
        };
        checkBackend();
    }, []);

    return (
        <header className="border-b border-border/50 bg-card/50 backdrop-blur-sm sticky top-0 z-10">
            <div className="max-w-4xl mx-auto px-4 py-3 md:py-4 flex items-center justify-between">
                <div className="flex items-center gap-2 md:gap-3 ml-10 md:ml-12">
                    <Image
                        src="/constellation.svg"
                        alt="Constellation"
                        width={40}
                        height={40}
                        className="w-8 h-8 md:w-10 md:h-10 rounded-lg"
                    />
                    <div>
                        <h1 className="font-semibold text-base md:text-lg">Polaris Lite</h1>
                        <p className="text-xs text-muted-foreground hidden sm:block">Multi-Agent Safety Chatbot</p>
                    </div>
                </div>

                <div className="flex items-center gap-2 md:gap-4">
                    {/* Backend status badge */}
                    <TooltipProvider>
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <Badge
                                    variant="outline"
                                    className={`text-xs gap-1.5 cursor-help ${backendStatus === "connecting"
                                        ? "border-amber-500/50 text-amber-400"
                                        : backendStatus === "online"
                                            ? "border-emerald-500/50 text-emerald-400"
                                            : "border-rose-500/50 text-rose-400"
                                        }`}
                                >
                                    {backendStatus === "connecting" ? (
                                        <>
                                            <Loader2 className="h-3 w-3 animate-spin" />
                                            <span className="hidden sm:inline">Connecting</span>
                                        </>
                                    ) : backendStatus === "online" ? (
                                        <>
                                            <span className="h-2 w-2 rounded-full bg-emerald-400" />
                                            <span className="hidden sm:inline">Online</span>
                                        </>
                                    ) : (
                                        <>
                                            <span className="h-2 w-2 rounded-full bg-rose-400" />
                                            <span className="hidden sm:inline">Offline</span>
                                        </>
                                    )}
                                </Badge>
                            </TooltipTrigger>
                            <TooltipContent side="bottom" className="max-w-xs">
                                {backendStatus === "connecting" ? (
                                    <p>Backend is waking up from sleep. This may take 30+ seconds on first load.</p>
                                ) : backendStatus === "online" ? (
                                    <p>Backend is online and ready.</p>
                                ) : (
                                    <p>Could not connect to backend. Please try again later.</p>
                                )}
                            </TooltipContent>
                        </Tooltip>
                    </TooltipProvider>

                    <div className="flex items-center gap-2">
                        <Shield className="h-4 w-4 text-muted-foreground hidden sm:block" />
                        <span className="text-sm text-muted-foreground hidden sm:inline">HITL</span>
                        <Switch
                            checked={hitlMode}
                            onCheckedChange={onHitlChange}
                        />
                    </div>
                    {hitlMode && (
                        <Badge variant="secondary" className="text-xs hidden md:flex">
                            Manual Approval
                        </Badge>
                    )}

                    {/* RAG Toggle */}
                    {onRagChange && (
                        <TooltipProvider>
                            <Tooltip>
                                <TooltipTrigger asChild>
                                    <div className="flex items-center gap-2">
                                        <BookOpen className={`h-4 w-4 ${ragMode ? 'text-blue-500' : 'text-muted-foreground'} hidden sm:block`} />
                                        <span className="text-sm text-muted-foreground hidden sm:inline">RAG</span>
                                        <Switch
                                            checked={ragMode}
                                            onCheckedChange={onRagChange}
                                        />
                                    </div>
                                </TooltipTrigger>
                                <TooltipContent side="bottom">
                                    <p>{ragMode ? "RAG enabled (slower, uses knowledge base)" : "RAG disabled (faster responses)"}</p>
                                </TooltipContent>
                            </Tooltip>
                        </TooltipProvider>
                    )}

                    <div className="flex items-center gap-1">
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setDarkMode(!darkMode)}
                            className="h-8 w-8"
                        >
                            {darkMode ? (
                                <Sun className="h-4 w-4" />
                            ) : (
                                <Moon className="h-4 w-4" />
                            )}
                        </Button>
                        <Button
                            variant="ghost"
                            size="icon"
                            asChild
                            className="h-8 w-8"
                        >
                            <a
                                href="https://github.com/hritsh/polaris-lite"
                                target="_blank"
                                rel="noopener noreferrer"
                            >
                                <Github className="h-4 w-4" />
                            </a>
                        </Button>
                    </div>
                </div>
            </div>
        </header>
    );
}
