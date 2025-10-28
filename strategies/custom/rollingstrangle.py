from strategies.strategy import (
    Strategy,
    StraddlebyThree,
    ThetaGamma,
    TG_STD3_2DTE,
    ThetaGamma_HedgebyForwards,
)
from strategies import policy
from Greeks import Greeks
import math
from datetime import datetime

class RollingStrangle(ThetaGamma):
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
        new_position = int(math.ceil(spot / float(self.context.movement))) * self.context.movement
        for key, quantity in self.context.portfolio.items():
            if quantity != 0:
                current_strike = int(key[:-2])
                break
        
        if new_position == current_strike:
            return True
        else:
            return False

    def hedge_with_puts(self, spot):
        position = int(math.ceil(spot / float(self.context.movement))) * self.context.movement

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
            or self.context.total_pnl > self.context.strategy_args.get("profit_book", math.inf)
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
        call_position, put_position = self.context.find_delta_strike(spot, 0.4)
        
        gcalc = Greeks()

        # prices = self.context.get_current_price([
        #     f'{call_position}CE',
        #     f'{put_position}PE',
        # ])

        # print(f"Call Price: {prices[0]}", flush=True)
        # print(f"Put Price: {prices[1]}", flush=True)

        # ttm = self.context.timeToMaturity()
        # if self.context.strategy_args["IVCalc"] == "Reference":
        #     IV = self.context.strategy_args["refIV"]
        # else:
        #     IV = gcalc.Call_IV(spot, position, self.context.rfr, ttm, prices[0])

        # delta_call = gcalc.delta('CE', spot, position, ttm, IV, self.context.rfr)
        # delta_put = gcalc.delta('PE', spot, position, ttm, IV, self.context.rfr)

        # ratio = abs(delta_put/delta_call)

        # quantity_calls = self.context.strategy_args["demand"]
        # quantity_puts = quantity_calls/ratio

        # # lower hedge when no strike change
        # no_change_hedge_amt = 1/3
        # if hedge and self.no_strike_change(spot):
        #     if quantity_puts < -self.context.portfolio[f"{position}PE"]:
        #         # 1/3rd the distance between current and final number of puts
        #         quantity_puts = quantity_puts + (-self.context.portfolio[f"{position}PE"]-quantity_puts)*(1-no_change_hedge_amt)
        #     pass

        # quantity_puts = (int(quantity_puts/self.context.lot_size))*self.context.lot_size

        # options = [f"{position}CE", f"{position}PE"]
        # sell = [True, True]
        # quantities = [quantity_calls, quantity_puts]
        # self.context.make_orders(options, sell, quantities)

        quantity = self.context.strategy_args["demand"]

        self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["construction_lots_per_cycle"]
        self.context.policy_variables["to_create_portfolio"] = {
            f"{call_position}CE" : quantity,
            f"{put_position}PE" : quantity,
        }

        # clears current portfolio
        for key, value in self.context.portfolio.items():
            self.context.policy_variables["to_create_portfolio"][key] = self.context.policy_variables["to_create_portfolio"].get(key, 0) + value

        self.context.set_policy(policy.CustomPortfolioBuilder())
        pass

    def existing_position_handler(self, spot):
        self.new_position_handler(spot)
        pass


class RollingStrangle_StraddlebyThree(RollingStrangle, StraddlebyThree):
    pass

class RollingStrangle_TG_STD3_2DTE(RollingStrangle, TG_STD3_2DTE):
    pass

class RollingStrangle_FWD_TG_STD3_2DTE(RollingStrangle, TG_STD3_2DTE):
    def hedge(self, spot):
        return ThetaGamma_HedgebyForwards.hedge(self, spot)
    pass