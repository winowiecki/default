"""Local transcript de-identification for qualitative research.

Originals never leave this machine. The only network traffic this package
ever produces is to a local Ollama server (localhost), and the LLM is used
strictly as a *detector* — it never generates or rewrites transcript text.
"""

__version__ = "0.1.0"
