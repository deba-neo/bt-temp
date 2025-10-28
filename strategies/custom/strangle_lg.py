from strategies.strategy import (
    Strategy,
    TG_STD3_2DTE,
)

from strategies import policy
from Greeks import Greeks
import math
from datetime import datetime

class Strangle_LG(Strategy):
    def hedge(self, spot) -> None:
        self.new_position_handler(spot)
        pass
    
    def hedge_point(self, spot) -> bool:
        std_price, _ = self.context.atm_straddle_price(spot)
        is_hedge = self.context.strategy_args["std_position"] - spot < self.context.strategy_args["hedge_range"]*std_price
        return is_hedge
         
    
    def position_management(self, spot) -> None:
        close_time = list(map(int, self.context.strategy_args["close_position_time"].split(":")))
        t = datetime.strptime(str(self.context.MD.current_time), "%Y-%m-%d %H:%M:%S")
        if (
            t
            > t.replace(hour=close_time[0], minute=close_time[1], second=close_time[2], microsecond=0)
            or \
                self.context.strategy_args["close_position"]
            or self.context.hit_stop_loss
        ):
            self.context.policy_variables["size_target"] = 0
            self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["destruction_lots_per_cycle"]
            self.context.set_policy(policy.Destructor())
        return 
    
    def new_position_handler(self, spot) -> None:
        straddle_demand = self.context.strategy_args["demand"]
        wing_demand = self.context.strategy_args["demand"]*self.context.strategy_args["wing_ratio"]
        wing_dist = self.context.strategy_args["wing_dist"]

        std_price, position = self.context.atm_straddle_price(spot)
        
        call_std, put_std = self.context.find_strangle_strikes(position, spot)
        
        call_wing = int(round( (call_std+std_price*wing_dist) / float(self.context.movement))) * self.context.movement
        put_wing = int(round( (put_std-std_price*wing_dist) / float(self.context.movement))) * self.context.movement

        options_list = [f'{put_std}PE', f'{call_std}CE', f'{put_wing}PE', f'{call_wing}CE']
        is_sell_list = [False, False, True, True]
        quantity_list = [straddle_demand, straddle_demand, wing_demand, wing_demand]


        self.context.strategy_args["std_position"] = (call_std + put_std)/2
        self.context.strategy_args["wing_dist"] = wing_dist

        self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["construction_lots_per_cycle"]
        self.context.policy_variables["to_create_portfolio"] = {
            f'{put_std}PE' : -straddle_demand,
            f'{call_std}CE' : -straddle_demand,
            # f'{put_wing}PE' : wing_demand,
            # f'{call_wing}CE' : wing_demand,
        }

        # self.context.make_orders(options_list, is_sell_list, quantity_list)

        for key, value in self.context.portfolio.items():
            self.context.policy_variables["to_create_portfolio"][key] = self.context.policy_variables["to_create_portfolio"].get(key, 0) + value
        
        self.context.set_policy(policy.CustomPortfolioBuilder())
    
    def existing_position_handler(self, spot):
        pass