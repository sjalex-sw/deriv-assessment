from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

from jsonschema import validate as jsonschema_validate
from jsonschema import ValidationError

from llm.openai_client import OpenAILLMClient


@dataclass
class PromptContract:
    stage: str
    system_prompt: str
    user_prompt: str
    schema: Dict[str, Any]
    output_path: str
    user_id: Optional[str] = None
    input_files: Optional[List[str]] = None
    temperature: float = 0.2


class ContractRunner:
    """
    Executes LLM calls under strict schema + logging + validation rules.
    """

    def __init__(self, client: OpenAILLMClient):
        self.client = client

    def run(self, contract: PromptContract) -> dict:
        messages = [
            {"role": "system", "content": contract.system_prompt},
            {"role": "user", "content": contract.user_prompt}
        ]

        raw_output = self.client.call(
            stage=contract.stage,
            messages=messages,
            user_id=contract.user_id,
            input_files=contract.input_files,
            output_file=contract.output_path,
            temperature=contract.temperature
        )

        if not raw_output or raw_output.strip() == "":
            raise ValueError(
                f"[{contract.stage}] Empty LLM response. No data returned."
            )

        # ----------------------------
        # STEP 1: JSON parsing
        # ----------------------------

        import re


        def safe_json_parse(text: str):
            if not text:
                raise ValueError("Empty LLM output")

            text = text.strip()

            # remove markdown fences
            text = re.sub(r"^```json|^```|```$", "", text).strip()

            # try direct parse
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

            # fallback: extract first JSON array/object
            match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
            if match:
                return json.loads(match.group(1))

            raise ValueError(f"Could not parse JSON. Raw output:\n{text}")


        def extract_array_output(parsed):
            if isinstance(parsed, list):
                return parsed

            if isinstance(parsed, dict):
                # common wrappers
                for key in ["criteria", "interventions", "results", "data"]:
                    if key in parsed and isinstance(parsed[key], list):
                        return parsed[key]

            raise ValueError("Output is not a valid array format")


        try:
            raw_output = raw_output.strip()
            if raw_output.startswith("```"):
                raw_output = raw_output.strip("`")
                raw_output = raw_output.replace("json", "", 1).strip()
            parsed = extract_array_output(safe_json_parse(raw_output))
        except Exception as e:
            raise ValueError(f"[{contract.stage}] Invalid JSON output: {e}")


        def normalize_confidence(parsed: dict):
            c = parsed.get("confidence")

            if isinstance(c, (int, float)):
                if c < 0.4:
                    parsed["confidence"] = "low"
                elif c < 0.7:
                    parsed["confidence"] = "medium"
                else:
                    parsed["confidence"] = "high"

            return parsed

        parsed = normalize_confidence(parsed)

        # ----------------------------
        # STEP 2: JSONSchema validation (HARD GATE)
        # ----------------------------
        try:
            jsonschema_validate(instance=parsed, schema=contract.schema)
        except ValidationError as e:
            raise ValueError(
                f"[{contract.stage}] Schema validation failed: {e.message}"
            )

        return parsed