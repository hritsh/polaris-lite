"use client";

import { ConstellationResponse } from "@/lib/types";
import {
    Accordion,
    AccordionContent,
    AccordionItem,
    AccordionTrigger,
} from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { DiffView } from "./DiffView";
import { AlertTriangle, CheckCircle, Stethoscope, Scale, Bot, Sparkles } from "lucide-react";

interface SafetyReportProps {
    constellation: ConstellationResponse;
}

export function SafetyReport({ constellation }: SafetyReportProps) {
    const { draft, medical_audit, legal_audit, final_response, was_corrected } = constellation;

    return (
        <Accordion type="single" collapsible className="mt-3" defaultValue={was_corrected ? "safety" : undefined}>
            <AccordionItem value="safety" className="border-border/50 rounded-lg bg-muted/30">
                <AccordionTrigger className="text-sm py-2 px-3 hover:no-underline">
                    <div className="flex items-center gap-2">
                        <Sparkles className="h-4 w-4 text-blue-400" />
                        <span className="text-muted-foreground">Reasoning Chain</span>
                        {was_corrected ? (
                            <Badge variant="outline" className="text-xs bg-amber-500/10 text-amber-400 border-amber-500/30">
                                Corrected
                            </Badge>
                        ) : (
                            <Badge variant="outline" className="text-xs bg-emerald-500/10 text-emerald-400 border-emerald-500/30">
                                Passed
                            </Badge>
                        )}
                    </div>
                </AccordionTrigger>
                <AccordionContent className="px-3 pb-3">
                    <div className="space-y-3">
                        {/* Nurse Draft */}
                        <div className="flex items-start gap-2 p-3 rounded-md bg-background/50">
                            <Bot className="h-4 w-4 mt-0.5 text-blue-400 shrink-0" />
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1">
                                    <span className="text-sm font-medium">Nurse Agent</span>
                                    <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />
                                </div>
                                <p className="text-xs text-muted-foreground">Draft generated</p>
                            </div>
                        </div>

                        {/* Medical Audit */}
                        <div className="flex items-start gap-2 p-3 rounded-md bg-background/50">
                            <Stethoscope className="h-4 w-4 mt-0.5 text-rose-400 shrink-0" />
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1">
                                    <span className="text-sm font-medium">Medical Auditor</span>
                                    {medical_audit.safe ? (
                                        <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />
                                    ) : (
                                        <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
                                    )}
                                </div>
                                {medical_audit.reasoning && (
                                    <p className="text-xs text-muted-foreground">{medical_audit.reasoning}</p>
                                )}
                                {medical_audit.suggestion && (
                                    <p className="text-xs text-amber-400 mt-1">→ {medical_audit.suggestion}</p>
                                )}
                            </div>
                        </div>

                        {/* Legal Audit */}
                        <div className="flex items-start gap-2 p-3 rounded-md bg-background/50">
                            <Scale className="h-4 w-4 mt-0.5 text-purple-400 shrink-0" />
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1">
                                    <span className="text-sm font-medium">Legal Auditor</span>
                                    {legal_audit.safe ? (
                                        <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />
                                    ) : (
                                        <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
                                    )}
                                </div>
                                {legal_audit.reasoning && (
                                    <p className="text-xs text-muted-foreground">{legal_audit.reasoning}</p>
                                )}
                                {legal_audit.suggestion && (
                                    <p className="text-xs text-amber-400 mt-1">→ {legal_audit.suggestion}</p>
                                )}
                            </div>
                        </div>

                        {/* Diff View if corrected */}
                        {was_corrected && (
                            <div className="border-t border-border/50 pt-3">
                                <h5 className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1">
                                    <AlertTriangle className="h-3 w-3 text-amber-400" />
                                    Changes Applied:
                                </h5>
                                <div className="p-3 rounded-md bg-background/50 overflow-x-auto">
                                    <DiffView original={draft} corrected={final_response} />
                                </div>
                            </div>
                        )}
                    </div>
                </AccordionContent>
            </AccordionItem>
        </Accordion>
    );
}
