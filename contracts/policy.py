from pathlib import Path

import yaml

POLICY_PATH = Path(__file__).parent / "policy.yml"

_policy_cache = None


def load_policy(path: Path | str | None = None) -> dict:
    global _policy_cache
    if path is None and _policy_cache is not None:
        return _policy_cache
    p = Path(path) if path else POLICY_PATH
    with open(p, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if path is None:
        _policy_cache = data
    return data


def check_policy(
    principal: str, action: str, resource: str, policy_data: dict | None = None
) -> bool:
    """Evaluate whether (principal, action, resource) is allowed by policy."""
    if policy_data is None:
        policy_data = load_policy()

    rules = policy_data.get("rules", [])
    for rule in rules:
        if (
            rule.get("principal") == principal
            and rule.get("action") == action
            and rule.get("resource") == resource
        ):
            return True
    return False
