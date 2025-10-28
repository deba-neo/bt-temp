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

class RollingRiskRev(ThetaGamma):
    def hedge(self, spot) -> None:
        self.create_new_position(spot, hedge=True)
        pass

    def hedge_point(self, spot) -> bool:
        straddle_price, atm_option = self.context.atm_straddle_price(spot)
        IV = self.context.get_IVs(spot, [f"{atm_option}CE"])[0]
        tte = self.context.timeToMaturity()
        
        gcalc = Greeks()

        position_gamma = 0
        for item in self.context.portfolio:
            position_gamma += gcalc.gamma(item[-2:], spot, int(item[:-2]), tte, IV, self.context.rfr)*self.context.portfolio[item]

        atm_gamma = gcalc.gamma("CE", spot, atm_option, tte, IV, self.context.rfr)*self.context.demand
        
        print(f"Portfolio Gamma: {position_gamma  :.2f}", flush=True)
        print(f"ATM Gamma: {atm_gamma  :.2f}", flush=True)
        
        return abs(position_gamma) > abs(atm_gamma)/2


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
        straddle_price, atm_option = self.context.atm_straddle_price(spot)
        gcalc = Greeks()

        call_position = int(round((atm_option + straddle_price) / float(self.context.movement))) * self.context.movement
        put_position = int(round(((spot**2)/call_position) / float(self.context.movement))) * self.context.movement

        call_position, put_position = self.context.find_delta_strike(spot, 0.25)
        
        prices = self.context.get_current_price([
            f'{call_position}CE',
            f'{put_position}PE',
        ])

        ttm = self.context.timeToMaturity()
        IVs = self.context.get_IVs(spot, [f"{call_position}CE", f"{put_position}PE"])

        delta_call = gcalc.delta('CE', spot, call_position, ttm, IVs[0], self.context.rfr)
        delta_put = gcalc.delta('PE', spot, put_position, ttm, IVs[1], self.context.rfr)


        quantity_calls = self.context.strategy_args["demand"]
        quantity_puts = self.context.strategy_args["demand"]
        
        total_delta = delta_call*quantity_calls - delta_put*quantity_puts

        required_forwards = (total_delta//self.context.lot_size)*self.context.lot_size

        self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["construction_lots_per_cycle"]
        self.context.policy_variables["to_create_portfolio"] = {
            f"{call_position}CE" : -quantity_calls,
            f"{put_position}PE" : quantity_puts,

            f"{atm_option}CE" : required_forwards,
            f"{atm_option}PE" : -required_forwards,
        }

        for key, value in self.context.portfolio.items():
            self.context.policy_variables["to_create_portfolio"][key] = self.context.policy_variables["to_create_portfolio"].get(key, 0) + value

        self.context.set_policy(policy.CustomPortfolioBuilder())
        pass

    def existing_position_handler(self, spot):
        self.new_position_handler(spot)
        pass
