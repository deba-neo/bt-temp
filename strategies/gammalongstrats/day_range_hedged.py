from strategies.strategy import (
    Strategy,
    ThetaGamma,
    StraddlebyThree,
    TG_STD3_2DTE_HedgebyBuying,
)

from strategies.gammalongstrats.day_range import GammaLong_ATR

from Greeks import Greeks
import math
from strategies import policy
from datetime import datetime

class GammaLong_ATR_Hedged(GammaLong_ATR):
    def position_management(self, spot) -> None:
        t = datetime.strptime(str(self.context.MD.current_time), "%Y-%m-%d %H:%M:%S")
        entry_time = list(map(int, self.context.strategy_args["entry_position_time"].split(":")))
        close_time = list(map(int, self.context.strategy_args["close_position_time"].split(":")))

        
        if (
            t
            > t.replace(hour=close_time[0], minute=close_time[1], second=close_time[2], microsecond=0)
            or \
                self.context.strategy_args["close_position"]
            or self.context.total_pnl < self.context.strategy_args["stop_loss"]
            ):
            self.context.policy_variables["size_target"] = 0
            self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["destruction_lots_per_cycle"]
            self.context.set_policy(policy.Destructor())
            return
        
        self.check_trade_signal(spot)
        self.building_position(spot)
        self.set_exit_conditions(spot)

        self.roll_position(spot)
        
        if self.context.strategy_args["position_created"] and self.exit_condition(spot):
            self.context.policy_variables["size_target"] = 0
            self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["destruction_lots_per_cycle"]
            self.context.set_policy(policy.Destructor())
            pass

    def roll_position(self, spot):
        
        current_options = []
        current_option_quantities = []

        for key, value in self.context.portfolio.items():
            if value != 0:
                current_options.append(key)
                current_option_quantities.append(value)


        if len(current_options) != 1:
            return
            


        if current_options[0][-2:] == "CE":
            distance = int(current_options[0][:-2]) - spot
        else:
            distance = spot - int(current_options[0][:-2])

        straddle_price, atm_option = self.context.atm_straddle_price(spot)

        if distance > straddle_price/2:
            return

        call_option = int(math.ceil((spot + straddle_price)/ float(self.context.movement))) * self.context.movement 
        put_option = int(math.floor((spot - straddle_price)/ float(self.context.movement))) * self.context.movement

        if current_options[0][-2:] == "CE":
            options_list = [f'{call_option}CE']
            is_sell_list = [False]
            quantity_list = [self.context.strategy_args["demand"]]
        else:
            options_list = [f'{put_option}PE']
            is_sell_list = [False]
            quantity_list = [self.context.strategy_args["demand"]]

        options_list.append(current_options[0])
        is_sell_list.append(True)
        quantity_list.append(current_option_quantities[0])


        self.context.make_orders(options_list, is_sell_list, quantity_list)