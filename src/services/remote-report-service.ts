import * as FileSystem from "expo-file-system/legacy";

import type { WorkerSafetyReport } from "@/types";
import { getSupabaseClient, isSupabaseConfigured } from "./supabase-client";

const reportAudioBucket = "report-audio";
const reportPhotosBucket = "report-photos";

export interface RemoteReportResult {
  remoteReportId?: string;
  remoteAudioPath?: string;
  remotePhotoPath?: string;
}

export class RemoteReportError extends Error {
  constructor(message = "Unable to sync report to Supabase.") {
    super(message);
    this.name = "RemoteReportError";
  }
}

export async function submitReportToSupabase(
  report: WorkerSafetyReport,
): Promise<RemoteReportResult> {
  if (!isSupabaseConfigured()) {
    return {};
  }

  const remotePhotoPath = await uploadReportMedia(report, "photo");
  const remoteAudioPath = await uploadReportMedia(report, "audio");
  const supabase = getSupabaseClient();
  const { error } = await supabase
    .from("reports")
    .upsert(
      {
        area_or_equipment: report.areaOrEquipment,
        audio_path: remoteAudioPath,
        client_report_id: report.id,
        detected_language: report.detectedLanguage ?? null,
        final_text: report.description,
        original_text: report.reportingMethod === "text" ? report.description : null,
        photo_path: remotePhotoPath,
        report_language: report.language,
        report_type: report.reportingMethod,
        site: report.site,
        status: report.status,
        submitted_at: report.submittedAt,
        sync_status: "synced",
        synced_at: new Date().toISOString(),
        tracking_id: report.trackingId,
        transcribed_text:
          report.reportingMethod === "voice" ? report.description : null,
      },
      { onConflict: "client_report_id" },
    );

  if (error) {
    throw new RemoteReportError(error.message);
  }

  if (report.aiAnalysis) {
    const { error: analysisError } = await supabase
      .from("report_analysis")
      .upsert(
        {
          activity: report.aiAnalysis.activity,
          barrier_failure: report.aiAnalysis.barrierFailure,
          exposure: report.aiAnalysis.exposure,
          hazard: report.aiAnalysis.hazard,
          life_saving_rules: report.aiAnalysis.lifeSavingRules,
          potential_consequence: report.aiAnalysis.potentialConsequence,
          report_client_id: report.id,
        },
        { onConflict: "report_client_id" },
      );

    if (analysisError) {
      throw new RemoteReportError(analysisError.message);
    }
  }

  return {
    remoteAudioPath,
    remotePhotoPath,
  };
}

async function uploadReportMedia(
  report: WorkerSafetyReport,
  type: "audio" | "photo",
): Promise<string | undefined> {
  const uri = type === "audio" ? report.audioUri : report.photoUri;

  if (!uri) {
    return undefined;
  }

  const supabase = getSupabaseClient();
  const bucket = type === "audio" ? reportAudioBucket : reportPhotosBucket;
  const extension = getFileExtension(uri, type);
  const storagePath = `reports/${report.id}/${type}.${extension}`;
  const contentType =
    type === "audio" ? getAudioMimeType(extension) : getImageMimeType(extension);
  const fileBody = await readLocalFileAsArrayBuffer(uri);
  const { error } = await supabase.storage
    .from(bucket)
    .upload(storagePath, fileBody, {
      contentType,
      upsert: true,
    });

  if (error) {
    throw new RemoteReportError(error.message);
  }

  return storagePath;
}

async function readLocalFileAsArrayBuffer(uri: string): Promise<ArrayBuffer> {
  const base64 = await FileSystem.readAsStringAsync(uri, {
    encoding: FileSystem.EncodingType.Base64,
  });

  return base64ToArrayBuffer(base64);
}

function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const lookup = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  const cleanBase64 = base64.replace(/=+$/, "");
  const bytes: number[] = [];

  for (let index = 0; index < cleanBase64.length; index += 4) {
    const encoded1 = lookup.indexOf(cleanBase64[index] ?? "A");
    const encoded2 = lookup.indexOf(cleanBase64[index + 1] ?? "A");
    const encoded3 = lookup.indexOf(cleanBase64[index + 2] ?? "A");
    const encoded4 = lookup.indexOf(cleanBase64[index + 3] ?? "A");
    const triplet =
      (encoded1 << 18) | (encoded2 << 12) | (encoded3 << 6) | encoded4;

    bytes.push((triplet >> 16) & 255);

    if (index + 2 < cleanBase64.length) {
      bytes.push((triplet >> 8) & 255);
    }

    if (index + 3 < cleanBase64.length) {
      bytes.push(triplet & 255);
    }
  }

  return Uint8Array.from(bytes).buffer;
}

function getFileExtension(uri: string, type: "audio" | "photo"): string {
  const cleanUri = uri.split("?")[0] ?? uri;
  const extension = cleanUri.split(".").pop()?.toLowerCase();

  if (extension && extension.length <= 5 && !extension.includes("/")) {
    return extension === "jpeg" ? "jpg" : extension;
  }

  return type === "audio" ? "m4a" : "jpg";
}

function getAudioMimeType(extension: string): string {
  if (extension === "webm") {
    return "audio/webm";
  }

  if (extension === "wav") {
    return "audio/wav";
  }

  if (extension === "caf") {
    return "audio/x-caf";
  }

  return "audio/m4a";
}

function getImageMimeType(extension: string): string {
  if (extension === "png") {
    return "image/png";
  }

  if (extension === "heic") {
    return "image/heic";
  }

  if (extension === "webp") {
    return "image/webp";
  }

  return "image/jpeg";
}
