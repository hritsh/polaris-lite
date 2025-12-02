"use client";

import { useMemo } from "react";
import { diffWords } from "diff";

interface DiffViewProps {
    original: string;
    corrected: string;
}

export function DiffView({ original, corrected }: DiffViewProps) {
    const diff = useMemo(() => {
        return diffWords(original, corrected);
    }, [original, corrected]);

    return (
        <div className="text-sm leading-relaxed">
            {diff.map((part, idx) => {
                if (part.added) {
                    return (
                        <span
                            key={idx}
                            className="bg-green-500/20 text-green-400 px-0.5 rounded"
                        >
                            {part.value}
                        </span>
                    );
                }
                if (part.removed) {
                    return (
                        <span
                            key={idx}
                            className="bg-red-500/20 text-red-400 line-through px-0.5 rounded"
                        >
                            {part.value}
                        </span>
                    );
                }
                return <span key={idx}>{part.value}</span>;
            })}
        </div>
    );
}
