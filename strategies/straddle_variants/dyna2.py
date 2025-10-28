from strategies.strategy import Strategy, StraddlebyThree, StraddlebyThree_HedgebyBuying, TG_STD3_2DTE
from Greeks import Greeks
import math
from strategies import policy
from datetime import datetime

class Dynamic2(TG_STD3_2DTE):
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
        
        
        self.iatr_tracker(spot)


    
    def new_position_handler(self, spot) -> None:
        self.context.strategy_args["current_tranche"] = 0

        tranche1 = self.context.strategy_args["tranche1"]
        tranche2 = self.context.strategy_args["tranche2"]
        tranche3 = self.context.strategy_args["tranche3"]
        
        self.context.strategy_args["entry_points"] = [tranche1, tranche2, tranche3, tranche3*2]
        self.set_exit_positions(tranche1, tranche2, tranche3)




        self.context.strategy_args["Lows"] = []
        self.context.strategy_args["Highs"] = []

        iv = self.context.straddle_IV(spot)
        self.context.strategy_args["sodiv"] = iv

        self.context.strategy_args["prev_atr"] = 0
        self.context.strategy_args["prev_low"] = spot
        self.context.strategy_args["prev_high"] = spot

    def existing_position_handler(self, spot):
        try:
            current_tranche = self.context.strategy_args["current_tranche"]
        except:
            current_tranche = 0
        
        self.new_position_handler(spot)
        self.context.strategy_args["current_tranche"] = current_tranche

    def set_exit_positions(self, tranche1, tranche2, tranche3):
        self.context.strategy_args["exit_points"] = [0, (tranche1-0)/2, tranche1, tranche2]

    def iatr_tracker(self, spot):
        self.context.strategy_args["DataStorage"] = [self.context.strategy_args["Lows"], self.context.strategy_args["Highs"]]

        prev_atr = self.context.strategy_args["prev_atr"]
        prev_low = self.context.strategy_args["prev_low"]
        prev_high = self.context.strategy_args["prev_high"]
        
        
        current_atr = self.context.high - self.context.low
        
        self.context.strategy_args["prev_atr"] = current_atr
        self.context.strategy_args["prev_high"] = self.context.high
        self.context.strategy_args["prev_low"] = self.context.low
        
        print(prev_atr)
        print(current_atr)

        if not current_atr > prev_atr:
            return
        
        iv = self.context.straddle_IV(spot)
        start_of_day_iv = self.context.strategy_args["sodiv"]

        
        time = 1-self.context.timeinDay()
        dte = self.context.timeToMaturity()

        # print("Here")
        
        # New Low
        if prev_low > self.context.low:
            self.context.strategy_args["Lows"].append([current_atr, iv, start_of_day_iv, time, dte, spot])
            return

        # New High
        self.context.strategy_args["Highs"].append([current_atr, iv, start_of_day_iv, time, dte, spot])

        
        pass


class Dynamic2Conservative(Dynamic2):
    def set_exit_positions(self, tranche1, tranche2, tranche3):
        self.context.strategy_args["exit_points"] = [0, (tranche1-0)/2, (tranche2+tranche1)/2, (tranche3+tranche2)/2]


class Dynamic2NoExit(Dynamic2):
    def set_exit_positions(self, tranche1, tranche2, tranche3):
        self.context.strategy_args["exit_points"] = [0, 0, 0, 0]


class Dynamic2_HedgebyBuying(Dynamic2, StraddlebyThree_HedgebyBuying):
    pass