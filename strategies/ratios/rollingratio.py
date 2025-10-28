from strategies.strategy import (
    Strategy,
    StraddlebyThree,
    ThetaGamma,
    TG_STD3_2DTE,
)
from strategies import policy
from Greeks import Greeks
import math
from datetime import datetime

class RollingBCRS(ThetaGamma):
    def hedge(self, spot) -> None:
        # lots = 0
        # for key, quantity in self.context.portfolio.items():
        #     lots = max(lots, abs(quantity)//self.context.lot_size + 1)
        
        self.create_new_position(spot, hedge=True)
        pass

    def hedge_point(self, spot):
        call_strike1 = self.context.strategy_args["call_strike1"]

        gcalc = Greeks()

        prices = self.context.get_current_price([
            f'{call_strike1}CE',
        ])

        ttm = self.context.timeToMaturity()
        IV = gcalc.IV(spot, call_strike1, self.context.rfr, ttm, prices[0], "CE")
        delta = gcalc.delta('CE', spot, call_strike1, ttm, IV, self.context.rfr)

        if delta < 0.2 or delta > 0.6:
            self.create_new_position(spot, hedge=True)
        

    def position_management(self, spot) -> None:
        close_time = list(map(int, self.context.strategy_args["close_position_time"].split(":")))
        if (
            datetime.now()
            > datetime.now().replace(hour=close_time[0], minute=close_time[1], second=close_time[2], microsecond=0)
            or \
                self.context.strategy_args["close_position"]
            or self.context.hit_stop_loss
        ):
            self.context.policy_variables["size_target"] = 0
            self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["destruction_lots_per_cycle"]
            self.context.set_policy(policy.Destructor())
            self.context.strategy_args["demand"] = 0
        
        straddle_price, atm_option = self.context.atm_straddle_price(spot)
        print(f"Straddle Price: {straddle_price}")
        return 


    
    def new_position_handler(self, spot) -> None:
        self.create_new_position(spot, hedge=False)
        pass    
    
    def create_new_position(self, spot, hedge = False) -> None:
        call_strike1, _ = self.context.find_delta_strike(spot, 0.4)
        call_strike2, _ = self.context.find_delta_strike(spot, 0.2)

        self.context.strategy_args["call_strike1"] = call_strike1

        quantity = self.context.strategy_args["demand"]

        self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["construction_lots_per_cycle"]
        self.context.policy_variables["to_create_portfolio"] = {
            f"{call_strike1}CE" : -quantity,
            f"{call_strike2}CE" : 2*quantity,
        }

        # clears current portfolio
        for key, value in self.context.portfolio.items():
            self.context.policy_variables["to_create_portfolio"][key] = self.context.policy_variables["to_create_portfolio"].get(key, 0) + value

        self.context.set_policy(policy.CustomPortfolioBuilder())
        pass

    def existing_position_handler(self, spot):
        self.new_position_handler(spot)
        pass


class RollingBPRS(ThetaGamma):
    def hedge(self, spot) -> None:
        self.create_new_position(spot, hedge=True)
        pass

    def hedge_point(self, spot):
        put_strike1 = self.context.strategy_args["put_strike1"]

        gcalc = Greeks()

        prices = self.context.get_current_price([
            f'{put_strike1}PE',
        ])

        ttm = self.context.timeToMaturity()
        IV = gcalc.IV(spot, put_strike1, self.context.rfr, ttm, prices[0], "CE")
        delta = gcalc.delta('PE', spot, put_strike1, ttm, IV, self.context.rfr)
        delta = abs(delta)

        if delta < 0.2 or delta > 0.6:
            self.create_new_position(spot, hedge=True)
        

    def position_management(self, spot) -> None:
        close_time = list(map(int, self.context.strategy_args["close_position_time"].split(":")))
        if (
            datetime.now()
            > datetime.now().replace(hour=close_time[0], minute=close_time[1], second=close_time[2], microsecond=0)
            or \
                self.context.strategy_args["close_position"]
            or self.context.hit_stop_loss
        ):
            self.context.policy_variables["size_target"] = 0
            self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["destruction_lots_per_cycle"]
            self.context.set_policy(policy.Destructor())
            self.context.strategy_args["demand"] = 0
        
        straddle_price, atm_option = self.context.atm_straddle_price(spot)
        print(f"Straddle Price: {straddle_price}")
        return 


    
    def new_position_handler(self, spot) -> None:
        self.create_new_position(spot, hedge=False)
        pass    
    
    def create_new_position(self, spot, hedge = False) -> None:
        call_strike1, put_strike1 = self.context.find_delta_strike(spot, 0.4)
        call_strike2, put_strike2 = self.context.find_delta_strike(spot, 0.2)

        self.context.strategy_args["put_strike1"] = put_strike1

        quantity = self.context.strategy_args["demand"]

        self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["construction_lots_per_cycle"]
        self.context.policy_variables["to_create_portfolio"] = {
            f"{put_strike1}PE" : -quantity,
            f"{put_strike2}PE" : 2*quantity,
        }

        # clears current portfolio
        for key, value in self.context.portfolio.items():
            self.context.policy_variables["to_create_portfolio"][key] = self.context.policy_variables["to_create_portfolio"].get(key, 0) + value

        self.context.set_policy(policy.CustomPortfolioBuilder())
        pass

    def existing_position_handler(self, spot):
        self.new_position_handler(spot)
        pass