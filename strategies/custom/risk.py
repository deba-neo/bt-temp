from strategies.strategy import Strategy
from strategies import policy
from Greeks import Greeks
from datetime import datetime
import math

class Risk(Strategy):
    def hedge(self, spot) -> None:
        return super().hedge(spot)
    
    def hedge_point(self, spot) -> bool:
        return super().hedge_point(spot)
    
    def position_management(self, spot) -> None:
        close_time = list(map(int, self.context.strategy_args["close_position_time"].split(":")))
        if (
            datetime.now()
            > datetime.now().replace(hour=close_time[0], minute=close_time[1], second=close_time[2], microsecond=0)
            or \
                self.context.strategy_args["close_position"]
            or self.context.hit_stop_loss):
            self.context.policy_variables["size_target"] = 0
            self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["destruction_lots_per_cycle"]
            self.context.set_policy(policy.Destructor())
            return
        

        if (
            self.context.number_of_calls()
            != self.context.strategy_args["total_calls"]
            or self.context.number_of_puts()
            != self.context.strategy_args["total_puts"]
            or self.context.strategy_args["reset_position"]
        ):
            self.new_position_handler(spot)
            self.context.strategy_args["reset_position"] = False
            pass
        
        pass

    def new_position_handler(self, spot) -> None:
        straddle_price, straddle_position = self.context.atm_straddle_price(spot)
        call_position, put_position = self.context.find_strangle_strikes(straddle_position, spot)

        if self.context.strategy_args["wing_distance_metric"] == "Straddle":
            call_wing_distance = self.context.strategy_args["call_wing_distance"]
            put_wing_distance = self.context.strategy_args["put_wing_distance"]

            call_position = int(round((call_position + call_wing_distance*straddle_price) / float(self.context.movement))) * self.context.movement
            put_position = int(round((put_position - put_wing_distance*straddle_price) / float(self.context.movement))) * self.context.movement
        
        elif self.context.strategy_args["wing_distance_metric"] == "Absolute":
            call_wing_distance = self.context.strategy_args["call_wing_distance"]
            put_wing_distance = self.context.strategy_args["put_wing_distance"]

            call_position = int(round((call_position + call_wing_distance) / float(self.context.movement))) * self.context.movement
            put_position = int(round((put_position - put_wing_distance) / float(self.context.movement))) * self.context.movement
        

        quantity_calls = self.context.strategy_args["total_calls"]
        quantity_puts = self.context.strategy_args["total_puts"]
        
        self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["construction_lots_per_cycle"]
        self.context.policy_variables["to_create_portfolio"] = {
            f"{call_position}CE" : -quantity_calls,
            f"{put_position}PE" : -quantity_puts,
        }
        
        for key, value in self.context.portfolio.items():
            self.context.policy_variables["to_create_portfolio"][key] = self.context.policy_variables["to_create_portfolio"].get(key, 0) + value

        self.context.set_policy(policy.CustomPortfolioBuilder())
        pass
    
    def existing_position_handler(self, spot):
        return super().existing_position_handler(spot)