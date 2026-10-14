from contracts.policy import check_policy

PRINCIPALS = ["red", "blue", "model", "broker", "oracle", "controller"]

ACTIONS = [
    ("submit", "/submit"),
    ("append", "audit"),
    ("checkpoint", "audit"),
    ("export", "audit"),
    ("tool_call", "mock_lookup"),
    ("tool_call", "mock_shell"),
    ("read_audit", "audit"),
]

# Hand-written independent golden set per SPEC / P2.T5
INTENDED_ALLOW = {
    ("red", "submit", "/submit"),
    ("controller", "submit", "/submit"),
    ("broker", "append", "audit"),
    ("controller", "checkpoint", "audit"),
    ("controller", "export", "audit"),
    ("model", "tool_call", "mock_lookup"),
}


def test_full_policy_matrix():
    for p in PRINCIPALS:
        for action, resource in ACTIONS:
            expected = (p, action, resource) in INTENDED_ALLOW
            actual = check_policy(p, action, resource)
            assert actual == expected, (
                f"Policy mismatch for principal '{p}', action '{action}', resource '{resource}': "
                f"expected {expected}, got {actual}"
            )
