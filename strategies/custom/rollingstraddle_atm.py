from strategies.strategy import (
    Strategy,
    StraddlebyThree,
    ThetaGamma,
    TG_STD3_2DTE,
    ThetaGamma_HedgebyBuying
)
from strategies import policy
from Greeks import Greeks
import math
from datetime import datetime

class RollingStraddle_ATM(ThetaGamma):
    def hedge(self, spot) -> None:
        self.create_new_position(spot, hedge=True)
        pass


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
            self.context.strategy_args["demand"] = 0
        return 


    
    def new_position_handler(self, spot) -> None:
        self.create_new_position(spot, hedge=False)
        pass    
    
    def create_new_position(self, spot, hedge = False) -> None:
        position = int(round(spot / float(self.context.movement))) * self.context.movement
        call_position, put_position = self.context.find_strangle_strikes(position, spot)
        gcalc = Greeks()

        prices = self.context.get_current_price([
            f'{call_position}CE',
            f'{put_position}PE',
        ])

        print(f"Call Price: {prices[0]}", flush=True)
        print(f"Put Price: {prices[1]}", flush=True)

        ttm = self.context.timeToMaturity()
        if self.context.strategy_args["IVCalc"] == "Reference":
            IV = self.context.strategy_args["refIV"]
        else:
            IV = gcalc.Call_IV(spot, position, self.context.rfr, ttm, prices[0])

        quantity_calls = self.context.strategy_args["demand"]
        quantity_puts = self.context.strategy_args["demand"]

        self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["construction_lots_per_cycle"]
        self.context.policy_variables["to_create_portfolio"] = {
            f"{call_position}CE" : quantity_calls,
            f"{put_position}PE" : quantity_puts,
        }

        for key, value in self.context.portfolio.items():
            self.context.policy_variables["to_create_portfolio"][key] = self.context.policy_variables["to_create_portfolio"].get(key, 0) + value

        self.context.set_policy(policy.CustomPortfolioBuilder())
        pass

    def existing_position_handler(self, spot):
        self.new_position_handler(spot)
        pass


class RollingStraddle_ATM_StraddlebyThree(RollingStraddle_ATM, StraddlebyThree):
    pass

class RollingStraddle_ATM_TG_STD3_2DTE(RollingStraddle_ATM, TG_STD3_2DTE):
    pass


class RollingStraddle_ATM_NewHedge(RollingStraddle_ATM_TG_STD3_2DTE):
    def hedge(self, spot) -> None:
        self.context.strategy_args["num_hedges"] = self.context.strategy_args.get("num_hedges", 0) + 1
        
        if self.context.strategy_args["num_hedges"] % 3 == 0:
            return super().hedge(spot)
        else:
            return ThetaGamma_HedgebyBuying.hedge(self, spot)