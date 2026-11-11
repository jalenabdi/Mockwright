import { useCallback, useEffect, useRef, useState } from "react";

import { api, ApiError } from "../lib/api";

/**
 * Reads interview questions aloud with the backend's Deepgram voice.
 * Falls back to the browser's built-in speech if the server has no Deepgram key.
 */
export function useQuestionAudio(interviewId: number) {
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const cacheRef = useRef(new Map<number, string>());
  const serverVoiceRef = useRef(true);
  const requestRef = useRef(0);

  const stop = useCallback(() => {
    requestRef.current += 1;
    audioRef.current?.pause();
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    setPlaying(false);
    setLoading(false);
  }, []);

  const speakInBrowser = useCallback((text: string) => {
    if (!("speechSynthesis" in window)) return;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1;
    utterance.onend = () => setPlaying(false);
    utterance.onerror = () => setPlaying(false);
    setPlaying(true);
    window.speechSynthesis.speak(utterance);
  }, []);

  const play = useCallback(
    async (questionId: number, text: string) => {
      stop();
      const request = requestRef.current;
      if (!serverVoiceRef.current) {
        speakInBrowser(text);
        return;
      }
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
          speakInBrowser(text);
          return;
        }
      }
      if (request !== requestRef.current) return;
      setLoading(false);
      const audio = audioRef.current ?? new Audio();
      audioRef.current = audio;
      audio.src = url;
      audio.onended = () => setPlaying(false);
      audio.onpause = () => setPlaying(false);
      try {
        setPlaying(true);
        await audio.play();
      } catch {
        // Autoplay blocked until the user interacts: they can press "Hear Question Again".
        setPlaying(false);
      }
    },
    [interviewId, speakInBrowser, stop],
  );

  useEffect(() => {
    const cache = cacheRef.current;
    return () => {
      audioRef.current?.pause();
      if ("speechSynthesis" in window) window.speechSynthesis.cancel();
      cache.forEach((url) => URL.revokeObjectURL(url));
      cache.clear();
    };
  }, []);

  return { play, stop, playing, loading };
}
