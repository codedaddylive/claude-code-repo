"""
whisper.py — Groq and OpenAI Whisper API clients using only Python stdlib.

No requests, httpx, or any third-party HTTP library.
"""

import json
import os
import uuid
import urllib.request
import urllib.error


GROQ_ENDPOINT = "https://api.groq.com/openai/v1/audio/transcriptions"
OPENAI_ENDPOINT = "https://api.openai.com/v1/audio/transcriptions"


def _build_multipart(fields, files):
    """
    Build a multipart/form-data body using only stdlib.

    Parameters:
        fields (dict): str → str form fields.
        files (dict): field_name → (filename, content_bytes, content_type).

    Returns:
        (boundary: str, body: bytes)
    """
    boundary = uuid.uuid4().hex
    parts = []

    for name, value in fields.items():
        parts.append(
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="{name}"\r\n'
            f'\r\n'
            f'{value}\r\n'
        )

    for name, (filename, data, content_type) in files.items():
        header = (
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
            f'Content-Type: {content_type}\r\n'
            f'\r\n'
        )
        parts.append(header.encode() + data + b'\r\n')

    closing = f'--{boundary}--\r\n'

    body = b''
    for part in parts:
        if isinstance(part, str):
            body += part.encode()
        else:
            body += part
    body += closing.encode()

    return boundary, body


def _post_audio(endpoint, api_key, audio_path, model, extra_fields=None):
    """
    POST an audio file to a Whisper-compatible endpoint.

    Returns the parsed JSON response dict.
    """
    with open(audio_path, "rb") as f:
        audio_data = f.read()

    filename = os.path.basename(audio_path)
    fields = {"model": model, "response_format": "verbose_json"}
    if extra_fields:
        fields.update(extra_fields)

    boundary, body = _build_multipart(
        fields=fields,
        files={"file": (filename, audio_data, "audio/wav")},
    )

    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        raise RuntimeError(
            f"Whisper API error {e.code} from {endpoint}:\n{body_text}"
        )


def _segments_to_entries(segments):
    """Convert Whisper verbose_json segments to [{start, text}] dicts."""
    entries = []
    for seg in segments or []:
        start_s = int(seg.get("start", 0))
        m = start_s // 60
        s = start_s % 60
        entries.append({
            "start": f"{m:02d}:{s:02d}",
            "text": seg.get("text", "").strip(),
        })
    return entries


def transcribe_groq(audio_path, api_key):
    """
    Transcribe audio using Groq whisper-large-v3.

    Returns list of {start: "MM:SS", text: str}.
    """
    data = _post_audio(GROQ_ENDPOINT, api_key, audio_path, "whisper-large-v3")
    return _segments_to_entries(data.get("segments", []))


def transcribe_openai(audio_path, api_key):
    """
    Transcribe audio using OpenAI whisper-1.

    Returns list of {start: "MM:SS", text: str}.
    """
    data = _post_audio(OPENAI_ENDPOINT, api_key, audio_path, "whisper-1")
    return _segments_to_entries(data.get("segments", []))


def transcribe(audio_path, backend=None):
    """
    Transcribe audio, selecting backend automatically or by name.

    Parameters:
        audio_path (str): Path to mono 16kHz WAV file.
        backend (str|None): "groq", "openai", or None (auto).

    Returns:
        list of {start: "MM:SS", text: str}.

    Raises:
        RuntimeError: If no API key is available for the chosen backend.
    """
    groq_key = os.environ.get("GROQ_API_KEY", "")
    openai_key = os.environ.get("OPENAI_API_KEY", "")

    if backend == "groq":
        if not groq_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Set it in ~/.config/watch/.env"
            )
        return transcribe_groq(audio_path, groq_key)

    if backend == "openai":
        if not openai_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Set it in ~/.config/watch/.env"
            )
        return transcribe_openai(audio_path, openai_key)

    # Auto-select
    if groq_key:
        return transcribe_groq(audio_path, groq_key)
    if openai_key:
        return transcribe_openai(audio_path, openai_key)

    raise RuntimeError(
        "No Whisper API key found. Set GROQ_API_KEY or OPENAI_API_KEY in "
        "~/.config/watch/.env, or use --no-whisper to skip transcription."
    )
