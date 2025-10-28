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

class RollingStraddle_LHS(ThetaGamma):
    def hedge(self, spot) -> None:
        lots = 0
        for key, quantity in self.context.portfolio.items():
            lots = max(lots, abs(quantity)//self.context.lot_size + 1)
        
        # if self.no_strike_change(spot):
        #     self.hedge_with_puts(spot)
        #     return
        
        # self.context.change_position_size(maximum_number_of_lots_per_cycle=lots, decrease=True)
        self.create_new_position(spot, hedge=True)
        pass

    def no_strike_change(self, spot):
        new_position = self.get_build_strike(spot)
        for key, quantity in self.context.portfolio.items():
            if quantity != 0:
                current_strike = int(key[:-2])
                break
        
        if new_position == current_strike:
            return True
        else:
            return False

    def hedge_with_puts(self, spot):
        position = self.get_build_strike(spot)

        gcalc = Greeks()

        prices = self.context.get_current_price([
            f'{position}CE',
            f'{position}PE',
        ])

        ttm = self.context.timeToMaturity()
        IV = gcalc.Call_IV(spot, position, self.context.rfr, ttm, prices[0])

        delta_call = gcalc.delta('CE', spot, position, ttm, IV, self.context.rfr)
        delta_put = gcalc.delta('PE', spot, position, ttm, IV, self.context.rfr)

        ratio = abs(delta_put/delta_call)

        quantity_calls = self.context.strategy_args["demand"]
        quantity_puts = quantity_calls/ratio

        current_quantity = self.context.portfolio[f'{position}PE']      # negative number

        buyquantity = abs(current_quantity)-quantity_puts

        # whether to buy or sell
        buyquantity, sellp = (buyquantity, False) if (buyquantity > 0) else (abs(buyquantity), True)

        print(buyquantity)

        options = [f"{position}PE"]
        sell = [sellp]
        quantities = [buyquantity]

        self.context.make_orders(options, sell, quantities)
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
        position = int(math.floor(spot / float(self.context.movement))) * self.context.movement
        gcalc = Greeks()

        prices = self.context.get_current_price([
            f'{position}CE',
            f'{position}PE',
        ])

        print(f"Call Price: {prices[0]}", flush=True)
        print(f"Put Price: {prices[1]}", flush=True)

        ttm = self.context.timeToMaturity()
        if self.context.strategy_args["IVCalc"] == "Reference":
            IV = self.context.strategy_args["refIV"]
        else:
            IV = gcalc.Put_IV(spot, position, self.context.rfr, ttm, prices[0])

        delta_call = gcalc.delta('CE', spot, position, ttm, IV, self.context.rfr)
        delta_put = gcalc.delta('PE', spot, position, ttm, IV, self.context.rfr)

        ratio = abs(delta_put/delta_call)
        ratio = abs(delta_call/delta_put)
        # if ratio>=3:
        #     self.context.strategy_args["close_position"] = True

        quantity_puts = self.context.strategy_args["demand"]
        quantity_calls = quantity_puts/ratio

        # lower hedge when no strike change
        # no_change_hedge_amt = 1/3
        # if hedge and self.no_strike_change(spot):
        #     if quantity_calls < -self.context.portfolio[f"{position}CE"]:
        #         # 1/3rd the distance between current and final number of puts
        #         quantity_calls = quantity_calls + (-self.context.portfolio[f"{position}CE"]-quantity_calls)*(1-no_change_hedge_amt)
        #     pass

        quantity_calls = (int(quantity_calls/self.context.lot_size))*self.context.lot_size

        # options = [f"{position}CE", f"{position}PE"]
        # sell = [True, True]
        # quantities = [quantity_calls, quantity_puts]
        # self.context.make_orders(options, sell, quantities)

        self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["construction_lots_per_cycle"]
        self.context.policy_variables["to_create_portfolio"] = {
            f"{position}CE" : quantity_calls,
            f"{position}PE" : quantity_puts,
        }

        for key, value in self.context.portfolio.items():
            self.context.policy_variables["to_create_portfolio"][key] = self.context.policy_variables["to_create_portfolio"].get(key, 0) + value

        self.context.set_policy(policy.CustomPortfolioBuilder())
        pass

    def existing_position_handler(self, spot):
        self.new_position_handler(spot)
        pass

    def get_build_strike(self, spot):
        strike = int(math.floor(spot / float(self.context.movement))) * self.context.movement

        return strike


class RollingStraddle_LHS_StraddlebyThree(RollingStraddle_LHS, StraddlebyThree):
    pass

class RollingStraddle_LHS_TG_STD3_2DTE(RollingStraddle_LHS, TG_STD3_2DTE):
    pass
