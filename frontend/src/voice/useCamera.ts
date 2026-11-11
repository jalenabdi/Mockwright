import fixWebmDuration from "fix-webm-duration";
import { useCallback, useEffect, useRef, useState } from "react";

export type CameraStatus = "off" | "starting" | "on" | "blocked" | "missing" | "unsupported" | "lost";

export interface Clip {
  video: Blob;
  durationSeconds: number;
}

// Best first. Chrome, Edge and Firefox record WebM; Safari records MP4.
// VP8 before VP9: it's cheaper to encode live and plays back everywhere.
const FORMATS = ["video/webm;codecs=vp8,opus", "video/webm;codecs=vp9,opus", "video/webm", "video/mp4"];

function pickFormat(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined;
  return FORMATS.find((format) => MediaRecorder.isTypeSupported(format));
}

/**
 * The candidate's camera: a live preview plus one recording per answer.
 *
 * The camera is optional. If it's blocked or missing, `status` says so and
 * `startClip` / `stopClip` do nothing, so the interview carries on without video.
 */
export function useCamera() {
  const [status, setStatus] = useState<CameraStatus>("off");
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [recording, setRecording] = useState(false);
  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const startedAtRef = useRef(0);
  const mountedRef = useRef(true);
  const startingRef = useRef(false);

  const start = useCallback(async () => {
    if (streamRef.current || startingRef.current) return;
    if (!navigator.mediaDevices?.getUserMedia || !pickFormat()) {
      setStatus("unsupported");
      return;
    }
    setStatus("starting");
    startingRef.current = true;
    try {
      const media = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
        audio: { echoCancellation: true, noiseSuppression: true },
      });
      if (!mountedRef.current) {
        media.getTracks().forEach((track) => track.stop()); // page closed while asking
        return;
      }
      streamRef.current = media;
      setStream(media);
      setStatus("on");
      // The camera can drop out (unplugged, taken by another app, encoder crash).
      // Say so instead of quietly saving audio-only clips.
      media.getVideoTracks()[0]?.addEventListener("ended", () => {
        if (streamRef.current !== media) return;
        recorderRef.current = null;
        setRecording(false);
        media.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        setStream(null);
        setStatus("lost");
      });
    } catch (caught) {
      const name = caught instanceof DOMException ? caught.name : "";
      if (mountedRef.current) {
        setStatus(name === "NotFoundError" || name === "OverconstrainedError" ? "missing" : "blocked");
      }
    } finally {
      startingRef.current = false;
    }
  }, []);

  const startClip = useCallback(() => {
    const media = streamRef.current;
    const format = pickFormat();
    if (!media || !format || recorderRef.current) return;
    chunksRef.current = [];
    const recorder = new MediaRecorder(media, {
      mimeType: format,
      videoBitsPerSecond: 600_000,
      audioBitsPerSecond: 64_000,
    });
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunksRef.current.push(event.data);
    };
    recorder.start(1000);
    recorderRef.current = recorder;
    startedAtRef.current = performance.now();
    setRecording(true);
  }, []);

  /** Finish the current clip. Resolves to null if nothing was being recorded. */
  const stopClip = useCallback(
    () =>
      new Promise<Clip | null>((resolve) => {
        const recorder = recorderRef.current;
        recorderRef.current = null;
        setRecording(false);
        if (!recorder || recorder.state === "inactive") {
          resolve(null);
          return;
        }
        const durationSeconds = (performance.now() - startedAtRef.current) / 1000;
        recorder.onstop = async () => {
          const type = recorder.mimeType.split(";")[0] || "video/webm";
          let video = new Blob(chunksRef.current, { type });
          chunksRef.current = [];
          if (video.size === 0) {
            resolve(null);
            return;
          }
          // Browsers leave the length out of recorded WebM files, so players
          // can't show it or seek. Write it in before uploading.
          if (type === "video/webm") {
            try {
              video = await fixWebmDuration(video, durationSeconds * 1000, { logger: false });
            } catch {
              // Still playable, just without a known length.
            }
          }
          resolve({ video, durationSeconds });
        };
        recorder.stop();
      }),
    [],
  );

  /** Throw away the current clip (e.g. the answer was empty and will be retried). */
  const discardClip = useCallback(() => {
    const recorder = recorderRef.current;
    recorderRef.current = null;
    setRecording(false);
    if (recorder && recorder.state !== "inactive") {
      recorder.onstop = null;
      recorder.stop();
    }
    chunksRef.current = [];
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      const recorder = recorderRef.current;
      if (recorder && recorder.state !== "inactive") {
        recorder.onstop = null;
        recorder.stop();
      }
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    };
  }, []);

  return { status, stream, recording, start, startClip, stopClip, discardClip };
}
