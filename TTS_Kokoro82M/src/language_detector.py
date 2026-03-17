from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Optional

from langdetect import DetectorFactory, LangDetectException, detect


DetectorFactory.seed = 0  # make detection deterministic


@dataclass
class LanguageDetector:
    voices_file: str

    def __post_init__(self) -> None:
        self._voices_by_language: Dict[str, List[str]] = {}
        self._languages: List[str] = []
        self._langdetect_map: Dict[str, str] = {}
        self._load_voices()

    def _load_voices(self) -> None:
        """Load languages and voices from VOICES.md file in a single pass."""
        file_path = self._resolve_file_path()
        if not file_path:
            print(f"Error: Could not find VOICES.md file. Searched in:")
            print(f"  - Current directory: {os.getcwd()}")
            print(f"  - Module directory: {os.path.dirname(os.path.abspath(__file__))}")
            return

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                current_language: Optional[str] = None
                for raw_line in file:
                    line = raw_line.strip()
                    if not line:
                        continue

                    # Extract language from header
                    if line.startswith("### "):
                        current_language = line[4:].strip()
                        if current_language:
                            self._voices_by_language[current_language] = []
                            if current_language not in self._languages:
                                self._languages.append(current_language)
                        continue

                    # Extract voice names from table rows
                    if current_language and line.startswith("|") and not line.startswith("| ----") and not line.startswith("| Name"):
                        parts = [p.strip() for p in line.strip("|").split("|")]
                        if parts:
                            voice_name = parts[0].replace("**", "").replace("`", "").strip()
                            if voice_name and voice_name.lower() != "name":
                                self._voices_by_language[current_language].append(voice_name)

            # Build langdetect mapping dynamically based on loaded languages
            self._build_langdetect_map()
            
            if not self._languages:
                print(f"Warning: No languages loaded from {file_path}. File may be empty or incorrectly formatted.")

        except (FileNotFoundError, OSError) as e:
            print(f"Error loading voices file: {e}")
            print(f"Attempted path: {file_path}")

    def _resolve_file_path(self) -> Optional[str]:
        """Resolve the file path, trying multiple locations including module directory."""
        if os.path.isabs(self.voices_file):
            return self.voices_file if os.path.exists(self.voices_file) else None

        # Get the directory where this Python file is located
        module_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Try current working directory
        if os.path.exists(self.voices_file):
            return os.path.abspath(self.voices_file)

        # Try in the same directory as this module (src/)
        module_file_path = os.path.join(module_dir, self.voices_file)
        if os.path.exists(module_file_path):
            return module_file_path

        # Try parent directory
        parent_path = os.path.join("..", self.voices_file)
        if os.path.exists(parent_path):
            return os.path.abspath(parent_path)

        # Try src directory from current directory
        src_path = os.path.join("src", self.voices_file)
        if os.path.exists(src_path):
            return os.path.abspath(src_path)

        return None

    def _build_langdetect_map(self) -> None:
        """Build mapping from langdetect codes to language names."""
        # Map langdetect codes to language names found in VOICES.md
        code_to_language = {
            "en-us": "American English",
            "en-gb": "British English",
            "ja": "Japanese",
            "zh": "Mandarin Chinese",
            "es": "Spanish",
            "fr": "French",
            "hi": "Hindi",
            "it": "Italian",
            "pt-br": "Brazilian Portuguese",
        }

        # Only include mappings for languages that exist in the loaded file
        self._langdetect_map = {
            code: lang for code, lang in code_to_language.items()
            if lang in self._languages
        }

    @property
    def languages(self) -> List[str]:
        """Return list of available languages."""
        return self._languages.copy()

    def get_voices(self, language: str) -> List[str]:
        """Get voices for a specific language."""
        return self._voices_by_language.get(language, []).copy()

    def detect_language(self, text: str) -> Optional[str]:
        """Detect language from text and return language name."""
        clean = (text or "").strip()
        if not clean:
            return None

        try:
            code = detect(clean)
        except LangDetectException:
            return None

        normalized = code.lower()
        primary = normalized.split("-")[0]

        if primary == "en":
            primary = "en-us"
        elif primary == "pt":
            primary = "pt-br"

        # Try full code first, then primary code
        return self._langdetect_map.get(primary)
        # return self._langdetect_map.get(normalized) or self._langdetect_map.get(primary)
        # return primary


