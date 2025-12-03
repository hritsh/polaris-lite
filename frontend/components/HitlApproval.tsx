"use client";

import { ConstellationResponse, AUDITOR_UI_INFO } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { DiffView } from "./DiffView";
import { AlertTriangle, Check, X, Stethoscope, Scale, Edit2, Heart, Baby, Pill } from "lucide-react";
import { useState } from "react";

interface HitlApprovalProps {
    response: ConstellationResponse;
    onApprove: (editedResponse?: string) => void;
    onReject: () => void;
}

// map icon names to components
const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
    Stethoscope,
    Scale,
    Heart,
    Baby,
    Pill,
};

export function HitlApproval({ response, onApprove, onReject }: HitlApprovalProps) {
    const { audits, active_auditors } = response;
    const [isEditing, setIsEditing] = useState(false);
    const [editedText, setEditedText] = useState(response.final_response);

    const handleApprove = () => {
        if (isEditing && editedText !== response.final_response) {
            onApprove(editedText);
        } else {
            onApprove();
        }
    };

    // get auditors that flagged issues
    const flaggedAuditors = (active_auditors || []).filter(
        (id) => audits?.[id] && !audits[id].safe
    );

    return (
        <Card className="p-4 border-amber-500/50 bg-amber-500/5">
            <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="h-5 w-5 text-amber-400" />
                <h4 className="font-medium">Human Approval Required</h4>
            </div>

            <p className="text-sm text-muted-foreground mb-4">
                The safety auditors flagged issues. Review the corrections and decide whether to apply them.
            </p>

            {/* Show what was flagged - dynamic auditors */}
            <div className="space-y-2 mb-4">
                {flaggedAuditors.map((auditorId) => {
                    const audit = audits?.[auditorId];
                    const auditorInfo = AUDITOR_UI_INFO[auditorId];
                    const IconComponent = auditorInfo ? iconMap[auditorInfo.icon] : Stethoscope;

                    if (!audit) return null;

                    return (
                        <div
                            key={auditorId}
                            className={`flex items-start gap-2 p-2 rounded bg-rose-500/10 border border-rose-500/20`}
                        >
                            {IconComponent && (
                                <IconComponent className={`h-4 w-4 mt-0.5 shrink-0 ${auditorInfo?.color || "text-rose-400"}`} />
                            )}
                            <div className="text-sm">
                                <span className={`font-medium ${auditorInfo?.color || "text-rose-400"}`}>
                                    {audit.name || auditorInfo?.name || auditorId}:{" "}
                                </span>
                                <span className="text-muted-foreground">{audit.reasoning}</span>
                                {audit.suggestion && (
                                    <p className={`text-xs mt-1 ${auditorInfo?.color || "text-rose-400"}`}>
                                        → {audit.suggestion}
                                    </p>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Diff or Edit mode */}
            <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                    <p className="text-xs font-medium text-muted-foreground">
                        {isEditing ? "Edit Response:" : "Proposed Changes:"}
                    </p>
                    <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 text-xs gap-1"
                        onClick={() => setIsEditing(!isEditing)}
                    >
                        <Edit2 className="h-3 w-3" />
                        {isEditing ? "View Diff" : "Edit"}
                    </Button>
                </div>

                {isEditing ? (
                    <textarea
                        value={editedText}
                        onChange={(e) => setEditedText(e.target.value)}
                        className="w-full p-3 rounded-md bg-background border border-border text-sm min-h-[200px] resize-y focus:outline-none focus:ring-2 focus:ring-ring"
                        placeholder="Edit the response..."
                    />
                ) : (
                    <div className="p-3 rounded-md bg-background/50 max-h-64 overflow-y-auto">
                        <DiffView original={response.draft} corrected={response.final_response} />
                    </div>
                )}
            </div>

            <div className="flex gap-2 flex-wrap">
                <Button onClick={handleApprove} size="sm" className="gap-1 bg-emerald-600 hover:bg-emerald-700">
                    <Check className="h-4 w-4" />
                    {isEditing && editedText !== response.final_response ? "Approve with Edits" : "Approve Correction"}
                </Button>
                <Button onClick={onReject} variant="outline" size="sm" className="gap-1 border-rose-500/50 text-rose-400 hover:bg-rose-500/10">
                    <X className="h-4 w-4" />
                    Use Original (Risky)
                </Button>
            </div>
        </Card>
    );
}
