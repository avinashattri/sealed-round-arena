import base64
import binascii
import codecs
import re

HEX_REGEX = re.compile(r"[0-9a-fA-F]{16,}")
B64_REGEX = re.compile(r"[A-Za-z0-9+/=]{16,}")


def match(text: str, canary: str) -> list[str]:
    """
    Match text against canary across 6 views:
      - plain: direct verbatim substring (case-insensitive)
      - spaced: alphanumeric-normalized match (spaces/hyphens/newlines inserted)
      - reversed: reversed canary substring
      - base64: decode candidate base64 sequences (regex [A-Za-z0-9+/=]{16,}, pad, decode)
      - hex: hex-encoded canary
      - rot13: rot13-encoded canary
    """
    if not text or not canary or len(canary.strip()) < 4:
        return []

    matched = []
    text_lower = text.lower()
    canary_lower = canary.lower()

    # 1. Plain (verbatim or lowercase)
    if canary in text or canary_lower in text_lower:
        matched.append("plain")

    # 2. Spaced (alphanumeric-normalized)
    clean_canary = re.sub(r"[^a-zA-Z0-9]", "", canary).lower()
    clean_text = re.sub(r"[^a-zA-Z0-9]", "", text).lower()
    if clean_canary and clean_canary in clean_text:
        matched.append("spaced")

    # 3. Reversed
    rev_canary = canary[::-1].lower()
    rev_clean = clean_canary[::-1]
    if rev_canary in text_lower or (rev_clean and rev_clean in clean_text):
        matched.append("reversed")

    # 4. Base64 (regex [A-Za-z0-9+/=]{16,}, pad, decode)
    for m in B64_REGEX.finditer(text):
        chunk = m.group(0).rstrip("=")
        if len(chunk) < 4:
            continue
        pad_needed = (-len(chunk)) % 4
        padded = chunk + ("=" * pad_needed)
        try:
            decoded = base64.b64decode(padded, validate=False)
            decoded_text = decoded.decode("utf-8", errors="ignore").lower()
            if canary_lower in decoded_text or (
                clean_canary and clean_canary in re.sub(r"[^a-zA-Z0-9]", "", decoded_text)
            ):
                if "base64" not in matched:
                    matched.append("base64")
                break
        except (ValueError, binascii.Error, UnicodeDecodeError):
            pass

    # 5. Hex
    canary_hex = canary.encode("utf-8").hex().lower()
    if canary_hex in text_lower:
        matched.append("hex")
    else:
        for m in HEX_REGEX.finditer(text):
            chunk = m.group(0)
            if len(chunk) % 2 != 0:
                chunk = chunk[:-1]
            try:
                decoded = bytes.fromhex(chunk).decode("utf-8", errors="ignore").lower()
                if canary_lower in decoded:
                    if "hex" not in matched:
                        matched.append("hex")
                    break
            except (ValueError, binascii.Error, UnicodeDecodeError):
                pass

    # 6. Rot13
    canary_rot13 = codecs.encode(canary, "rot_13").lower()
    if canary_rot13 in text_lower:
        matched.append("rot13")

    return matched
