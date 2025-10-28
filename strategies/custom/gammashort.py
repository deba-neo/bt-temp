from strategies.strategy import (
    Strategy,
    ThetaGamma,
    StraddlebyThree,
    TG_STD3_2DTE_HedgebyBuying,
)

from Greeks import Greeks
import math
from strategies import policy
from datetime import datetime

class GammaShort_Hedged(TG_STD3_2DTE_HedgebyBuying):
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
        
        if (
            t
            > t.replace(hour=entry_time[0], minute=entry_time[1], second=entry_time[2], microsecond=0)
            and not self.context.strategy_args["position_created"]
            ):
            strikes_away = 1
            call_option = int(math.ceil(spot / float(self.context.movement))) * self.context.movement + self.context.movement*(strikes_away-1) 
            put_option = int(math.floor(spot / float(self.context.movement))) * self.context.movement - self.context.movement*(strikes_away-1)

            gcalc = Greeks()

            prices = self.context.get_current_price([
                f'{call_option}CE',
                f'{put_option}PE',
            ])

            ttm = self.context.timeToMaturity()

            IV = gcalc.Call_IV(spot, call_option, self.context.rfr, ttm, prices[0])
            delta_call = gcalc.delta('CE', spot, call_option, ttm, IV, self.context.rfr)
            
            IV = gcalc.Put_IV(spot, put_option, self.context.rfr, ttm, prices[1])
            delta_put = gcalc.delta('PE', spot, put_option, ttm, IV, self.context.rfr)

            ratio = abs(delta_put/delta_call)

            quantity_calls = self.context.strategy_args["demand"]
            quantity_puts = quantity_calls/ratio

            options_list = [f'{put_option}PE', f'{call_option}CE']
            is_sell_list = [True, True]
            quantity_list = [quantity_puts, quantity_calls]

            self.context.make_orders(options_list, is_sell_list, quantity_list)

            self.context.strategy_args["position_created"] = True
            pass
        
    def new_position_handler(self, spot) -> None:
        self.context.strategy_args["position_created"] = False
        # if self.context.timeToMaturity() > 1:
        #     self.context.strategy_args["demand"] = 0
        pass
    