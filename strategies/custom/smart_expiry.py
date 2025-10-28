from strategies.strategy import StraddlebyThree_HedgebyBuying
from strategies.custom.smartstraddle import SmartStraddle, SmartStraddle_HedgebyBuying
from Greeks import Greeks
import math
from strategies import policy
import datetime


class SmartStraddle_Expiry(SmartStraddle):
    def find_edge(self, spot, current_straddle_price):
        build, expected_close, time_left = self.expected_close_and_time_left(spot)

        if not build:
            projected_gain = -1
            self.context.strategy_args["close_position"] = True
            return projected_gain

        
        projected_gain = current_straddle_price - expected_close
        projected_gain /= time_left
        
        return projected_gain
    
    def expected_close_and_time_left(self, spot):
        nw = datetime.datetime.strptime(str(self.context.MD.current_time), "%Y-%m-%d %H:%M:%S")

        target_time1 = nw.replace(hour=11, minute=0, second=0, microsecond=0)
        target_time2 = nw.replace(hour=13, minute=0, second=0, microsecond=0)
        target_time3 = nw.replace(hour=14, minute=15, second=0, microsecond=0)
        target_time4 = nw.replace(hour=15, minute=0, second=0, microsecond=0)
        target_time5 = nw.replace(hour=15, minute=15, second=0, microsecond=0)

        switch_time1 = nw.replace(hour=10, minute=30, second=0, microsecond=0)
        switch_time2 = nw.replace(hour=12, minute=30, second=0, microsecond=0)
        switch_time3 = nw.replace(hour=13, minute=55, second=0, microsecond=0)
        switch_time4 = nw.replace(hour=14, minute=40, second=0, microsecond=0)
        switch_time5 = nw.replace(hour=15, minute=0, second=0, microsecond=0)

        if nw < switch_time1:
            req_time = target_time1
            pass
        elif nw < switch_time2:
            req_time = target_time2
            pass
        elif nw < switch_time3:
            req_time = target_time3
            pass
        elif nw < switch_time4:
            req_time = target_time4
            pass
        elif nw < switch_time5:
            req_time = target_time5
            pass
        else:
            return False, None, None

        time_left = (
            datetime.datetime.combine(datetime.date.min, req_time.time())
            - datetime.datetime.combine(datetime.date.min, nw.time())
        ).total_seconds() / 22500

        expected_closing_IV = self.context.strategy_args["expected_closing_IV"]
        tte = self.context.timeToMaturity()
        target_time_tte = tte - time_left
        expected_close = self.context.find_straddle_price(spot, target_time_tte, expected_closing_IV)
        print(f"Target Time: {req_time.time().isoformat(timespec='seconds')}")
        print(f"Expected Straddle Close: {expected_close  :.2f}")
        return True, expected_close, time_left
    
    def new_position_handler(self, spot) -> None:
        super().new_position_handler(spot)

        tte = self.context.timeToMaturity()
        if tte > 1:
            self.context.set_strategy(SmartStraddle())


class SmartStraddle_Expiry_HedgebyBuying(SmartStraddle_Expiry, StraddlebyThree_HedgebyBuying):
    def new_position_handler(self, spot) -> None:
        super().new_position_handler(spot)

        tte = self.context.timeToMaturity()
        if tte > 1:
            self.context.set_strategy(SmartStraddle_HedgebyBuying())
