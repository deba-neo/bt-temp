from strategies.strategy import Strategy, StraddlebyThree, StraddlebyThree_HedgebyBuying, TG_STD3_2DTE
from Greeks import Greeks
import math
from strategies import policy
from datetime import datetime

class SmartStraddle(TG_STD3_2DTE):
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
        
        self.context.strategy_args["ATR_size"] = self.get_atr_sizing(spot)
        kk = self.context.strategy_args["ATR_size"]
        print(f"ATR Size : {kk}")
        
        current_tranche = self.context.strategy_args["current_tranche"]
        
        self.context.strategy_args["total_tranches"].append(self.context.full_portfolio_size())

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

        if self.context.full_portfolio_size() > self.context.strategy_args[f"position_size_limit_{current_tranche}"]:
            self.context.policy_variables["size_target"] = self.context.strategy_args[
                f"position_size_limit_{current_tranche}"
            ]
            self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["destruction_lots_per_cycle"]
            self.context.set_policy(policy.Destructor())
            return
        
        if projected_gain > normalised_entry_point:
            if t > t.replace(hour=14, minute=30, second=0, microsecond=0):
                return
            
            current_tranche = min(current_tranche+1, 3)
            self.context.strategy_args["current_tranche"] = current_tranche
            # set new target
            self.context.policy_variables["size_target"] = self.context.strategy_args[
                f"tranche_{current_tranche}_target"
            ] + self.context.strategy_args[f"ATR_size"]

            print(f"tranche_{current_tranche}_target")


            print(self.context.strategy_args[f"tranche_{current_tranche}_target"])
            tt = self.context.policy_variables["size_target"]
            
            print(tt)
            self.context.set_policy(policy.ATMBuiler())

        elif projected_gain < normalised_exit_point:
            current_tranche = max(current_tranche-1, 0)
            self.context.strategy_args["current_tranche"] = current_tranche
            # set new target

            if current_tranche == 0:
                self.context.policy_variables["size_target"] = 0
            else:    
                self.context.policy_variables["size_target"] = self.context.strategy_args[
                    f"tranche_{current_tranche}_target"
                ] + self.context.strategy_args[f"ATR_size"]
            
            self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["construction_lots_per_cycle"]
            self.context.set_policy(policy.Destructor())


        elif self.context.strategy_args["ATR"] < self.context.strategy_args[f"ATR_size"]:
            self.context.strategy_args["ATR"] = self.context.strategy_args[f"ATR_size"]
            # set new target
            self.context.policy_variables["size_target"] = self.context.strategy_args[
                f"tranche_{current_tranche}_target"
            ] + self.context.strategy_args[f"ATR_size"]
            self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["construction_lots_per_cycle"]
            self.context.set_policy(policy.ATMBuiler())

    
    def get_atr_sizing(self, spot):
        max_atr_size = self.context.strategy_args[f"tranche_3_target"]

        avg_atr = self.context.strategy_args["Average_ATR"]

        completed_atr = (self.context.high - self.context.low)/self.context.close

        mult = min(completed_atr/avg_atr, 1)

        print(f"Completed ATR : {completed_atr}")
        print(f"Completed ATR Amount: {mult*100}%")

        return max_atr_size*mult

        pass
    
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
        
        self.context.strategy_args["entry_points"] = [tranche1, tranche2, tranche3, tranche3*2]
        self.context.strategy_args["total_tranches"] = []

        max_size = self.context.strategy_args[f"tranche_3_target"]
        
        self.context.strategy_args[f"tranche_1_target"] = 0
        self.context.strategy_args[f"tranche_2_target"] = max_size/4
        self.context.strategy_args[f"tranche_3_target"] = max_size/2
        
        self.context.strategy_args[f"ATR_size"] = 0

        self.context.strategy_args["ATR"] = 0

        self.set_exit_positions(tranche1, tranche2, tranche3)

    def existing_position_handler(self, spot):
        try:
            current_tranche = self.context.strategy_args["current_tranche"]
        except:
            current_tranche = 0
        
        self.new_position_handler(spot)
        self.context.strategy_args["current_tranche"] = current_tranche

    def set_exit_positions(self, tranche1, tranche2, tranche3):
        self.context.strategy_args["exit_points"] = [0, (tranche1-0)/2, tranche1, tranche2]


class SmartStraddlConservative(SmartStraddle):
    def set_exit_positions(self, tranche1, tranche2, tranche3):
        self.context.strategy_args["exit_points"] = [0, (tranche1-0)/2, (tranche2+tranche1)/2, (tranche3+tranche2)/2]


class SmartStraddleNoExit(SmartStraddle):
    def set_exit_positions(self, tranche1, tranche2, tranche3):
        self.context.strategy_args["exit_points"] = [0, 0, 0, 0]


class SmartStraddle_HedgebyBuying(SmartStraddle, StraddlebyThree_HedgebyBuying):
    pass