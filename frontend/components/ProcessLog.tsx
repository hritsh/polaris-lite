"use client";

import { ProcessState, AUDITOR_UI_INFO } from "@/lib/types";
import { Check, Loader2, AlertTriangle, Stethoscope, Scale, Sparkles, Bot, X, CheckCircle2, Heart, Baby, Pill } from "lucide-react";

interface ProcessLogProps {
    processState: ProcessState;
    isLoading: boolean;
}

type StepStatus = "pending" | "active" | "complete" | "skipped";

// map icon names to components
const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
    Stethoscope,
    Scale,
    Heart,
    Baby,
    Pill,
};

export function ProcessLog({ processState, isLoading }: ProcessLogProps) {
    // don't show if nothing has started
    if (processState.drafting === "pending" && !isLoading) return null;

    const getStatusIcon = (status: StepStatus) => {
        switch (status) {
            case "active":
                return <Loader2 className="h-4 w-4 animate-spin text-blue-400" />;
            case "complete":
                return <Check className="h-4 w-4 text-emerald-400" />;
            case "skipped":
                return <X className="h-4 w-4 text-muted-foreground" />;
            default:
                return <div className="h-4 w-4 rounded-full border border-muted-foreground/30" />;
        }
    };

    const getAuditResultIcon = (safe: boolean | undefined) => {
        if (safe === undefined) return null;
        return safe ? (
            <Check className="h-3.5 w-3.5 text-emerald-400" />
        ) : (
            <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
        );
    };

    // get active auditors from process state
    const activeAuditors = processState.activeAuditors || [];

    return (
        <div className="bg-muted/50 rounded-lg p-4 border border-border/50">
            <h4 className="text-sm font-medium mb-3 text-muted-foreground flex items-center gap-2">
                {isLoading ? (
                    <>
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        Processing through safety constellation...
                    </>
                ) : (
                    <>
                        <Sparkles className="h-3.5 w-3.5" />
                        Reasoning Chain
                    </>
                )}
            </h4>

            <div className="space-y-3">
                {/* Drafting Step */}
                <div className={`flex items-start gap-3 ${processState.drafting === "pending" ? "opacity-40" : ""}`}>
                    {getStatusIcon(processState.drafting)}
                    <div className="flex-1">
                        <div className="flex items-center gap-2">
                            <Bot className="h-4 w-4 text-blue-400" />
                            <span className="text-sm font-medium">Nurse Agent</span>
                        </div>
                        {processState.drafting === "complete" && (
                            <p className="text-xs text-muted-foreground mt-1">
                                Draft response generated
                            </p>
                        )}
                    </div>
                </div>

                {/* Dynamic Auditor Steps */}
                {activeAuditors.map((auditorId) => {
                    const auditorInfo = AUDITOR_UI_INFO[auditorId];
                    const state = processState.auditorStates[auditorId] || "pending";
                    const result = processState.auditorResults[auditorId];
                    const IconComponent = auditorInfo ? iconMap[auditorInfo.icon] : Stethoscope;

                    return (
                        <div
                            key={auditorId}
                            className={`flex items-start gap-3 transition-all duration-300 ${state === "pending" ? "opacity-40" : ""}`}
                        >
                            {getStatusIcon(state)}
                            <div className="flex-1">
                                <div className="flex items-center gap-2">
                                    {IconComponent && (
                                        <IconComponent className={`h-4 w-4 ${auditorInfo?.color || "text-muted-foreground"}`} />
                                    )}
                                    <span className="text-sm font-medium">
                                        {auditorInfo?.name || auditorId}
                                    </span>
                                    {state === "complete" && getAuditResultIcon(result?.safe)}
                                </div>
                                {result && (
                                    <p className="text-xs text-muted-foreground mt-1">
                                        {result.reasoning}
                                    </p>
                                )}
                            </div>
                        </div>
                    );
                })}

                {/* Show placeholder when auditors haven't been determined yet */}
                {activeAuditors.length === 0 && processState.drafting === "complete" && (
                    <div className="flex items-start gap-3 opacity-40">
                        <Loader2 className="h-4 w-4 animate-spin text-blue-400" />
                        <div className="flex-1">
                            <span className="text-sm font-medium text-muted-foreground">
                                Determining required auditors...
                            </span>
                        </div>
                    </div>
                )}

                {/* Correction Step - only show if needed */}
                {processState.correcting !== "pending" && processState.correcting !== "skipped" && (
                    <div className="flex items-start gap-3">
                        {getStatusIcon(processState.correcting)}
                        <div className="flex-1">
                            <div className="flex items-center gap-2">
                                <AlertTriangle className="h-4 w-4 text-yellow-400" />
                                <span className="text-sm font-medium">Safety Correction</span>
                            </div>
                            {processState.correcting === "complete" && (
                                <p className="text-xs text-muted-foreground mt-1">
                                    Response revised based on auditor feedback
                                </p>
                            )}
                        </div>
                    </div>
                )}

                {/* Finalizing Step */}
                {processState.finalizing !== "pending" && (
                    <div className="flex items-start gap-3">
                        {getStatusIcon(processState.finalizing)}
                        <div className="flex-1">
                            <div className="flex items-center gap-2">
                                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                                <span className="text-sm font-medium">Finalizing</span>
                            </div>
                            {processState.finalizing === "complete" && (
                                <p className="text-xs text-muted-foreground mt-1">
                                    Safety verification complete
                                </p>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
