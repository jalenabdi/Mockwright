import { useCallback, useEffect, useRef, useState } from "react";

import { getToken, WS_URL } from "../lib/api";

export type VoiceStatus = "idle" | "connecting" | "listening" | "finishing";

export type VoiceErrorCode = "mic_blocked" | "no_mic" | "voice_unavailable" | "voice_failed" | "session_expired";

const METER_BARS = 28;
const FINISH_TIMEOUT_MS = 6000;

interface ServerEvent {
  type: string;
  text?: string;
  is_final?: boolean;
  code?: string;
  message?: string;
}

function joinTranscript(current: string, addition: string): string {
  const next = addition.trim();
  if (!next) return current;
  return current ? `${current.trimEnd()} ${next}` : next;
}

/**
 * Streams the microphone to the backend voice socket and collects a transcript.
 *
 * Protocol: see backend/app/routers/voice.py. Audio goes up as PCM16 mono 16 kHz
 * frames; transcript events come back. The transcript is only saved when the
 * user presses "Save Answer", through the same endpoint as typed answers.
 */
export function useVoiceAnswer(interviewId: number) {
  const [status, setStatus] = useState<VoiceStatus>("idle");
  const [transcript, setTranscript] = useState("");
  const [interim, setInterimState] = useState("");
  const interimRef = useRef("");
  const setInterim = useCallback((value: string) => {
    interimRef.current = value;
    setInterimState(value);
  }, []);
  const [levels, setLevels] = useState<number[]>(() => Array(METER_BARS).fill(0));
  const [error, setError] = useState<{ code: VoiceErrorCode; message: string } | null>(null);

  const statusRef = useRef<VoiceStatus>("idle");
  const socketRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const finishTimerRef = useRef<number | null>(null);

  const updateStatus = useCallback((next: VoiceStatus) => {
    statusRef.current = next;
    setStatus(next);
  }, []);

  const stopAudio = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    const context = audioContextRef.current;
    audioContextRef.current = null;
    if (context && context.state !== "closed") void context.close().catch(() => undefined);
    setLevels(Array(METER_BARS).fill(0));
  }, []);

  const teardown = useCallback(() => {
    stopAudio();
    if (finishTimerRef.current !== null) {
      window.clearTimeout(finishTimerRef.current);
      finishTimerRef.current = null;
    }
    const socket = socketRef.current;
    socketRef.current = null;
    if (socket && socket.readyState <= WebSocket.OPEN) socket.close(1000);
    setInterim("");
    updateStatus("idle");
  }, [setInterim, stopAudio, updateStatus]);

  const fail = useCallback(
    (code: VoiceErrorCode, message: string) => {
      setError({ code, message });
      teardown();
    },
    [teardown],
  );

  const startAudio = useCallback(
    async (socket: WebSocket, stream: MediaStream) => {
      const context = new AudioContext();
      audioContextRef.current = context;
      await context.audioWorklet.addModule("/pcm-worklet.js");
      const source = context.createMediaStreamSource(stream);
      const capture = new AudioWorkletNode(context, "pcm-capture");
      // A silent sink keeps the graph running in every browser.
      const sink = context.createGain();
      sink.gain.value = 0;
      source.connect(capture);
      capture.connect(sink);
      sink.connect(context.destination);

      capture.port.onmessage = (event: MessageEvent<{ pcm: ArrayBuffer; rms: number }>) => {
        if (socket.readyState === WebSocket.OPEN && statusRef.current === "listening") {
          socket.send(event.data.pcm);
        }
        const level = Math.min(1, event.data.rms * 6);
        setLevels((previous) => [...previous.slice(1), level]);
      };
      if (context.state === "suspended") await context.resume();
    },
    [],
  );

  const start = useCallback(async () => {
    if (statusRef.current !== "idle") return;
    setError(null);
    setInterim("");
    updateStatus("connecting");

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
    } catch (caught) {
      const name = caught instanceof DOMException ? caught.name : "";
      if (name === "NotFoundError" || name === "OverconstrainedError") {
        fail("no_mic", "No microphone was found. Plug one in, or switch to Text.");
      } else {
        fail("mic_blocked", "Microphone access is blocked. Allow it in your browser’s site settings, or switch to Text.");
      }
      return;
    }
    streamRef.current = stream;

    const socket = new WebSocket(`${WS_URL}/interviews/${interviewId}/voice`);
    socket.binaryType = "arraybuffer";
    socketRef.current = socket;

    socket.onopen = () => socket.send(JSON.stringify({ token: getToken() }));

    socket.onmessage = (message) => {
      if (typeof message.data !== "string") return;
      let event: ServerEvent;
      try {
        event = JSON.parse(message.data) as ServerEvent;
      } catch {
        return;
      }
      switch (event.type) {
        case "ready":
          updateStatus("listening");
          startAudio(socket, stream).catch(() =>
            fail("voice_failed", "Couldn’t start recording in this browser. Try Chrome or Edge, or switch to Text."),
          );
          break;
        case "transcript":
          if (event.is_final) {
            setTranscript((current) => joinTranscript(current, event.text ?? ""));
            setInterim("");
          } else {
            setInterim(event.text ?? "");
          }
          break;
        case "closed":
          teardown();
          break;
        case "error":
          fail(
            event.code === "voice_unavailable" ? "voice_unavailable" : "voice_failed",
            event.message ?? "The voice connection dropped. Try again or switch to Text.",
          );
          break;
      }
    };

    socket.onclose = (closeEvent) => {
      if (socketRef.current !== socket) return; // already torn down on purpose
      if (closeEvent.code === 4401) {
        fail("session_expired", "Your session expired. Log in again to keep recording.");
      } else if (statusRef.current === "finishing") {
        teardown();
      } else {
        fail("voice_failed", "The voice connection dropped. Try again or switch to Text.");
      }
    };
  }, [fail, interviewId, setInterim, startAudio, teardown, updateStatus]);

  const stop = useCallback(() => {
    if (statusRef.current === "connecting") {
      teardown();
      return;
    }
    if (statusRef.current !== "listening") return;
    updateStatus("finishing");
    stopAudio();
    const socket = socketRef.current;
    if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: "stop" }));
    // Fold any interim words in if Deepgram never finalizes them.
    finishTimerRef.current = window.setTimeout(() => {
      const pending = interimRef.current;
      if (pending) setTranscript((current) => joinTranscript(current, pending));
      teardown();
    }, FINISH_TIMEOUT_MS);
  }, [stopAudio, teardown, updateStatus]);

  const reset = useCallback(() => {
    teardown();
    setTranscript("");
    setError(null);
  }, [teardown]);

  useEffect(() => teardown, [teardown]);

  return { status, transcript, setTranscript, interim, levels, error, start, stop, reset };
}
