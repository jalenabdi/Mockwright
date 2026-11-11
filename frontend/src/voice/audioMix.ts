/**
 * One shared Web Audio graph for the interview, so the interviewer's voice can
 * be heard *and* recorded into the candidate's video.
 *
 *   interviewer <audio> ──▶ bus ──▶ speakers
 *                            └────▶ each recording's mix ◀── candidate's mic
 *
 * Browsers only let an AudioContext run after the user has interacted with the
 * page, so everything here degrades: if the context can't run, the voice plays
 * straight from its <audio> element and videos record the mic alone.
 */

interface Mixer {
  context: AudioContext;
  bus: GainNode;
}

let mixer: Mixer | null | undefined;

function getMixer(): Mixer | null {
  if (mixer !== undefined) return mixer;
  try {
    const context = new AudioContext();
    const bus = context.createGain();
    bus.connect(context.destination);
    mixer = { context, bus };
  } catch {
    mixer = null; // no Web Audio support
  }
  return mixer;
}

/**
 * Try to get the audio graph running. Resolves to true if the interviewer's
 * voice can be recorded, false if it can only be played the plain way.
 */
export async function wakeAudio(timeoutMs = 500): Promise<boolean> {
  const current = getMixer();
  if (!current) return false;
  if (current.context.state === "running") return true;
  try {
    await Promise.race([current.context.resume(), new Promise((resolve) => setTimeout(resolve, timeoutMs))]);
  } catch {
    // Not allowed yet (no user interaction).
  }
  return isRunning(); // re-read: resume() changes the state
}

function isRunning(): boolean {
  return getMixer()?.context.state === "running";
}

const routed = new WeakSet<HTMLMediaElement>();

/** Send an <audio> element through the bus. Only call once the graph is running. */
export function routeThroughMixer(element: HTMLMediaElement): boolean {
  const current = getMixer();
  if (!current || !isRunning()) return false;
  if (!routed.has(element)) {
    current.context.createMediaElementSource(element).connect(current.bus);
    routed.add(element);
  }
  return true;
}

/**
 * The stream to record: the camera's video, plus one audio track that mixes the
 * candidate's mic with the interviewer's voice. Falls back to the camera stream
 * as-is when the graph isn't running. Call `release` when the recording ends.
 */
export function recordingStream(camera: MediaStream): { stream: MediaStream; release: () => void } {
  const current = getMixer();
  if (!current || !isRunning()) return { stream: camera, release: () => undefined };

  const { context, bus } = current;
  const mix = context.createMediaStreamDestination();
  const mics = camera.getAudioTracks();
  const mic = mics.length ? context.createMediaStreamSource(new MediaStream(mics)) : null;
  mic?.connect(mix);
  bus.connect(mix);
  return {
    stream: new MediaStream([...camera.getVideoTracks(), ...mix.stream.getAudioTracks()]),
    release: () => {
      mic?.disconnect();
      try {
        bus.disconnect(mix);
      } catch {
        // Already disconnected.
      }
    },
  };
}
