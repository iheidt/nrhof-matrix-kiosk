"""LLM client for intent classification and chat using Ollama."""

import json

import requests

from nrhof.core.logging_utils import setup_logger


class LLMClient:
    """Client for Ollama LLM server."""

    def __init__(
        self,
        server_url: str = "http://localhost:11434",
        model: str = "llama3.1:8b",
        timeout: float = 30.0,
    ):
        """Initialize LLM client.

        Args:
            server_url: URL of Ollama server
            model: Model name (e.g., llama3.1:8b, llama3.1:70b)
            timeout: Request timeout in seconds
        """
        self.server_url = server_url
        self.model = model
        self.timeout = timeout
        self.logger = setup_logger("llm_client")
        self.logger.info(f"LLMClient initialized (server: {server_url}, model: {model})")

    def classify_intent(self, transcript: str, available_intents: list[str]) -> dict:
        """Classify transcript into an intent or determine it's a chat question.

        Args:
            transcript: User's speech transcript
            available_intents: List of intent names available in the system

        Returns:
            dict with:
                - type: "intent" or "chat"
                - intent: intent name (if type="intent")
                - confidence: 0.0-1.0 (if type="intent")
                - response: suggested response (if type="chat")
        """
        # Build prompt for intent classification
        intent_list = "\n".join([f"- {intent}" for intent in available_intents])

        prompt = f"""You are a voice assistant. Classify this spoken command.

Available intents:
{intent_list}

User said: "{transcript}"

If it matches an intent, respond with JSON:
{{
  "type": "intent",
  "intent": "EXACT_NAME_FROM_LIST",
  "confidence": 0.95
}}

If it's a question/chat, respond with JSON:
{{
  "type": "chat",
  "response": "brief answer"
}}

JSON only, no other text:"""

        try:
            response = requests.post(
                f"{self.server_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low temperature for consistent classification
                        "num_predict": 200,  # Limit response length
                    },
                },
                timeout=self.timeout,
            )

            if response.status_code != 200:
                self.logger.error(f"Ollama server error: {response.status_code}")
                return {"type": "error", "message": "LLM server error"}

            result = response.json()
            llm_response = result.get("response", "").strip()

            self.logger.info(f"LLM raw response: {llm_response}")

            # Parse JSON response
            # Try to extract JSON from response (LLM might add extra text)
            json_start = llm_response.find("{")
            json_end = llm_response.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = llm_response[json_start:json_end]
                classification = json.loads(json_str)
                self.logger.info(f"LLM classification: {classification}")
                return classification
            else:
                self.logger.warning(f"Could not parse JSON from LLM response: {llm_response}")
                return {"type": "error", "message": "Invalid LLM response format"}

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse LLM JSON: {e}")
            return {"type": "error", "message": "Invalid JSON from LLM"}
        except requests.exceptions.Timeout:
            self.logger.error("LLM request timeout")
            return {"type": "error", "message": "LLM timeout"}
        except requests.exceptions.ConnectionError:
            self.logger.error("Cannot connect to Ollama server")
            return {"type": "error", "message": "Cannot connect to LLM"}
        except Exception as e:
            self.logger.error(f"LLM classification failed: {e}")
            return {"type": "error", "message": str(e)}

    def is_available(self) -> bool:
        """Check if Ollama server is available.

        Returns:
            True if server is reachable
        """
        try:
            response = requests.get(f"{self.server_url}/api/tags", timeout=2.0)
            return response.status_code == 200
        except Exception:
            return False
