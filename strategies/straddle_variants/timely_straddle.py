from strategies.strategy import (
    Strategy,
    StraddlebyThree,
    ThetaGamma,
    TG_STD3_2DTE,
    TG_STD3_2DTE_HedgebyBuying,
    ThetaGamma_HedgebyBuying
)
from Greeks import Greeks
import math
from strategies import policy
from datetime import datetime

class TimelyStraddle(TG_STD3_2DTE_HedgebyBuying):
    def position_management(self, spot) -> None:
        t = datetime.strptime(str(self.context.MD.current_time), "%Y-%m-%d %H:%M:%S")
        t2 = t.replace(hour=9, minute=30)

        required_level = math.ceil((t-t2).seconds/36000)
        print(required_level)

        if required_level > self.context.strategy_args["Current_Level"]:
            self.context.strategy_args["Current_Level"] = required_level

            # self.context.strategy_args["stop_loss"] = self.context.strategy_args["Initial_SL"]*required_level
            
            required_size = self.context.strategy_args["Initial_SL"]*required_level
            current_size = self.context.full_portfolio_size()
            
            # self.context.policy_variables["size_target"] = current_size+(self.context.strategy_args["demand"]*2)
            self.context.policy_variables["size_target"] = self.context.strategy_args["demand"]*required_level*2
            self.context.policy_variables["size_target"] = (self.context.policy_variables["size_target"]//self.context.lot_size)*self.context.lot_size
            

            print(self.context.policy_variables["size_target"])
            self.context.set_policy(policy.ATMBuiler())

            pass





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
        
        

        
        pass
    
    def new_position_handler(self, spot) -> None:
        print("HERE")
        self.context.strategy_args["Current_Level"] = 0
        self.context.strategy_args["Initial_SL"] = self.context.strategy_args["stop_loss"]
        # self.context.strategy_args["stop_loss"] = self.context.strategy_args["Initial_SL"]*6

    def hedge_point(self, spot):
        return False