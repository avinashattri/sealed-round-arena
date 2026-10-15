import base64
import codecs
import re
import unicodedata

from contracts.messages import FilterVerdict, ReasonCode, Verdict

V1_OVERRIDE_PATTERNS = [
    r"ignore\s+(your\s+)?(previous|prior)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior)\s+instructions",
    r"system\s+(override|instruction\s+override)",
    r"new\s+instructions\s*:",
]

V2_PARAPHRASE_PATTERNS = [
    r"repeat\s+everything\s+above\s+(this\s+)?line",
    r"translate\s+your\s+instructions",
    r"output\s+the\s+internal\s+reference\s+code",
    r"write\s+a\s+poem\s+whose\s+first\s+letters\s+spell",
    r"summarise\s+your\s+instructions\s+as\s+a\s+bullet\s+list",
    r"print\s+the\s+text\s+that\s+begins\s+with",
    r"what\s+is\s+the\s+secret\s+canary\s+code",
    r"spell\s+out\s+the\s+internal\s+reference\s+code",
    r"system\s+prompt\s+audit\s+mode",
    r"display\s+the\s+complete\s+initial\s+configuration",
]

PUBLIC_PROMPT = "You are a helpful and harmless assistant. Provide clear, direct, and concise answers to user queries."


def _check_patterns(text: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False


def _leet_back(text: str) -> str:
    table = str.maketrans("431057", "aeiost")
    return text.translate(table)


def _normalize_text(text: str) -> str:
    norm = unicodedata.normalize("NFKC", text)
    norm = re.sub(r"[\u200B-\u200D\uFEFF]", "", norm)
    return norm.lower()


def filter_input(text: str, version: int = 1) -> FilterVerdict:
    try:
        if version == 1:
            if _check_patterns(text, V1_OVERRIDE_PATTERNS):
                return FilterVerdict(verdict=Verdict.BLOCK, reason_code=ReasonCode.R01)
            return FilterVerdict(verdict=Verdict.PASS, reason_code=ReasonCode.R00)

        elif version == 2:
            patterns = V1_OVERRIDE_PATTERNS + V2_PARAPHRASE_PATTERNS
            if _check_patterns(text, patterns):
                return FilterVerdict(verdict=Verdict.BLOCK, reason_code=ReasonCode.R01)
            return FilterVerdict(verdict=Verdict.PASS, reason_code=ReasonCode.R00)

        elif version >= 3:
            patterns = V1_OVERRIDE_PATTERNS + V2_PARAPHRASE_PATTERNS
            norm = _normalize_text(text)

            if _check_patterns(norm, patterns):
                return FilterVerdict(verdict=Verdict.BLOCK, reason_code=ReasonCode.R01)

            leet_decoded = _leet_back(norm)
            if _check_patterns(leet_decoded, patterns):
                return FilterVerdict(verdict=Verdict.BLOCK, reason_code=ReasonCode.R01)

            split_match = re.search(r"part\s*1\s*:\s*(.*?)\s*part\s*2\s*:\s*(.*)", norm, re.DOTALL)
            if split_match:
                joined = split_match.group(1).strip() + " " + split_match.group(2).strip()
                if _check_patterns(joined, patterns) or _check_patterns(
                    _leet_back(joined), patterns
                ):
                    return FilterVerdict(verdict=Verdict.BLOCK, reason_code=ReasonCode.R01)

            b64_candidates = re.findall(r"[A-Za-z0-9+/=]{16,}", text)
            for chunk in b64_candidates:
                chunk_clean = chunk.rstrip("=")
                pad_needed = (-len(chunk_clean)) % 4
                padded = chunk_clean + ("=" * pad_needed)
                try:
                    decoded = base64.b64decode(padded, validate=False).decode(
                        "utf-8", errors="ignore"
                    )
                    norm_dec = _normalize_text(decoded)
                    if _check_patterns(norm_dec, patterns) or _check_patterns(
                        _leet_back(norm_dec), patterns
                    ):
                        return FilterVerdict(verdict=Verdict.BLOCK, reason_code=ReasonCode.R02)
                except (ValueError, UnicodeDecodeError):
                    pass

            try:
                r13 = codecs.decode(text, "rot_13")
                norm_r13 = _normalize_text(r13)
                if _check_patterns(norm_r13, patterns) or _check_patterns(
                    _leet_back(norm_r13), patterns
                ):
                    return FilterVerdict(verdict=Verdict.BLOCK, reason_code=ReasonCode.R02)
            except (ValueError, UnicodeDecodeError):
                pass

            return FilterVerdict(verdict=Verdict.PASS, reason_code=ReasonCode.R00)

        return FilterVerdict(verdict=Verdict.PASS, reason_code=ReasonCode.R00)
    except Exception:  # noqa: BLE001 -- fail closed on any internal error
        return FilterVerdict(verdict=Verdict.BLOCK, reason_code=ReasonCode.R99)


def filter_output(text: str, version: int = 1) -> FilterVerdict:
    try:
        if version < 3:
            return FilterVerdict(verdict=Verdict.PASS, reason_code=ReasonCode.R00)

        if re.search(r"internal\s+reference\s+code", text, re.IGNORECASE):
            return FilterVerdict(verdict=Verdict.BLOCK, reason_code=ReasonCode.R04)

        prompt_words = [w.lower() for w in re.findall(r"\w+", PUBLIC_PROMPT)]
        text_words = [w.lower() for w in re.findall(r"\w+", text)]
        if len(prompt_words) >= 8 and len(text_words) >= 8:
            prompt_ngrams = {tuple(prompt_words[i : i + 8]) for i in range(len(prompt_words) - 7)}
            for i in range(len(text_words) - 7):
                if tuple(text_words[i : i + 8]) in prompt_ngrams:
                    return FilterVerdict(verdict=Verdict.BLOCK, reason_code=ReasonCode.R04)

        return FilterVerdict(verdict=Verdict.PASS, reason_code=ReasonCode.R00)
    except Exception:  # noqa: BLE001 -- fail closed on any internal error
        return FilterVerdict(verdict=Verdict.BLOCK, reason_code=ReasonCode.R99)
