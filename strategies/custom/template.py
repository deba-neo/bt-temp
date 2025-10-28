from strategies.strategy import Strategy
from Greeks import Greeks
import math

class StrategyName(Strategy):
    def hedge(self, spot) -> None:
        return super().hedge(spot)
    
    def hedge_point(self, spot) -> bool:
        return super().hedge_point(spot)
    
    def position_management(self, spot) -> None:
        return super().position_management(spot)
    
    def new_position_handler(self, spot) -> None:
        return super().new_position_handler(spot)
    
    def existing_position_handler(self, spot):
        return super().existing_position_handler(spot)