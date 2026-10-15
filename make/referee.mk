.PHONY: verify
verify: ## Verify audit log integrity (needs evidence/audit_export.jsonl, evidence/audit_pubkey.hex, evidence/anchors/)
> .venv/bin/python -m referee.verify.verify evidence/audit_export.jsonl \
>   --pubkey evidence/audit_pubkey.hex \
>   --checkpoint $$(ls -t evidence/anchors/*.json | head -1)

.PHONY: tamper-demo
tamper-demo: ## Apply all 5 tampers to in-memory copy of real log and print each failure reason
> .venv/bin/python scripts/tamper_demo.py
