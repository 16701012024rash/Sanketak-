declare const Deno: {
  env: {
    get(name: string): string | undefined;
  };
  serve(handler: (request: Request) => Promise<Response> | Response): void;
};

const corsHeaders = {
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Origin": "*",
};

interface VoiceAnalysis {
  activity: string;
  hazard: string;
  exposure: string;
  barrier_failure: string;
  potential_consequence: string;
  life_saving_rules: string[];
}

type DenoFormData = {
  get(name: string): File | string | null;
};

Deno.serve(async (request) => {
  if (request.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  if (request.method !== "POST") {
    return json({ error: "Method not allowed." }, 405);
  }

  try {
    const openAiKey = Deno.env.get("OPENAI_API_KEY");

    if (!openAiKey) {
      return json({ error: "OPENAI_API_KEY is not configured." }, 500);
    }

    const formData = (await request.formData()) as unknown as DenoFormData;
    const audio = formData.get("audio");
    const language = String(formData.get("language") ?? "en");

    if (!(audio instanceof File)) {
      return json({ error: "Audio file is required." }, 400);
    }

    const transcript = await transcribeAudio(audio, language, openAiKey);
    const analysis = await analyseSafetyReport(transcript, openAiKey);

    return json({
      analysis,
      detected_language: language,
      transcript,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error.";
    return json({ error: message }, 500);
  }
});

async function transcribeAudio(
  audio: File,
  language: string,
  openAiKey: string,
): Promise<string> {
  const body = new FormData();

  body.append("file", audio, audio.name || "voice-report.m4a");
  body.append("model", "gpt-4o-mini-transcribe");
  body.append(
    "prompt",
    getTranscriptionPrompt(language),
  );

  const response = await fetch("https://api.openai.com/v1/audio/transcriptions", {
    body,
    headers: {
      Authorization: `Bearer ${openAiKey}`,
    },
    method: "POST",
  });

  if (!response.ok) {
    throw new Error(`OpenAI transcription failed with ${response.status}.`);
  }

  const payload = await response.json();
  const text = typeof payload.text === "string" ? payload.text.trim() : "";

  if (!text) {
    throw new Error("OpenAI transcription returned empty text.");
  }

  return text;
}

async function analyseSafetyReport(
  transcript: string,
  openAiKey: string,
): Promise<VoiceAnalysis> {
  const response = await fetch("https://api.openai.com/v1/responses", {
    body: JSON.stringify({
      input: [
        {
          content:
            "Classify this OIL workplace safety observation. Return only compact JSON with keys activity, hazard, exposure, barrier_failure, potential_consequence, life_saving_rules. life_saving_rules must be an array of strings.",
          role: "system",
        },
        {
          content: transcript,
          role: "user",
        },
      ],
      max_output_tokens: 450,
      model: "gpt-5-mini",
    }),
    headers: {
      Authorization: `Bearer ${openAiKey}`,
      "Content-Type": "application/json",
    },
    method: "POST",
  });

  if (!response.ok) {
    return createFallbackAnalysis(transcript);
  }

  const payload = await response.json();
  const text = extractResponseText(payload);

  if (!text) {
    return createFallbackAnalysis(transcript);
  }

  try {
    return normalizeAnalysis(JSON.parse(stripCodeFence(text)));
  } catch {
    return createFallbackAnalysis(transcript);
  }
}

function extractResponseText(payload: unknown): string | undefined {
  if (!payload || typeof payload !== "object") {
    return undefined;
  }

  const response = payload as {
    output_text?: unknown;
    output?: Array<{ content?: Array<{ text?: unknown; type?: unknown }> }>;
  };

  if (typeof response.output_text === "string") {
    return response.output_text;
  }

  return response.output
    ?.flatMap((item) => item.content ?? [])
    .map((content) => content.text)
    .find((text): text is string => typeof text === "string");
}

function normalizeAnalysis(value: unknown): VoiceAnalysis {
  if (!value || typeof value !== "object") {
    throw new Error("Invalid analysis.");
  }

  const analysis = value as Partial<Record<keyof VoiceAnalysis, unknown>>;
  const rules = Array.isArray(analysis.life_saving_rules)
    ? analysis.life_saving_rules.filter((item): item is string => typeof item === "string")
    : [];

  return {
    activity: readAnalysisString(analysis.activity, "General Work Activity"),
    barrier_failure: readAnalysisString(
      analysis.barrier_failure,
      "Safety concern needs review",
    ),
    exposure: readAnalysisString(analysis.exposure, "Worker exposure needs review"),
    hazard: readAnalysisString(analysis.hazard, "Unsafe condition"),
    life_saving_rules: rules.length ? rules : ["Follow site safety controls"],
    potential_consequence: readAnalysisString(
      analysis.potential_consequence,
      "Potential injury or incident",
    ),
  };
}

function readAnalysisString(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

function createFallbackAnalysis(transcript: string): VoiceAnalysis {
  const lowerTranscript = transcript.toLowerCase();
  const isolationIssue =
    lowerTranscript.includes("isolation") ||
    lowerTranscript.includes("loto") ||
    lowerTranscript.includes("lockout");

  if (isolationIssue) {
    return {
      activity: "Maintenance",
      barrier_failure: "Energy isolation not verified",
      exposure: "Workers may be exposed during maintenance",
      hazard: "Stored Energy",
      life_saving_rules: ["Energy Isolation"],
      potential_consequence: "Serious or fatal injury",
    };
  }

  return {
    activity: "Workplace Observation",
    barrier_failure: "Safety control needs review",
    exposure: "Workers may be exposed to an unsafe condition",
    hazard: "Unsafe Condition",
    life_saving_rules: ["Stop Work Authority"],
    potential_consequence: "Injury or incident if not corrected",
  };
}

function getTranscriptionPrompt(language: string): string {
  if (language === "hi") {
    return "The speaker may use Hindi, English, or Hinglish workplace safety terms.";
  }

  if (language === "as") {
    return "The speaker may use Assamese, Hindi, English, or oilfield workplace safety terms.";
  }

  return "The speaker is reporting an oil and gas workplace safety observation.";
}

function stripCodeFence(text: string): string {
  return text
    .replace(/^```json\s*/i, "")
    .replace(/^```\s*/i, "")
    .replace(/```$/i, "")
    .trim();
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    headers: {
      ...corsHeaders,
      "Content-Type": "application/json",
    },
    status,
  });
}
