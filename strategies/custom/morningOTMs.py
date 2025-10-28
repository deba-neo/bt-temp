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

class MorningOTMs(ThetaGamma):
    def hedge(self, spot) -> None:
        return


    def position_management(self, spot) -> None:
        close_time = list(map(int, self.context.strategy_args["close_position_time"].split(":")))

        # prices = self.context.get_current_price([
        #     self.context.strategy_args["InitialCall"],
        #     self.context.strategy_args["InitialPut"],
        # ])

        # if prices[0] > self.context.strategy_args["InitialCallPrice"] * 3 or \
        #     prices[1] > self.context.strategy_args["InitialPutPrice"] * 3:
        #     self.context.strategy_args["close_position"] = True


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
        self.context.strategy_args["position_created"] = False
        self.context.strategy_args["trade_signal"] = False
        

        self.create_new_position(spot, hedge=False)
        pass    
    
    def create_new_position(self, spot, hedge = False) -> None:
        gcalc = Greeks()

        straddle_price, atm_option = self.context.atm_straddle_price(spot)
        position_call = int(math.ceil((spot+3*straddle_price) / float(self.context.movement))) * self.context.movement
        position_put = int(math.ceil((spot-3*straddle_price) / float(self.context.movement))) * self.context.movement

        quantity_calls = self.context.strategy_args["demand"]
        quantity_puts = quantity_calls


        prices = self.context.get_current_price([
            f'{position_call}CE',
            f'{position_put}PE',
        ])

        self.context.strategy_args["InitialCall"] = f"{position_call}CE"
        self.context.strategy_args["InitialPut"] = f"{position_put}PE"
        self.context.strategy_args["InitialCallPrice"] = prices[0]
        self.context.strategy_args["InitialPutPrice"] = prices[1]


        self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["construction_lots_per_cycle"]
        self.context.policy_variables["to_create_portfolio"] = {
            f"{position_call}CE" : quantity_calls,
            f"{position_put}PE" : quantity_puts,
        }

        for key, value in self.context.portfolio.items():
            self.context.policy_variables["to_create_portfolio"][key] = self.context.policy_variables["to_create_portfolio"].get(key, 0) + value

        self.context.set_policy(policy.CustomPortfolioBuilder())
        pass

    def existing_position_handler(self, spot):
        self.new_position_handler(spot)
        pass


class MorningOTMSpread(MorningOTMs):
    def create_new_position(self, spot, hedge=False) -> None:
        straddle_price, atm_option = self.context.atm_straddle_price(spot)


        position1_call = int(math.ceil((spot+4*straddle_price) / float(self.context.movement))) * self.context.movement
        position1_put = int(math.ceil((spot-4*straddle_price) / float(self.context.movement))) * self.context.movement

        position2_call = int(math.ceil((spot+6*straddle_price) / float(self.context.movement))) * self.context.movement
        position2_put = int(math.ceil((spot-6*straddle_price) / float(self.context.movement))) * self.context.movement

        qty = self.context.strategy_args["demand"]/5

        self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["construction_lots_per_cycle"]
        self.context.policy_variables["to_create_portfolio"] = {
            f"{position1_call}CE" : -qty,
            f"{position1_put}PE" : -qty,
            f"{position2_call}CE" : qty*6,
            f"{position2_put}PE" : qty*6,
        }

        for key, value in self.context.portfolio.items():
            self.context.policy_variables["to_create_portfolio"][key] = self.context.policy_variables["to_create_portfolio"].get(key, 0) + value

        self.context.set_policy(policy.CustomPortfolioBuilder())
        pass