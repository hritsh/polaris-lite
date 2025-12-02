import { ConstellationResponse, StreamEvent, Message } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:5000";

export async function sendMessage(message: string, history?: Message[]): Promise<ConstellationResponse> {
    const formattedHistory = history?.map(m => ({
        role: m.role,
        content: m.content
    })) || [];

    const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ message, history: formattedHistory }),
    });

    if (!response.ok) {
        throw new Error("Failed to get response from constellation");
    }

    return response.json();
}

export async function sendMessageStream(
    message: string,
    onEvent: (event: StreamEvent) => void,
    history?: Message[]
): Promise<ConstellationResponse> {
    const formattedHistory = history?.map(m => ({
        role: m.role,
        content: m.content
    })) || [];

    const response = await fetch(`${API_URL}/chat/stream`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ message, history: formattedHistory }),
    });

    if (!response.ok) {
        throw new Error("Failed to get response from constellation");
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    let finalResult: ConstellationResponse | null = null;

    if (!reader) {
        throw new Error("No response body");
    }

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");

        for (const line of lines) {
            if (line.startsWith("data: ")) {
                try {
                    const data = JSON.parse(line.slice(6));
                    onEvent(data);

                    if (data.step === "complete" && data.result) {
                        finalResult = data.result;
                    }
                } catch {
                    // ignore parse errors for partial chunks
                }
            }
        }
    }

    if (!finalResult) {
        throw new Error("No final result received");
    }

    return finalResult;
}

export async function checkHealth(): Promise<boolean> {
    try {
        const response = await fetch(`${API_URL}/health`);
        return response.ok;
    } catch {
        return false;
    }
}
