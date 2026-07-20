
## Squad Collaboration

This project uses squad for multi-agent collaboration. Run `squad help` for all commands and usage guide.

## Calling Gemini directly from code

For a synchronous path (as opposed to the async git bus in `COORDINATION.md`), use
`gemini_interaction.py`:

```bash
pip install google-genai
export GEMINI_API_KEY=...        # or GOOGLE_API_KEY
python gemini_interaction.py "Your prompt here"
```

```python
from gemini_interaction import get_gemini_response
print(get_gemini_response("Summarize the video pipeline."))
```

Defaults to `gemini-2.5-flash` (override with `$GEMINI_MODEL` or the `model` arg).

