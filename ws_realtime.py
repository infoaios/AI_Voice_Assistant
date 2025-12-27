"""
ws_realtime.py

Interactive real-time client: record from microphone, send to WebSocket server
as base64 WAV for `whisper` STT, forward transcription to `llama`, then to `xtts`,
and play the returned audio. Designed for Windows.

Dependencies:
  pip install sounddevice soundfile numpy websockets

Usage:
  python d:\flow\ws_realtime.py

Press Enter to record a short clip (default 3s). Type a number to record that many
seconds. Type `exit` to quit.
"""

import io
import sys
import base64
import json
from pathlib import Path

URI = "ws://5.101.168.158:8765?token=7c91e4f2b5a6c8d19e0f3a4b2c1d5e6f8a9b0c2d3e4f5a6b7c8d9e0f1a2b3c4d"

try:
    import sounddevice as sd
    import soundfile as sf
    import numpy as np
    import websockets
except Exception as e:
    print("Missing dependencies or import error:", e)
    print("Install with: pip install sounddevice soundfile numpy websockets")
    sys.exit(1)

import asyncio
import time

SAMPLE_RATE = 16000
CHANNELS = 1


def record_seconds(seconds: float):
    data = sd.rec(int(seconds * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=CHANNELS, dtype='int16')
    sd.wait()
    return data.squeeze()


def wav_bytes_from_numpy(np_arr: np.ndarray):
    buf = io.BytesIO()
    # soundfile expects float32 or int16; our array is int16 already
    sf.write(buf, np_arr, SAMPLE_RATE, format='WAV', subtype='PCM_16')
    return buf.getvalue()


async def send_and_receive(b64_audio: str):
    async with websockets.connect(URI, ping_interval=20) as ws:
        timings = {}

        # STT (whisper)
        t0 = time.time()
        await ws.send(json.dumps({"model_id": "whisper", "prompt": b64_audio, "prompt_id": 1}))
        t_after_whisper_send = time.time()
        stt_raw = await ws.recv()
        t_whisper_recv = time.time()
        try:
            stt = json.loads(stt_raw)
        except Exception:
            stt = {}
        text = stt.get('text') if isinstance(stt, dict) else None
        timings['whisper_ms'] = (t_whisper_recv - t_after_whisper_send) * 1000.0

        # LLM (llama)
        await ws.send(json.dumps({"model_id": "llama", "prompt": text, "prompt_id": 2}))
        t_after_llama_send = time.time()
        llm_raw = await ws.recv()
        t_llama_recv = time.time()
        try:
            llm = json.loads(llm_raw)
        except Exception:
            llm = {}
        reply = llm.get('text') if isinstance(llm, dict) else None
        timings['llama_ms'] = (t_llama_recv - t_after_llama_send) * 1000.0

        # TTS (xtts)
        await ws.send(json.dumps({"model_id": "xtts", "prompt": reply, "prompt_id": 3}))
        t_after_xtts_send = time.time()
        tts_raw = await ws.recv()
        t_xtts_recv = time.time()
        try:
            tts = json.loads(tts_raw)
        except Exception:
            tts = {}
        audio_b64 = tts.get('audio_b64') if isinstance(tts, dict) else None
        timings['xtts_ms'] = (t_xtts_recv - t_after_xtts_send) * 1000.0

        timings['total_generation_ms'] = (t_xtts_recv - t0) * 1000.0

        return {"audio_b64": audio_b64, "timings": timings, "stt": stt, "llm": llm, "tts": tts}


def play_wav_bytes(wav_bytes: bytes):
    # write to a temporary file and use winsound on Windows for playback
    try:
        import tempfile
        import winsound
        t = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        t.write(wav_bytes)
        t.flush()
        t.close()
        winsound.PlaySound(t.name, winsound.SND_FILENAME)
    except Exception:
        # fallback: try sounddevice playback
        try:
            data, sr = sf.read(io.BytesIO(wav_bytes), dtype='float32')
            sd.play(data, sr)
            sd.wait()
        except Exception as e:
            print('Could not play audio:', e)


def interactive():
    print('Interactive real-time client. Press Enter to record (default 3s). Type seconds or "exit".')
    while True:
        s = input('Record seconds> ').strip()
        if not s:
            secs = 3.0
        elif s.lower() in ('exit', 'quit'):
            break
        else:
            try:
                secs = float(s)
            except ValueError:
                print('Invalid number; try again.')
                continue

        try:
            arr = record_seconds(secs)
            wavb = wav_bytes_from_numpy(arr)
            b64 = base64.b64encode(wavb).decode('ascii')
            result = asyncio.run(send_and_receive(b64))
            timings = (result or {}).get('timings', {})
            # Print only the per-stage round-trip timings (ms)
            print(', '.join(f"{k}={v:.1f}" for k,v in timings.items()))
            # still play audio if present
            audio_b64 = (result or {}).get('audio_b64')
            if audio_b64:
                audio_bytes = base64.b64decode(audio_b64)
                play_wav_bytes(audio_bytes)
        except KeyboardInterrupt:
            print('Interrupted.')
            break
        except Exception as e:
            print('Error:', e)


if __name__ == '__main__':
    interactive()
