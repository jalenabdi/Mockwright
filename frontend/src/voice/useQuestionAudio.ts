import { useCallback, useEffect, useRef, useState } from "react";

import { api, ApiError } from "../lib/api";
import { routeThroughMixer } from "./audioMix";

/** Something the interviewer says: a question, or a follow-up on it. */
export interface SpokenLine {
  questionId: number;
  followUpId?: number;
  text: string;
}

const MP3 = "audio/mpeg";

function canStream(): boolean {
  return typeof MediaSource !== "undefined" && MediaSource.isTypeSupported(MP3);
}

/**
 * Feeds a streamed MP3 response into a MediaSource, so playback starts with the
 * first chunk instead of after the whole file. Resolves to the complete file
 * (for replays) once the stream ends.
 */
async function streamInto(source: MediaSource, body: ReadableStream<Uint8Array>, isCurrent: () => boolean): Promise<Blob> {
  if (source.readyState !== "open") {
    await new Promise((resolve) => source.addEventListener("sourceopen", resolve, { once: true }));
  }
  const buffer = source.addSourceBuffer(MP3);
  const parts: Uint8Array[] = [];
  const reader = body.getReader();
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      if (!isCurrent()) {
        await reader.cancel(); // stopped or replaced: stop downloading too
        break;
      }
      parts.push(value);
      buffer.appendBuffer(value as Uint8Array<ArrayBuffer>);
      await new Promise((resolve) => buffer.addEventListener("updateend", resolve, { once: true }));
    }
  } finally {
    reader.releaseLock();
  }
  if (source.readyState === "open") source.endOfStream();
  if (!isCurrent()) throw new Error("Stopped before the line finished downloading.");
  return new Blob(parts as BlobPart[], { type: MP3 });
}

/**
 * Reads the interviewer's lines aloud with the backend's Deepgram voice,
 * streaming each one so it starts speaking almost immediately. Falls back to
 * the browser's built-in speech if the server has no Deepgram key.
 *
 * `play` resolves once reading is over: finished, stopped, replaced by another
 * play, or impossible (autoplay blocked, no speech support). It never rejects.
 */
export function useQuestionAudio(interviewId: number) {
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null); // the element playing now
  const routedRef = useRef<HTMLAudioElement | null>(null); // plays through the mixer, so videos record it
  const plainRef = useRef<HTMLAudioElement | null>(null); // fallback while the mixer can't run
  const cacheRef = useRef(new Map<string, string>());
  const streamUrlRef = useRef<string | null>(null);
  const serverVoiceRef = useRef(true);
  const requestRef = useRef(0);
  const finishRef = useRef<(() => void) | null>(null);

  // Settle the promise of whatever is currently playing.
  const finish = useCallback(() => {
    const done = finishRef.current;
    finishRef.current = null;
    setPlaying(false);
    done?.();
  }, []);

  const releaseStreamUrl = useCallback(() => {
    if (streamUrlRef.current) URL.revokeObjectURL(streamUrlRef.current);
    streamUrlRef.current = null;
  }, []);

  const stop = useCallback(() => {
    requestRef.current += 1;
    audioRef.current?.pause();
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    setLoading(false);
    finish();
  }, [finish]);

  const speakInBrowser = useCallback(
    (text: string) =>
      new Promise<void>((resolve) => {
        if (!("speechSynthesis" in window)) {
          resolve();
          return;
        }
        finishRef.current = resolve;
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.onend = finish;
        utterance.onerror = finish;
        setPlaying(true);
        window.speechSynthesis.speak(utterance);
      }),
    [finish],
  );

  /** Play `src`, through the mixer when it's running; resolves when it ends or stops. */
  const playSource = useCallback(
    (src: string) => {
      const routed = routedRef.current ?? new Audio();
      let audio: HTMLAudioElement;
      if (routeThroughMixer(routed)) {
        routedRef.current = routed;
        audio = routed;
      } else {
        plainRef.current ??= new Audio();
        audio = plainRef.current;
      }
      audioRef.current = audio; // play() already stopped whatever was playing before
      audio.src = src;
      return new Promise<void>((resolve) => {
        finishRef.current = resolve;
        audio.onended = finish;
        audio.onpause = finish;
        audio.onerror = finish;
        setPlaying(true);
        // Autoplay can be blocked until the user interacts with the page.
        audio.play().catch(finish);
      });
    },
    [finish],
  );

  const play = useCallback(
    async (line: SpokenLine): Promise<void> => {
      stop();
      const request = requestRef.current;
      const isCurrent = () => request === requestRef.current;
      if (!serverVoiceRef.current) return speakInBrowser(line.text);

      const key = line.followUpId ? `f${line.followUpId}` : `q${line.questionId}`;
      const cached = cacheRef.current.get(key);
      if (cached) return playSource(cached);

      setLoading(true);
      let response: Response;
      try {
        response = await api.speech(interviewId, line);
      } catch (caught) {
        if (!isCurrent()) return;
        setLoading(false);
        if (caught instanceof ApiError && caught.status === 503) serverVoiceRef.current = false;
        return speakInBrowser(line.text);
      }
      if (!isCurrent()) return;
      setLoading(false);

      const remember = (file: Blob) => {
        if (file.size > 0) cacheRef.current.set(key, URL.createObjectURL(file));
      };

      if (canStream() && response.body) {
        const source = new MediaSource();
        releaseStreamUrl();
        streamUrlRef.current = URL.createObjectURL(source);
        const playback = playSource(streamUrlRef.current);
        streamInto(source, response.body, isCurrent).then(remember, () => undefined);
        return playback;
      }

      try {
        const file = await response.blob();
        if (!isCurrent()) return;
        remember(file);
        const url = cacheRef.current.get(key);
        if (url) return playSource(url);
      } catch {
        // Fall through to the browser's voice.
      }
      if (isCurrent()) return speakInBrowser(line.text);
    },
    [interviewId, playSource, releaseStreamUrl, speakInBrowser, stop],
  );

  useEffect(() => {
    const cache = cacheRef.current;
    return () => {
      audioRef.current?.pause();
      if ("speechSynthesis" in window) window.speechSynthesis.cancel();
      finishRef.current?.();
      cache.forEach((url) => URL.revokeObjectURL(url));
      cache.clear();
      releaseStreamUrl();
    };
  }, [releaseStreamUrl]);

  return { play, stop, playing, loading };
}
