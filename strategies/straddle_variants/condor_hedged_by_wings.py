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

class Condor_with_Wings(TG_STD3_2DTE):
    def hedge(self, spot) -> None:
        strategy_args = self.context.strategy_args
        ref_IV = strategy_args["refIV"]
        hedge_amount = strategy_args["hedge_amount"]

        if self.context.greeks["portfolio_delta"] > 0:
            self.context.hedge_by_buying_put_spreads(
                spot, self.context.greeks["portfolio_delta"]*hedge_amount, ref_IV
            )
        else:
            self.context.hedge_by_buying_call_spreads(
                spot, self.context.greeks["portfolio_delta"]*hedge_amount, ref_IV
            )

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
        
        

        
        pass
    
    def new_position_handler(self, spot) -> None:
        self.context.policy_variables["size_target"] = self.context.strategy_args["demand"]*4
        self.context.set_policy(policy.ATMBuiler())
        pass