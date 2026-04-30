import os
import json
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

from openai import OpenAI


class OpenAILLMClient:
    """
    Thin wrapper around OpenAI API with mandatory structured logging.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4.1-mini",
        log_path: str = "llm_calls.jsonl",
    ):
        # 🔴 THIS IS THE FIX
        load_dotenv()

        key = api_key or os.getenv("OPENAI_API_KEY")

        if not key:
            raise ValueError(
                "OPENAI_API_KEY not found. "
                "Make sure .env exists and load_dotenv() is called."
            )

        self.client = OpenAI(api_key=key)
        self.model = model
        self.log_path = log_path

        # ensure log file exists
        os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
        if not os.path.exists(log_path):
            open(log_path, "w").close()

    # -------------------------
    # Core public method
    # -------------------------
    def call(
        self,
        *,
        stage: str,
        messages: List[Dict[str, str]],
        user_id: Optional[str] = None,
        input_files: Optional[List[str]] = None,
        output_file: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        """
        Executes LLM call + logs everything required.
        Returns raw model output (string).
        """

        timestamp = datetime.now(timezone.utc).isoformat()

        # 1. Build prompt hash (deterministic fingerprint)
        prompt_hash = self._hash_messages(messages)

        # 2. Call OpenAI
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"}  # or json_schema if available
        )

        output_text = response.choices[0].message.content

        if output_text is None or output_text.strip() == "":
            raise ValueError(
                f"Empty LLM response. Full response: {response}"
            )

        # 3. Write output file if provided
        if output_file:
            self._write_file(output_file, output_text)

        # 4. Log call
        self._log_call(
            {
                "stage": stage,
                "user_id": user_id,
                "timestamp": timestamp,
                "provider": "openai",
                "model": self.model,
                "prompt_hash": prompt_hash,
                "input_artifacts": input_files or [],
                "output_artifact": output_file,
            }
        )

        return output_text

    # -------------------------
    # Logging
    # -------------------------
    def _log_call(self, record: Dict[str, Any]) -> None:
        """
        Append-only JSONL logging.
        """
        with open(self.log_path, "a") as f:
            f.write(json.dumps(record) + "\n")

    # -------------------------
    # Prompt hashing
    # -------------------------
    def _hash_messages(self, messages: List[Dict[str, str]]) -> str:
        """
        Stable hash of prompt content for reproducibility tracking.
        """
        normalized = json.dumps(messages, sort_keys=True)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    # -------------------------
    # File helper
    # -------------------------
    def _write_file(self, path: str, content: str) -> None:
        dir_path = os.path.dirname(path)
        if dir_path:  # only create folder if it exists
            os.makedirs(dir_path, exist_ok=True)
        with open(path, "w") as f:
            f.write(content)