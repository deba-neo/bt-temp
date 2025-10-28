from XTConnect.APIWrapper import Interaction
from BaseStraddle import BaseStraddle
import math
from datetime import datetime
from Greeks import Greeks

"""
#########################
VERSION 1 DELTA/GAMMA HEADGING

Hedges by:
- Call Bull Spread when Delta short
- Call Bear Spread when Delta long


Points away from Delta Neutrality: Delta/Gamma
Hedge Point: 30

#########################################################################
"""


class DeltaGammav1(BaseStraddle):
    def __init__(
        self,
        index: str,
        expiry: str,
        rfr: float,
        instruments: list,
        Order: Interaction,
        demand: int,
    ) -> None:
        super().__init__(index, expiry, rfr, instruments, Order, demand)

    def adjust(self, spot, strategy_args):
        if self.position == None:
            position = int(round(spot / float(self.movement))) * self.movement
            self.create_position(position, spot)
            return self.position

        # potential automatic background calculation
        # next update - self.greeks attribute
        greeks = self.get_portfolio_greeks(spot)
        self.pretty_print(greeks)

        points_out = abs(greeks["portfolio_delta"] / greeks["portfolio_gamma"])
        print(f"Points Out: {points_out}", flush=True)
        print(f"Hedge Point: {30}", flush=True)

        if points_out > 30:
            if greeks["portfolio_delta"] > 0:
                self.call_bear_spread(spot, greeks["portfolio_delta"])
            else:
                self.call_bull_spread(spot, greeks["portfolio_delta"])

        print(self.portfolio)
        return self.position


"""
#######################################################################
VERSION 2 DELTA/GAMMA HEADGING

Hedges by:
- Positive Delta (Long):
    - High IV: Sells Bear Spread []
    - Low IV: Buys Bear Spread
- Negative Delta (Short):
    - High IV: Sells Bull Spread
    - Low IV: Buys Bull Spread


Points away from Delta Neutrality: Delta/Gamma
Hedge Point: Root(Theta/2*Gamma)


Latest Features Added:
    - Auto Descaling of position beyond a certain time based on strategy configurations
    - Picking up existing positions and hedging those options
    *- Auto storage of current portfolio details

#########################################################################
"""


class DeltaGammav2(BaseStraddle):
    def __init__(
        self,
        index: str,
        expiry: str,
        adjustment: int,
        rfr: float,
        instruments: list,
        Order: Interaction,
        strategy_args: dict,
    ) -> None:
        super().__init__(
            index, expiry, adjustment, rfr, instruments, Order, strategy_args
        )

    def adjust(self, spot, strategy_args):
        self.strategy_args = strategy_args

        if self.position == None:
            self.new_position_handler(spot, strategy_args)
            self.constructing = True
            self._POSITION_LIMIT_ = None
            print(self.portfolio)
            return self.position

        # potential automatic background calculation
        # next update - self.greeks attribute
        greeks, points_out, hedge_point = self.boilerplate(spot)
        self.greeks = greeks

        print(f"Points Out: {points_out  :.2f}", flush=True)
        print(f"Hedge Point: {hedge_point  :.2f}", flush=True)

        # Hedging
        if points_out > hedge_point:
            self.hedge(spot)

        # Close position beyond 3:15 PM
        close_time = list(map(int, self.strategy_args["close_position_time"].split(":")))
        if (
            datetime.now()
            > datetime.now().replace(hour=close_time[0], minute=close_time[1], second=close_time[2], microsecond=0)
            or \
                self.strategy_args["close_position"]
            or (not self.constructing and self.full_portfolio_size() > self._POSITION_LIMIT_)
        ):
            self.constructing = False
            self.change_position_size(
                strategy_args["construction_lots_per_cycle"], decrease=True
            )

        # Constructing Portfoio
        if self.constructing:
            if self.strategy_args["target"] == "theta":
                att = greeks["portfolio_theta"]
                target = self.strategy_args["theta_target"]

            elif self.strategy_args["target"] == "size":
                att = self.full_portfolio_size()
                target = self.strategy_args["size_target"]

            elif self.strategy_args["target"] == "vega":
                att = abs(greeks["portfolio_vega"])
                target = abs(self.strategy_args["vega_target"])

            # target theta
            if att > target:
                self.constructing = False
                self._POSITION_LIMIT_ = (
                    self.full_portfolio_size() * self.strategy_args["quantity_limit"]
                )
            
            else:
                print("Constructing Portfolio")
                self.new_position_handler(spot, strategy_args)
                # self.change_position_size(
                #     strategy_args["construction_lots_per_cycle"], decrease=False
                # )

        print(self.portfolio)
        return self.position

    def new_position_handler(self, spot, strategy_args):
        if strategy_args["position_exists"] == True:
            return self.existing_position_handler(spot, strategy_args)
        
        
        position = int(round(spot / float(self.movement))) * self.movement

        self.wings = None
        self.strategy_args = strategy_args

        straddle_price, _ = self.atm_straddle_price(spot)
        self.wings = (
            int(round(strategy_args["wings"] * straddle_price / float(self.movement)))
            * self.movement
        )

        self.create_position(position, spot)
        return

    def existing_position_handler(self, spot, strategy_args):
        existing_pf: dict[str, int] = strategy_args["existing_pf"]
        existing_pf_value: int = strategy_args["existing_pf_value"]

        self.portfolio = existing_pf

        # creating our order cache for quick accesss
        instruments = {}
        for key, value in existing_pf.items():
            instruments[key] = self._get_option(key)
            pass 
        
        self.orders = instruments
        
        self.net_value = existing_pf_value
        self.PnL()

        self.position = 0
        self._POSITION_LIMIT_ = self.full_portfolio_size()*strategy_args["quantity_limit"]

        return

    def boilerplate(self, spot):
        strategy_args = self.strategy_args
        ref_IV = strategy_args["refIV"]

        if strategy_args["IVCalc"] == "Reference":
            greeks = self.get_portfolio_greeks(spot, refIV=ref_IV)
        else:
            greeks = self.get_portfolio_greeks(spot)
        self.pretty_print(greeks)

        target_theta = greeks["portfolio_theta"]
        
        try:
            points_out = abs(greeks["portfolio_delta"] / greeks["portfolio_gamma"])
            hedge_point = math.sqrt(
                abs(target_theta / (2 * greeks["portfolio_gamma"]))
            )
        except ZeroDivisionError as e:
            print(e)
            points_out = self.zero_gamma_handler(greeks["portfolio_delta"])
            hedge_point = self.zero_gamma_handler(greeks["portfolio_theta"]/2)

        return greeks, points_out, hedge_point

    def hedge(self, spot, hedge_amount=None):
        strategy_args = self.strategy_args
        ref_IV = strategy_args["refIV"]
        hedge_amount = (
            strategy_args["hedge_amount"] if hedge_amount == None else hedge_amount
        )

        straddle_IV = self.straddle_IV(spot)

        # print(f"Straddle IV: {straddle_IV}")

        if self.greeks["portfolio_delta"] > 0:
            if straddle_IV > ref_IV:
                self.call_bear_spread(
                    spot, self.greeks["portfolio_delta"], hedge_amount, ref_IV
                )
            else:
                self.put_bear_spread(
                    spot, self.greeks["portfolio_delta"], hedge_amount, ref_IV
                )
        else:
            if straddle_IV > ref_IV:
                self.put_bull_spread(
                    spot, self.greeks["portfolio_delta"], hedge_amount, ref_IV
                )
            else:
                self.call_bull_spread(
                    spot, self.greeks["portfolio_delta"], hedge_amount, ref_IV
                )

    def full_portfolio_size(self):
        total = 0
        for key in self.portfolio:
            total+= abs(self.portfolio[key])
        return total
    
    def zero_gamma_handler(self, numerator):
        return numerator


"""
#######################################################################
VERSION 3 DELTA/GAMMA HEADGING
[Inherited from Version 2]

Changes made:
Hedge Point: Straddle by 3 

#########################################################################
"""


class DeltaGammav3(DeltaGammav2):
    def __init__(
        self,
        index: str,
        expiry: str,
        adjustment: int,
        rfr: float,
        instruments: list,
        Order: Interaction,
        strategy_args: dict,
    ) -> None:
        super().__init__(
            index, expiry, adjustment, rfr, instruments, Order, strategy_args
        )

    def boilerplate(self, spot):
        strategy_args = self.strategy_args
        ref_IV = strategy_args["refIV"]

        if strategy_args["IVCalc"] == "Reference":
            greeks = self.get_portfolio_greeks(spot, refIV=ref_IV)
        else:
            greeks = self.get_portfolio_greeks(spot)
        self.pretty_print(greeks)

        straddle_price, _ = self.atm_straddle_price(spot)

        try:
            points_out = abs(greeks["portfolio_delta"] / greeks["portfolio_gamma"])
            hedge_point = straddle_price / 3
        except ZeroDivisionError as e:
            print(e)
            points_out = self.zero_gamma_handler(greeks["portfolio_delta"])
            hedge_point = self.zero_gamma_handler(greeks["portfolio_theta"]/2)
        
        return greeks, points_out, hedge_point


"""
#######################################################################
VERSION 4 DELTA/GAMMA HEADGING
[Inherited from Version 2]

Aggressive Hedging
#########################################################################
"""


class DeltaGammav4(DeltaGammav2):
    def __init__(
        self,
        index: str,
        expiry: str,
        adjustment: int,
        rfr: float,
        instruments: list,
        Order: Interaction,
        strategy_args: dict,
    ) -> None:
        super().__init__(
            index, expiry, adjustment, rfr, instruments, Order, strategy_args
        )
    
    def boilerplate(self, spot):
        strategy_args = self.strategy_args
        ref_IV = strategy_args["refIV"]

        if strategy_args["IVCalc"] == "Reference":
            greeks = self.get_portfolio_greeks(spot, refIV=ref_IV)
        else:
            greeks = self.get_portfolio_greeks(spot)
        self.pretty_print(greeks)

        straddle_price, _ = self.atm_straddle_price(spot)

        try:
            points_out = abs(greeks["portfolio_delta"] / greeks["portfolio_gamma"])
            hedge_point = straddle_price / 6
        except ZeroDivisionError as e:
            print(e)
            points_out = self.zero_gamma_handler(greeks["portfolio_delta"])
            hedge_point = self.zero_gamma_handler(greeks["portfolio_theta"]/2)
        
        return greeks, points_out, hedge_point

"""
#######################################################################
VERSION 5 DELTA/GAMMA HEADGING
[Inherited from Version 2]

Rolling Theta Retention

#########################################################################
"""

class RollingThetaRetention(DeltaGammav3):
    def __init__(
        self,
        index: str,
        expiry: str,
        adjustment: int,
        rfr: float,
        instruments: list,
        Order: Interaction,
        strategy_args: dict,
    ) -> None:
        super().__init__(
            index, expiry, adjustment, rfr, instruments, Order, strategy_args
        )

    def adjust(self, spot, strategy_args):
        return super().adjust(spot, strategy_args)

    def new_position_handler(self, spot, strategy_args):
        position = int(math.ceil(spot / float(self.movement))) * self.movement
        gcalc = Greeks()

        spread_instruments = [self._get_call(strike=position), self._get_put(strike=position)]
        prices = self.MD._get_price(spread_instruments)

        ttm = self.timeToMaturity()
        IV = gcalc.Call_IV(spot, position, self.rfr, ttm, prices[0])

        delta_call = gcalc.delta('CE', spot, position, ttm, IV, self.rfr)
        delta_put = gcalc.delta('PE', spot, position, ttm, IV, self.rfr)

        ratio = abs(delta_put/delta_call)

        quantity_calls = self.strategy_args["demand"]
        quantity_puts = quantity_calls/ratio

        options = [f"{position}CE", f"{position}PE"]
        sell = [True, True]
        quantities = [quantity_calls, quantity_puts]

        self.make_orders(options, sell, quantities)
        
        self.position = position
        return
    
    def hedge(self, spot, hedge_amount=None):
        lots = 0
        for key, quantity in self.portfolio.items():
            lots = max(lots, abs(quantity)//self.lot_size + 1)
        
        self.change_position_size(maximum_number_of_lots_per_cycle=lots, decrease=True)
        self.new_position_handler(spot, None)
        
        return