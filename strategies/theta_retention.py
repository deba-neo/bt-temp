from BaseStraddle import BaseStraddle
from XTConnect.APIWrapper import Interaction

# theta retention using futures
class ThetaRetention(BaseStraddle):
    def __init__(self, index: str, expiry: str, rfr: float, instruments: list, Order: Interaction, demand: int) -> None:
        super().__init__(index, expiry, rfr, instruments, Order, demand)

    def adjust(self, spot):
        return super().adjust(spot)