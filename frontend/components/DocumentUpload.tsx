"use client";

import { useState, useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { 
    FileText, 
    Upload, 
    X, 
    Trash2, 
    FileUp,
    Loader2,
    CheckCircle,
    AlertCircle
} from "lucide-react";

interface Document {
    doc_id: string;
    filename: string;
    chunks: number;
    doc_type: string;
    is_builtin?: boolean;
}

interface DocumentUploadProps {
    backendUrl: string;
}

export function DocumentUpload({ backendUrl }: DocumentUploadProps) {
    const [documents, setDocuments] = useState<Document[]>([]);
    const [isUploading, setIsUploading] = useState(false);
    const [uploadStatus, setUploadStatus] = useState<{
        type: "success" | "error";
        message: string;
    } | null>(null);
    const [isExpanded, setIsExpanded] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Fetch documents on mount
    const fetchDocuments = useCallback(async () => {
        try {
            const res = await fetch(`${backendUrl}/documents`);
            if (res.ok) {
                const data = await res.json();
                setDocuments(data.documents || []);
            }
        } catch (error) {
            console.error("Failed to fetch documents:", error);
        }
    }, [backendUrl]);

    // Upload file
    const handleFileUpload = async (file: File) => {
        if (!file.name.toLowerCase().endsWith(".pdf")) {
            setUploadStatus({ type: "error", message: "Only PDF files are supported" });
            return;
        }

        setIsUploading(true);
        setUploadStatus(null);

        try {
            const formData = new FormData();
            formData.append("file", file);

            const res = await fetch(`${backendUrl}/documents/upload`, {
                method: "POST",
                body: formData,
            });

            const data = await res.json();

            if (res.ok && data.success) {
                setUploadStatus({ 
                    type: "success", 
                    message: `Uploaded "${data.filename}" (${data.chunks} chunks)` 
                });
                fetchDocuments();
            } else {
                setUploadStatus({ 
                    type: "error", 
                    message: data.error || data.message || "Upload failed" 
                });
            }
        } catch (error) {
            setUploadStatus({ type: "error", message: "Failed to upload document" });
        } finally {
            setIsUploading(false);
        }
    };

    // Delete document
    const handleDelete = async (docId: string) => {
        try {
            const res = await fetch(`${backendUrl}/documents/${docId}`, {
                method: "DELETE",
            });
            
            if (res.ok) {
                fetchDocuments();
                setUploadStatus({ type: "success", message: "Document deleted" });
            }
        } catch (error) {
            setUploadStatus({ type: "error", message: "Failed to delete document" });
        }
    };

    // Clear all documents
    const handleClearAll = async () => {
        try {
            const res = await fetch(`${backendUrl}/documents/clear`, {
                method: "POST",
            });
            
            if (res.ok) {
                setDocuments([]);
                setUploadStatus({ type: "success", message: "All documents cleared" });
            }
        } catch (error) {
            setUploadStatus({ type: "error", message: "Failed to clear documents" });
        }
    };

    // Handle drag and drop
    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        const file = e.dataTransfer.files[0];
        if (file) {
            handleFileUpload(file);
        }
    };

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
    };

    // Auto-fetch on expand
    const toggleExpand = () => {
        if (!isExpanded) {
            fetchDocuments();
        }
        setIsExpanded(!isExpanded);
    };

    return (
        <div className="border-b border-border">
            {/* Header button */}
            <button
                onClick={toggleExpand}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-muted/50 transition-colors"
            >
                <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium">
                        RAG Documents
                        {documents.length > 0 && (
                            <span className="ml-2 text-xs text-muted-foreground">
                                ({documents.length})
                            </span>
                        )}
                    </span>
                </div>
                <span className="text-xs text-muted-foreground">
                    {isExpanded ? "−" : "+"}
                </span>
            </button>

            {/* Expanded content */}
            {isExpanded && (
                <div className="px-4 pb-4 space-y-3">
                    {/* Upload area */}
                    <div
                        onDrop={handleDrop}
                        onDragOver={handleDragOver}
                        className="border-2 border-dashed border-muted-foreground/30 rounded-lg p-4 text-center hover:border-primary/50 transition-colors cursor-pointer"
                        onClick={() => fileInputRef.current?.click()}
                    >
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept=".pdf"
                            className="hidden"
                            onChange={(e) => {
                                const file = e.target.files?.[0];
                                if (file) handleFileUpload(file);
                                e.target.value = "";
                            }}
                        />
                        
                        {isUploading ? (
                            <div className="flex flex-col items-center gap-2">
                                <Loader2 className="h-6 w-6 animate-spin text-primary" />
                                <span className="text-sm text-muted-foreground">
                                    Processing...
                                </span>
                            </div>
                        ) : (
                            <div className="flex flex-col items-center gap-2">
                                <FileUp className="h-6 w-6 text-muted-foreground" />
                                <span className="text-sm text-muted-foreground">
                                    Drop PDF or click to upload
                                </span>
                            </div>
                        )}
                    </div>

                    {/* Status message */}
                    {uploadStatus && (
                        <div
                            className={`flex items-center gap-2 text-sm p-2 rounded ${
                                uploadStatus.type === "success"
                                    ? "bg-green-500/10 text-green-600"
                                    : "bg-red-500/10 text-red-600"
                            }`}
                        >
                            {uploadStatus.type === "success" ? (
                                <CheckCircle className="h-4 w-4" />
                            ) : (
                                <AlertCircle className="h-4 w-4" />
                            )}
                            <span className="flex-1">{uploadStatus.message}</span>
                            <button 
                                onClick={() => setUploadStatus(null)}
                                className="hover:opacity-70"
                            >
                                <X className="h-3 w-3" />
                            </button>
                        </div>
                    )}

                    {/* Document list */}
                    {documents.length > 0 && (
                        <div className="space-y-2">
                            {/* Builtin documents */}
                            {documents.filter(d => d.is_builtin).length > 0 && (
                                <div className="space-y-1">
                                    <p className="text-xs text-muted-foreground font-medium">Built-in Knowledge</p>
                                    {documents.filter(d => d.is_builtin).map((doc) => (
                                        <div
                                            key={doc.doc_id}
                                            className="flex items-center gap-2 p-2 bg-blue-500/10 rounded-lg text-sm"
                                        >
                                            <FileText className="h-4 w-4 text-blue-500 shrink-0" />
                                            <span className="flex-1 truncate text-blue-700 dark:text-blue-300">{doc.filename}</span>
                                            <span className="text-xs text-blue-500">
                                                {doc.chunks} chunks
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            )}
                            
                            {/* User uploaded documents */}
                            {documents.filter(d => !d.is_builtin).length > 0 && (
                                <div className="space-y-1">
                                    <p className="text-xs text-muted-foreground font-medium">Your Documents</p>
                                    {documents.filter(d => !d.is_builtin).map((doc) => (
                                        <div
                                            key={doc.doc_id}
                                            className="flex items-center gap-2 p-2 bg-muted/50 rounded-lg text-sm"
                                        >
                                            <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                                            <span className="flex-1 truncate">{doc.filename}</span>
                                            <span className="text-xs text-muted-foreground">
                                                {doc.chunks} chunks
                                            </span>
                                            <button
                                                onClick={() => handleDelete(doc.doc_id)}
                                                className="p-1 hover:bg-muted rounded transition-colors"
                                            >
                                                <Trash2 className="h-3 w-3 text-muted-foreground hover:text-destructive" />
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            )}
                            
                            {documents.filter(d => !d.is_builtin).length > 0 && (
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="w-full text-xs"
                                    onClick={handleClearAll}
                                >
                                    Clear User Documents
                                </Button>
                            )}
                        </div>
                    )}

                    {documents.length === 0 && !isUploading && (
                        <p className="text-xs text-muted-foreground text-center">
                            Upload medical PDFs to enhance responses with RAG
                        </p>
                    )}
                </div>
            )}
        </div>
    );
}
