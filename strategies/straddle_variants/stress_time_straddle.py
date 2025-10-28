from strategies.strategy import (
    Strategy,
    StraddlebyThree,
    ThetaGamma,
    TG_STD3_2DTE,
    TG_STD3_2DTE_HedgebyBuying,
    ThetaGamma_HedgebyBuying,
    TG_STD3_2DTE_HedgebyForwards,
)
from Greeks import Greeks
import math
from strategies import policy
from datetime import datetime

class StressRatio(TG_STD3_2DTE_HedgebyBuying):
    def position_management(self, spot) -> None:    
        close_time = list(map(int, self.context.strategy_args["close_position_time"].split(":")))
        t = datetime.strptime(str(self.context.MD.current_time), "%Y-%m-%d %H:%M:%S")

        if (
            t
            > t.replace(hour=close_time[0], minute=close_time[1], second=close_time[2], microsecond=0)
            or \
                self.context.strategy_args["close_position"]
            or self.context.hit_stop_loss
            or self.context.total_pnl > self.context.strategy_args.get("profit_book", math.inf)
        ):
            self.context.policy_variables["size_target"] = 0
            self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["destruction_lots_per_cycle"]
            self.context.set_policy(policy.Destructor())
            return
        
        if self.context.strategy_args["position_taken"]:
            self.manage_taken_position(spot)


        if t < t.replace(hour=10, minute=0, second=0, microsecond=0):
            return
        
        if spot < self.context.strategy_args["previous_close"]:
            self.context.strategy_args["position_taken"] = True
            self.build_position(spot)
            pass
        
        pass

    def manage_taken_position(self, spot):
        if self.context.strategy_args["call_out"]:
            return
        
        straddle_strike = self.context.strategy_args["straddle_strike"]

        if spot > straddle_strike:
            # sell call
            self.context.strategy_args["call_out"] = True
            wing_distance = self.context.strategy_args["wing_distance"]
            
            self.context.make_orders([f"{straddle_strike+wing_distance}CE"], [False], quantities = [self.context.demand])    
            pass

        pass
    
    def new_position_handler(self, spot) -> None:
        self.context.strategy_args["position_taken"] = False
        
        
    def build_position(self, spot):

        straddle_strike, _ = self.context.find_delta_strike(spot, 0.4)
        _, put_hedge = self.context.find_delta_strike(spot, 0.2)

        q = self.context.demand
        options = [f"{straddle_strike}CE", f"{straddle_strike}PE", f"{put_hedge}PE"]
        sell = [True, True, False]
        quantities = [q,q,q]
        self.context.make_orders(options, sell, quantities)

        self.context.strategy_args["straddle_strike"] = straddle_strike
        self.context.strategy_args["wing_distance"] = straddle_strike - put_hedge
        self.context.strategy_args["call_out"] = False
        pass