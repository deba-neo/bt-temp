from strategies.strategy import Strategy
from Greeks import Greeks
from datetime import datetime
import math
from strategies import policy


class NoDecay(Strategy):
    def hedge(self, spot) -> None:
        return super().hedge(spot)
    
    def hedge_point(self, spot) -> bool:
        return super().hedge_point(spot)
    
    def position_management(self, spot) -> None:

        t = datetime.strptime(str(self.context.MD.current_time), "%Y-%m-%d %H:%M:%S")
        entry_time = list(map(int, self.context.strategy_args["entry_position_time"].split(":")))
        close_time = list(map(int, self.context.strategy_args["close_position_time"].split(":")))

        
        choke_points = self.context.strategy_args["choke_points"]
        for i, choke_point in enumerate(choke_points):
            entry_time = list(map(int, choke_point.split(":")))
            if t == t.replace(hour=entry_time[0], minute=entry_time[1], second=entry_time[2], microsecond=0):
                self.context.strategy_args["choke_detected"] = True
                self.context.strategy_args["choke_IV"] = self.context.strategy_args["choke_IVs"][i]
            else:
                self.context.strategy_args["choke_detected"] = False

        
        
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
            not self.context.strategy_args["trade_taken"]
        ):
            if self.context.strategy_args["choke_detected"]:
                self.build_position(spot)
            else:
                return
        else:
            curr_pnl = self.context.PnL()

            if (
                curr_pnl < self.context.strategy_args["stop_loss_PNL"] or
                curr_pnl > self.context.strategy_args["profit_book_PNL"]
            ):
                self.square_off_position(spot)
                self.context.strategy_args["trade_taken"] = False


        
        
        return super().position_management(spot)
    
    def check_for_choke(self,spot):
        self.context.strategy_args["choke_detected"] = True
        pass
    
    def build_position(self, spot):
        call_option = int(math.ceil(spot / float(self.context.movement))) * self.context.movement  
        put_option = int(math.floor(spot / float(self.context.movement))) * self.context.movement 

        quantity_calls = self.context.strategy_args["demand"]
        quantity_puts = self.context.strategy_args["demand"]

        options_list = [f'{put_option}PE', f'{call_option}CE']
        is_sell_list = [False, False]
        quantity_list = [quantity_puts, quantity_calls]

        self.context.make_orders(options_list, is_sell_list, quantity_list)

        self.context.strategy_args["trade_taken"] = True

        iv = self.context.straddle_IV(spot)

        gcalc = Greeks()

        ttm = self.context.timeToMaturity()
        eod_dte = ttm - self.context.timeinDay()
        
        iv_init = self.context.strategy_args["choke_IV"]
        
        curr_call_price = gcalc.Call_BS_Value(spot, call_option, self.context.rfr, ttm, iv_init)
        curr_put_price = gcalc.Put_BS_Value(spot, put_option, self.context.rfr, ttm, iv_init)
        
        time_45_mins = 0.12
        start_call_price = gcalc.Call_BS_Value(spot, call_option, self.context.rfr, ttm+time_45_mins, iv_init)
        start_put_price = gcalc.Put_BS_Value(spot, put_option, self.context.rfr, ttm+time_45_mins, iv_init)

        print("Start STD", start_call_price + start_put_price)
        print("End STD", curr_call_price + curr_put_price)
        print("QTY Calls: ", quantity_calls)

        SL = (start_call_price-curr_call_price)*quantity_calls + (start_put_price-curr_put_price)*quantity_puts

        SL = SL*2

        self.context.strategy_args["stop_loss_PNL"] = -SL
        self.context.strategy_args["profit_book_PNL"] = 2.5*SL

        pass


    def get_stop_loss(self, spot):
        pass
    
    def square_off_position(self, spot):
        self.context.policy_variables["size_target"] = 0
        self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["destruction_lots_per_cycle"]
        self.context.set_policy(policy.Destructor())
        pass
    
    def new_position_handler(self, spot) -> None:
        self.context.strategy_args["trade_taken"] = False
        return super().new_position_handler(spot)
    
    def existing_position_handler(self, spot):
        return super().existing_position_handler(spot)