import base64
import json
from typing import Generator

import requests

from config import settings


class LMStudioService:

    def __init__(self):

        self.base_url = (
            settings.LM_STUDIO_BASE_URL
            .rstrip("/")
        )

        self.text_model = (
            settings.LM_STUDIO_MODEL
        )

        self.vision_model = (
            settings.LM_STUDIO_VISION_MODEL
        )

    # ==================================================
    # TEXT GENERATION
    # ==================================================

    def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None
    ) -> str:

        payload = {
            "model": self.text_model,
            "input": prompt,
            "stream": False,
        }

        if system_prompt:
            payload["system_prompt"] = (
                system_prompt
            )

        response = requests.post(
            f"{self.base_url}/api/v1/chat",
            json=payload,
            timeout=180,
        )

        if not response.ok:
            raise RuntimeError(
                "LM Studio text request failed:\n"
                f"Status: {response.status_code}\n"
                f"Body: {response.text}"
            )

        return self._extract_native_message(
            response.json()
        )

    # ==================================================
    # TEXT STREAMING
    # ==================================================

    def stream_text(
        self,
        prompt: str,
        system_prompt: str | None = None
    ) -> Generator[str, None, None]:

        payload = {
            "model": self.text_model,
            "input": prompt,
            "stream": True,
        }

        if system_prompt:
            payload["system_prompt"] = (
                system_prompt
            )

        response = requests.post(
            f"{self.base_url}/api/v1/chat",
            json=payload,
            stream=True,
            timeout=180,
        )

        if not response.ok:
            raise RuntimeError(
                "LM Studio streaming request failed:\n"
                f"Status: {response.status_code}\n"
                f"Body: {response.text}"
            )

        try:

            for raw_line in response.iter_lines(
                decode_unicode=True
            ):

                if not raw_line:
                    continue

                line = raw_line.strip()

                if not line.startswith(
                    "data:"
                ):
                    continue

                data_text = (
                    line[5:].strip()
                )

                if not data_text:
                    continue

                try:

                    data = json.loads(
                        data_text
                    )

                except json.JSONDecodeError:
                    continue

                event_type = data.get(
                    "type",
                    ""
                )

                # ------------------------------------------
                # Incremental token
                # ------------------------------------------

                if event_type == (
                    "message.delta"
                ):

                    content = data.get(
                        "content",
                        ""
                    )

                    if content:
                        yield content

                # ------------------------------------------
                # Error
                # ------------------------------------------

                elif event_type == "error":

                    raise RuntimeError(
                        data.get(
                            "message",
                            "LM Studio streaming error."
                        )
                    )

                # ------------------------------------------
                # Completed
                # ------------------------------------------

                elif event_type == "chat.end":

                    return

        finally:

            response.close()

    # ==================================================
    # VISION / IMAGE ANALYSIS
    #
    # LM Studio OpenAI-compatible endpoint:
    # /v1/chat/completions
    # ==================================================

    def analyze_image(
        self,
        image_bytes: bytes,
        mime_type: str,
        prompt: str
    ) -> str:

        if not image_bytes:
            raise ValueError(
                "image_bytes cannot be empty."
            )

        if not mime_type:
            mime_type = "image/png"

        encoded = base64.b64encode(
            image_bytes
        ).decode("utf-8")

        image_url = (
            f"data:{mime_type};base64,"
            f"{encoded}"
        )

        payload = {
            "model": self.vision_model,

            "messages": [
                {
                    "role": "user",

                    "content": [
                        {
                            "type": "text",
                            "text": prompt,
                        },
                        {
                            "type": "image_url",

                            "image_url": {
                                "url": image_url
                            },
                        },
                    ],
                }
            ],

            "temperature": 0.0,

            "stream": False,
        }

        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            headers={
                "Content-Type":
                    "application/json"
            },
            json=payload,
            timeout=180,
        )

        if not response.ok:

            raise RuntimeError(
                "LM Studio vision request failed:\n"
                f"Status: {response.status_code}\n"
                f"Body: {response.text}"
            )

        data = response.json()

        try:

            content = (
                data["choices"][0]
                ["message"]
                ["content"]
            )

            if not isinstance(
                content,
                str
            ):

                raise TypeError(
                    "Vision response content "
                    "is not a string."
                )

            return content.strip()

        except (
            KeyError,
            IndexError,
            TypeError
        ):

            raise RuntimeError(
                "Unexpected LM Studio vision "
                f"response:\n{data}"
            )

    # ==================================================
    # OCR
    # ==================================================

    def ocr_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/png"
    ) -> str:

        prompt = """
Extract ALL readable text from this image.

This is OCR, not summarization.

Preserve:

- headings
- section numbers
- regulation numbers
- rule numbers
- paragraphs
- dates
- names
- bullet points
- tables
- numerical values
- punctuation
- original reading order

Important:

- Do not summarize.
- Do not explain.
- Do not add commentary.
- Do not invent missing text.
- If text is unclear, preserve the
  readable portion rather than guessing.
- Return only the extracted text.
""".strip()

        return self.analyze_image(
            image_bytes=image_bytes,
            mime_type=mime_type,
            prompt=prompt
        )

    # ==================================================
    # NATIVE LM STUDIO RESPONSE PARSER
    # ==================================================

    @staticmethod
    def _extract_native_message(
        data: dict
    ) -> str:

        output = data.get(
            "output",
            []
        )

        if isinstance(
            output,
            list
        ):

            for item in output:

                if (
                    item.get("type")
                    == "message"
                ):

                    content = item.get(
                        "content",
                        ""
                    )

                    if isinstance(
                        content,
                        str
                    ):

                        return content.strip()

        fallback = data.get(
            "response",
            ""
        )

        if isinstance(
            fallback,
            str
        ):

            return fallback.strip()

        return ""
