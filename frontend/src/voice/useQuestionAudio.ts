import { useCallback, useEffect, useRef, useState } from "react";

import { api, ApiError } from "../lib/api";

/**
 * Reads interview questions aloud with the backend's Deepgram voice.
 * Falls back to the browser's built-in speech if the server has no Deepgram key.
 *
 * `play` resolves once reading is over: finished, stopped, replaced by another
 * play, or impossible (autoplay blocked, no speech support). It never rejects.
 */
export function useQuestionAudio(interviewId: number) {
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const cacheRef = useRef(new Map<number, string>());
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

  const play = useCallback(
    async (questionId: number, text: string): Promise<void> => {
      stop();
      const request = requestRef.current;
      if (!serverVoiceRef.current) return speakInBrowser(text);

      let url = cacheRef.current.get(questionId);
      if (!url) {
        setLoading(true);
        try {
          url = URL.createObjectURL(await api.questionSpeech(interviewId, questionId));
          cacheRef.current.set(questionId, url);
        } catch (caught) {
          if (request !== requestRef.current) return;
          setLoading(false);
          if (caught instanceof ApiError && caught.status === 503) serverVoiceRef.current = false;
          return speakInBrowser(text);
        }
      }
      if (request !== requestRef.current) return;
      setLoading(false);

      const audio = audioRef.current ?? new Audio();
      audioRef.current = audio;
      audio.src = url;
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
    [finish, interviewId, speakInBrowser, stop],
  );

  useEffect(() => {
    const cache = cacheRef.current;
    return () => {
      audioRef.current?.pause();
      if ("speechSynthesis" in window) window.speechSynthesis.cancel();
      finishRef.current?.();
      cache.forEach((url) => URL.revokeObjectURL(url));
      cache.clear();
    };
  }, []);

  return { play, stop, playing, loading };
}
