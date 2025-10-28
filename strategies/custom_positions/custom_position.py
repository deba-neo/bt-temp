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

class CustomPosition(ThetaGamma):
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
        print(f"CATR: {self.context.high - self.context.low}")
        print(f"Max ATR: {self.context.strategy_args['expected_ATR']*0.8}")

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
        
        current_IV = self.context.straddle_IV(spot)

        straddle_price, atm_option = self.context.atm_straddle_price(spot)
        
        # expected_ATR = math.sqrt(2/math.pi)

        expected_ATR = (current_IV/math.sqrt(365))*spot

        ttm = self.context.timeToMaturity()

        expected_ATR = (2*straddle_price)/math.sqrt(ttm)
        
        self.context.strategy_args["morning_IV"] = current_IV
        self.context.strategy_args["initial_spot"] = spot
        self.context.strategy_args["expected_ATR"] = expected_ATR

        self.create_new_position(spot, hedge=False)
        pass    
    
    def create_new_position(self, spot, hedge = False) -> None:
        

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
        strike = int(math.ceil(spot / float(self.context.movement))) * self.context.movement




        return strike

