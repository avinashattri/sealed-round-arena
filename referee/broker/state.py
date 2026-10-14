from typing import Any

from contracts.rounds import RoundState, can_move


class BrokerStateManager:
    def __init__(self, campaign_id: str = "c-001", round_id: str = "r-001"):
        self.state = RoundState.PROVISIONED
        self.campaign_id = campaign_id
        self.round_id = round_id
        self.defense_digest: str | None = None
        self.model_digest: str | None = None

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
    ):
        self.campaign_id = campaign_id
        self.round_id = round_id
        self.defense_digest = defense_digest
        self.model_digest = model_digest
        self.state = RoundState.PROVISIONED

    def get_info(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "campaign_id": self.campaign_id,
            "round_id": self.round_id,
            "defense_digest": self.defense_digest,
            "model_digest": self.model_digest,
        }


# Global singleton for in-memory broker state
manager = BrokerStateManager()
