# Step 2.5 — Transcribe video / audio files

**When to read this file:** Step 2 (detect) reported one or more `video` files. If `video` count is zero, skip this file entirely.

Video and audio files cannot be read directly. Transcribe them to text first, then treat the transcripts as doc files in Step 3.

## Strategy

Read the god nodes from the detect output or analysis file. You are already a language model — write a one-sentence domain hint yourself from those labels. Then pass it to Whisper as the initial prompt. No separate API call needed.

**However**, if the corpus has *only* video files and no other docs/code, use the generic fallback prompt: `"Use proper punctuation and paragraph breaks."`

## Step 1 — Write the Whisper prompt yourself

Read the top god node labels from detect output or analysis, then compose a short domain hint sentence, for example:

- Labels: `transformer, attention, encoder, decoder` → `"Machine learning research on transformer architectures and attention mechanisms. Use proper punctuation and paragraph breaks."`
- Labels: `kubernetes, deployment, pod, helm` → `"DevOps discussion about Kubernetes deployments and Helm charts. Use proper punctuation and paragraph breaks."`

Set it as `$env:GRAPHIFY_WHISPER_PROMPT` before running the transcription command.

## Step 2 — Transcribe (PowerShell)

```powershell
@'
import json, os
from pathlib import Path
from graphify.transcribe import transcribe_all

detect = json.loads(Path('graphify-out/.graphify_detect.json').read_text(encoding="utf-8"))
video_files = detect.get('files', {}).get('video', [])
prompt = os.environ.get('GRAPHIFY_WHISPER_PROMPT', 'Use proper punctuation and paragraph breaks.')

transcript_paths = transcribe_all(video_files, initial_prompt=prompt)
print(json.dumps(transcript_paths, ensure_ascii=False))
'@ | Out-File -FilePath .graphify_step_transcribe.py -Encoding utf8
& (Get-Content graphify-out\.graphify_python) .graphify_step_transcribe.py | Out-File -FilePath graphify-out\.graphify_transcripts.json -Encoding utf8
Remove-Item -ErrorAction SilentlyContinue .graphify_step_transcribe.py
```

## After transcription

- Read the transcript paths from `graphify-out\.graphify_transcripts.json`
- Add them to the docs list before dispatching semantic subagents in Step 3B
- Print how many transcripts were created: `Transcribed N video file(s) -> treating as docs`
- If transcription fails for a file, print a warning and continue with the rest

## Whisper model selection

Default is `base`. If the user passed `--whisper-model <name>`, set `$env:GRAPHIFY_WHISPER_MODEL = "<name>"` before running the command above.

Then return to SKILL.md Step 3.
