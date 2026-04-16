import OpenAI from "openai";

if (!process.env.OXLO_API_KEY) {
  throw new Error("OXLO_API_KEY is not set in environment variables");
}

export const oxloClient = new OpenAI({
  baseURL: "https://api.oxlo.ai/v1",
  apiKey: process.env.OXLO_API_KEY,
});

export { AVAILABLE_MODELS, type ModelId } from "./models";

function buildMessages(prompt: string, systemPrompt?: string) {
  const messages: Array<{ role: "system" | "user"; content: string }> = [];
  if (systemPrompt) {
    messages.push({ role: "system", content: systemPrompt });
  }
  messages.push({ role: "user", content: prompt });
  return messages;
}

export async function generateCompletion(
  prompt: string,
  systemPrompt?: string,
  model: string = "llama-3.3-70b",
  apiKey?: string
): Promise<string> {
  const client = apiKey ? new OpenAI({ baseURL: "https://api.oxlo.ai/v1", apiKey }) : oxloClient;
  const response = await client.chat.completions.create({
    model,
    messages: buildMessages(prompt, systemPrompt),
    temperature: 0.7,
    max_tokens: 4096,
  });

  return response.choices[0]?.message?.content || "";
}

export async function generateStreamingCompletion(
  prompt: string,
  systemPrompt?: string,
  model: string = "llama-3.3-70b",
  apiKey?: string
): Promise<ReadableStream<Uint8Array>> {
  const client = apiKey ? new OpenAI({ baseURL: "https://api.oxlo.ai/v1", apiKey }) : oxloClient;
  const stream = await client.chat.completions.create({
    model,
    messages: buildMessages(prompt, systemPrompt),
    temperature: 0.7,
    max_tokens: 4096,
    stream: true,
  });

  const encoder = new TextEncoder();

  return new ReadableStream({
    async start(controller) {
      try {
        for await (const chunk of stream) {
          const content = chunk.choices[0]?.delta?.content;
          if (content) {
            controller.enqueue(encoder.encode(content));
          }
        }
        controller.close();
      } catch (error) {
        controller.error(error);
      }
    },
  });
}
