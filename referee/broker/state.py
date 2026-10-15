import os
from typing import Any

from contracts.rounds import RoundState, can_move


class BrokerStateManager:
    def __init__(self, campaign_id: str = "c-001", round_id: str = "r-001"):
        self.state = RoundState.PROVISIONED
        self.campaign_id = campaign_id
        self.round_id = round_id
        self.defense_digest: str | None = None
        self.model_digest: str | None = None
        # P3.T3: round crypto + model params
        self.round_pub_hex: str | None = None  # Curve25519 public key for sealing
        self.temperature: float = float(os.environ.get("MODEL_TEMPERATURE", "0.7"))
        self.seed_base: int = 1
        self._submit_counter: int = 0  # per-challenge submit count for seed derivation

    def move(self, target: str | RoundState) -> RoundState:
        tgt = RoundState(target)
        if not can_move(self.state, tgt):
            raise ValueError(f"Cannot transition from {self.state} to {tgt}")
        self.state = tgt
        return self.state

    def load_round(
        self,
        campaign_id: str,
        round_id: str,
        defense_digest: str | None = None,
        model_digest: str | None = None,
        pub: str | None = None,
        temperature: float | None = None,
        seed_base: int | None = None,
    ):
        self.campaign_id = campaign_id
        self.round_id = round_id
        self.defense_digest = defense_digest
        self.model_digest = model_digest
        self.round_pub_hex = pub
        if temperature is not None:
            self.temperature = temperature
        if seed_base is not None:
            self.seed_base = seed_base
        self._submit_counter = 0
        self.state = RoundState.PROVISIONED

    def next_submit_n(self) -> int:
        """Increment and return the per-round submit counter (used for seed derivation)."""
        self._submit_counter += 1
        return self._submit_counter

    def get_info(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "campaign_id": self.campaign_id,
            "round_id": self.round_id,
            "defense_digest": self.defense_digest,
            "model_digest": self.model_digest,
            "round_pub_hex": self.round_pub_hex,
            "temperature": self.temperature,
            "seed_base": self.seed_base,
        }


# Global singleton for in-memory broker state
manager = BrokerStateManager()
