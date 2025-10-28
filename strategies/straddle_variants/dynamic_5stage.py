from strategies.strategy import (
    Strategy,
    StraddlebyThree,
    StraddlebyThree_HedgebyBuying, 
    TG_STD3_2DTE,
    TG_STD3_2DTE_HedgebyBuying
)
from Greeks import Greeks
import math
from strategies import policy
from datetime import datetime

class Dynamic5Stage(TG_STD3_2DTE_HedgebyBuying):
    def position_management(self, spot) -> None:
        close_time = list(map(int, self.context.strategy_args["close_position_time"].split(":")))
        t = datetime.strptime(str(self.context.MD.current_time), "%Y-%m-%d %H:%M:%S")
        if (
            t
            > t.replace(hour=close_time[0], minute=close_time[1], second=close_time[2], microsecond=0)
            or \
                self.context.strategy_args["close_position"]
            or self.context.hit_stop_loss):
            self.context.policy_variables["size_target"] = 0
            self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["destruction_lots_per_cycle"]
            self.context.set_policy(policy.Destructor())
            return
        
        current_tranche = self.context.strategy_args["current_tranche"]
        entry_points = self.context.strategy_args["entry_points"]
        exit_points = self.context.strategy_args["exit_points"]
        
        current_straddle_price = self.context.atm_straddle_price(spot)[0]

        vol = self.context.straddle_IV(spot)
        
        projected_gain = self.find_edge(spot, current_straddle_price)

        normalised_entry_point = entry_points[current_tranche]*spot*vol
        normalised_exit_point = exit_points[current_tranche]*spot*vol

        print(f"Current Tranche: {current_tranche  :.2f}")
        print(f"Current Straddle Price: {current_straddle_price  :.2f}")
        print(f"Projected Gain: {projected_gain  :.2f}")
        print(f"Normalised Entry Point: {normalised_entry_point  :.2f}")
        print(f"Normalised Exit Point: {normalised_exit_point  :.2f}")

        # if self.context.full_portfolio_size() > self.context.strategy_args[f"position_size_limit_{current_tranche}"]:
        #     self.context.policy_variables["theta_target"] = self.context.strategy_args[
        #         f"position_size_limit_{current_tranche}"
        #     ]
        #     self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["destruction_lots_per_cycle"]
        #     self.context.set_policy(policy.ThetaDestructor())
        #     return
        
        if projected_gain > normalised_entry_point:
            if t > t.replace(hour=14, minute=30, second=0, microsecond=0):
                return
            
            current_tranche = min(current_tranche+1, 5)
            self.context.strategy_args["current_tranche"] = current_tranche
            # set new target
            self.context.policy_variables["theta_target"] = self.context.strategy_args[
                f"tranche_{current_tranche}_target"
            ]

            self.context.set_policy(policy.ATMThetaBuiler())

        elif projected_gain < normalised_exit_point:
            current_tranche = max(current_tranche-1, 0)
            self.context.strategy_args["current_tranche"] = current_tranche
            # set new target
            self.context.policy_variables["theta_target"] = self.context.strategy_args[
                f"tranche_{current_tranche}_target"
            ]
            self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["construction_lots_per_cycle"]
            self.context.set_policy(policy.ThetaDestructor())
    
    def find_edge(self, spot, current_straddle_price):
        expected_closing_IV = self.context.strategy_args["expected_closing_IV"]
        tte = self.context.timeToMaturity()
        time_in_day = self.context.timeinDay()
        tte_at_day_end = tte - time_in_day
        
        expected_close = self.context.find_straddle_price(spot, tte_at_day_end + 0.01, expected_closing_IV)
        print(f"Expected Straddle Close: {expected_close  :.2f}")
        projected_gain = current_straddle_price - expected_close
        projected_gain /= time_in_day
        return projected_gain
    
    def new_position_handler(self, spot) -> None:
        self.context.strategy_args["current_tranche"] = 0

        tranche1 = self.context.strategy_args["tranche1"]
        tranche2 = self.context.strategy_args["tranche2"]
        tranche3 = self.context.strategy_args["tranche3"]
        tranche4 = self.context.strategy_args["tranche4"]
        tranche5 = self.context.strategy_args["tranche5"]
        
        
        self.context.strategy_args["entry_points"] = [tranche1, tranche2, tranche3, tranche4, tranche5]
        self.set_exit_positions(tranche1, tranche2, tranche3, tranche4, tranche5)

    def existing_position_handler(self, spot):
        try:
            current_tranche = self.context.strategy_args["current_tranche"]
        except:
            current_tranche = 0
        
        self.new_position_handler(spot)
        self.context.strategy_args["current_tranche"] = current_tranche

    def set_exit_positions(self, tranche1, tranche2, tranche3, tranche4, tranche5):

        self.context.strategy_args["exit_points"] = [-math.inf, -math.inf, tranche1, tranche2, tranche3, tranche4]
