"use client";

import { ProcessState } from "@/lib/types";
import { Check, Loader2, AlertTriangle, Stethoscope, Scale, Sparkles, Bot, X, CheckCircle2 } from "lucide-react";

interface ProcessLogProps {
    processState: ProcessState;
    isLoading: boolean;
}

type StepStatus = "pending" | "active" | "complete" | "skipped";

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

                {/* Medical Audit Step */}
                <div className={`flex items-start gap-3 ${processState.medical_check === "pending" ? "opacity-40" : ""}`}>
                    {getStatusIcon(processState.medical_check)}
                    <div className="flex-1">
                        <div className="flex items-center gap-2">
                            <Stethoscope className="h-4 w-4 text-rose-400" />
                            <span className="text-sm font-medium">Medical Auditor</span>
                            {processState.medical_check === "complete" && getAuditResultIcon(processState.medicalResult?.safe)}
                        </div>
                        {processState.medicalResult && (
                            <p className="text-xs text-muted-foreground mt-1">
                                {processState.medicalResult.reasoning}
                            </p>
                        )}
                    </div>
                </div>

                {/* Legal Audit Step */}
                <div className={`flex items-start gap-3 ${processState.legal_check === "pending" ? "opacity-40" : ""}`}>
                    {getStatusIcon(processState.legal_check)}
                    <div className="flex-1">
                        <div className="flex items-center gap-2">
                            <Scale className="h-4 w-4 text-purple-400" />
                            <span className="text-sm font-medium">Legal Auditor</span>
                            {processState.legal_check === "complete" && getAuditResultIcon(processState.legalResult?.safe)}
                        </div>
                        {processState.legalResult && (
                            <p className="text-xs text-muted-foreground mt-1">
                                {processState.legalResult.reasoning}
                            </p>
                        )}
                    </div>
                </div>

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
