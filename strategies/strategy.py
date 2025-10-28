from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # Only imports the below statements during type checking
    from BaseStraddle import BaseStraddle
from abc import ABC, abstractmethod
from strategies import policy
import math

from datetime import datetime

from Greeks import Greeks

class Strategy(ABC):
    """
    Common Interface for all strategies
    Strategies inherit from this class
    Base Straddle constitutes a strategy
    through this interface
    """

    @property
    def context(self) -> BaseStraddle:
        return self._context

    @context.setter
    def context(self, context: BaseStraddle) -> None:
        self._context = context

    @abstractmethod
    def position_management(self, spot) -> None:
        pass

    @abstractmethod
    def hedge(self, spot) -> None:
        pass

    @abstractmethod
    def hedge_point(self, spot) -> bool:
        pass

    @abstractmethod
    def new_position_handler(self, spot) -> None:
        pass

    @abstractmethod
    def existing_position_handler(self, spot):
        pass


class ThetaGamma(Strategy):
    def new_position_handler(self, spot) -> None:
        if self.context.strategy_args["target"] == "size":
            self.context.policy_variables["size_target"] = self.context.strategy_args[
                "size_target"
            ]
            self.context.set_policy(policy.ATMBuiler())
        elif self.context.strategy_args["target"] == "theta":
            self.context.policy_variables["theta_target"] = self.context.strategy_args[
                "theta_target"
            ]
            self.context.set_policy(policy.ATMThetaBuiler())
        elif self.context.strategy_args["target"] == "vega":
            self.context.policy_variables["vega_target"] = self.context.strategy_args[
                "vega_target"
            ]
            self.context.set_policy(policy.ATMVegaBuiler())
        
        self.context.strategy_args["DataStorage"] = []
        pass

    def existing_position_handler(self, spot):
        self._POSITION_LIMIT_ = (
            self.context.full_portfolio_size()
            * self.context.strategy_args["quantity_limit"]
        )
        # self.new_position_handler(spot)

        
        pass

    def position_management(self, spot) -> None:
        # if self.context.full_portfolio_size() > self.context.strategy_args["position_size_limit"]:
        #     self.context.policy_variables["size_target"] = self.context.strategy_args[
        #         "position_size_limit"
        #     ]
        #     self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["destruction_lots_per_cycle"]
        #     self.context.set_policy(policy.Destructor())
        
        close_time = list(map(int, self.context.strategy_args["close_position_time"].split(":")))
        t = datetime.strptime(str(self.context.MD.current_time), "%Y-%m-%d %H:%M:%S")
        if (
            t > t.replace(hour=close_time[0], minute=close_time[1], second=close_time[2], microsecond=0) and \
            self.context.full_portfolio_size() > 0 and self.context.timeToMaturity() > 1
        ):
            self.hedge(spot)
        
        # self.context.strategy_args["DataStorage"].append(self.context.total_pnl)
        
        if (
            t
            > t.replace(hour=close_time[0], minute=close_time[1], second=close_time[2], microsecond=0)
            or \
                self.context.strategy_args["close_position"]
            or self.context.hit_stop_loss):
            self.context.policy_variables["size_target"] = 0
            self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["destruction_lots_per_cycle"]
            self.context.set_policy(policy.Destructor())
        
        data = []

        t = self.context.MD.current_time
        data.append(str(t))

        spot = spot
        data.append(spot)

        pnl = self.context.PnL()
        data.append(pnl)

        ttm = self.context.timeToMaturity()
        data.append(ttm)

        atm_IV = self.context.straddle_IV(spot)
        data.append(atm_IV)

        atm_straddle_price, atm_strike = self.context.atm_straddle_price(spot)
        data.append(atm_straddle_price)
        data.append(atm_strike)

        strike_gap = self.context.movement
        strike_list = [*range(atm_strike-10*strike_gap, atm_strike+11*strike_gap, strike_gap)]

        
        calls = [f"{strike}CE" for strike in strike_list]
        puts = [f"{strike}PE" for strike in strike_list]

        call_oi = self.context.get_OI(calls)
        put_oi = self.context.get_OI(puts)
        data.append(sum(call_oi))
        data.append(sum(put_oi))

        call_vol = self.context.get_Volumes(calls)
        put_vol = self.context.get_Volumes(puts)
        data.append(sum(call_vol))
        data.append(sum(put_vol))
        
        # options_list = [f"{strike}CE" for strike in strike_list] + [f"{strike}PE" for strike in strike_list]

        # OIs = self.context.get_OI(options_list)
        # for oi in OIs:
        #     data.append(oi)
        # Volumes = self.context.get_Volumes(options_list)
        # for vol in Volumes:
        #     data.append(vol)


        self.context.strategy_args["DataStorage"].append(data)

        pass

    def hedge_point(self, spot) -> bool:
        greeks = self.context.greeks

        try:
            points_out = abs(greeks["portfolio_delta"] / greeks["portfolio_gamma"])
            hedge_point = math.sqrt(
                abs(greeks["portfolio_theta"] / (2 * greeks["portfolio_gamma"]))
            )
            hedge_point *= self.context.strategy_args["hedge_point_multiplier"]
        except ZeroDivisionError as e:
            print(e)
            points_out = self.zero_gamma_handler(greeks["portfolio_delta"])
            hedge_point = self.zero_gamma_handler(greeks["portfolio_theta"] / 2)

        print(f"Points Out: {points_out  :.2f}", flush=True)
        print(f"Hedge Point: {hedge_point  :.2f}", flush=True)
        return points_out > hedge_point

    def zero_gamma_handler(self, numerator):
        return numerator

    def hedge(self, spot) -> None:
        strategy_args = self.context.strategy_args

        ref_IV = strategy_args["refIV"]
        hedge_amount = strategy_args["hedge_amount"]

        straddle_IV = self.context.straddle_IV(spot)

        # print(f"Straddle IV: {straddle_IV}")

        if self.context.greeks["portfolio_delta"] > 0:
            if straddle_IV > ref_IV:
                self.context.call_bear_spread(
                    spot, self.context.greeks["portfolio_delta"], hedge_amount, ref_IV
                )
            else:
                self.context.put_bear_spread(
                    spot, self.context.greeks["portfolio_delta"], hedge_amount, ref_IV
                )
        else:
            if straddle_IV > ref_IV:
                self.context.put_bull_spread(
                    spot, self.context.greeks["portfolio_delta"], hedge_amount, ref_IV
                )
            else:
                self.context.call_bull_spread(
                    spot, self.context.greeks["portfolio_delta"], hedge_amount, ref_IV
                )

    pass


class StraddlebyThree(ThetaGamma):
    def hedge_point(self, spot) -> bool:
        greeks = self.context.greeks
        straddle_price, _ = self.context.atm_straddle_price(spot)

        try:
            points_out = abs(greeks["portfolio_delta"] / greeks["portfolio_gamma"])
            hedge_point = straddle_price / 3
            hedge_point *= self.context.strategy_args["hedge_point_multiplier"]
        except ZeroDivisionError as e:
            print(e)
            points_out = self.zero_gamma_handler(greeks["portfolio_delta"])
            hedge_point = self.zero_gamma_handler(greeks["portfolio_theta"] / 2)

        print(f"Points Out: {points_out  :.2f}", flush=True)
        print(f"Hedge Point: {hedge_point  :.2f}", flush=True)
        return points_out > hedge_point

    pass

class ThetaGamma_DeltaWings(ThetaGamma):
    def new_position_handler(self, spot) -> None:
        size = self.context.demand
        size = (size//self.context.lot_size)*self.context.lot_size

        straddle_price, atm_option = self.context.atm_straddle_price(spot)
        print(straddle_price)
        
        self.context.naked_straddle(atm_option, spot, size)        
        
        wing_del = self.context.strategy_args["wing_delta"]

        call_strike, put_strike = self.context.find_delta_strike(spot, wing_del)

        options_list = [f'{put_strike}PE', f'{call_strike}CE']
        is_sell_list = [False, False]
        quantity_list = [size]*2

        self.context.make_orders(options_list, is_sell_list, quantity_list)
        pass

class TG_STD3_2DTE(ThetaGamma):
    def hedge_point(self, spot) -> bool:
        tte = self.context.timeToMaturity()
        if tte > 2:
            return ThetaGamma.hedge_point(self, spot)
        else:
            return StraddlebyThree.hedge_point(self, spot)



class ThetaGamma_HedgebyBuying(ThetaGamma):
    def hedge(self, spot) -> None:
        strategy_args = self.context.strategy_args
        ref_IV = strategy_args["refIV"]
        hedge_amount = strategy_args["hedge_amount"]

        if self.context.greeks["portfolio_delta"] > 0:
            self.context.hedge_by_buying_puts(
                spot, self.context.greeks["portfolio_delta"]*hedge_amount, ref_IV
            )
        else:
            self.context.hedge_by_buying_calls(
                spot, self.context.greeks["portfolio_delta"]*hedge_amount, ref_IV
            )

class StraddlebyThree_HedgebyBuying(StraddlebyThree, ThetaGamma_HedgebyBuying):
    pass

class TG_STD3_2DTE_HedgebyBuying(TG_STD3_2DTE, ThetaGamma_HedgebyBuying):
    pass


class ThetaGamma_HedgebyForwards(ThetaGamma):
    def hedge(self, spot) -> None:
        std_p, atm_option = self.context.atm_straddle_price(spot)
        
        for item in self.context.portfolio:
            if self.context.portfolio[item] != 0:
                strike = int(item[:-2])
        
        # print(strike,atm_option, std_p)
        # if std_p*2 < (strike-atm_option):
        #     # roll
        #     quantity = self.context.strategy_args["demand"]

        #     self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["construction_lots_per_cycle"]
        #     self.context.policy_variables["to_create_portfolio"] = {
        #         f"{atm_option}CE" : quantity,
        #         f"{atm_option}PE" : quantity,
        #     }

        #     for key, value in self.context.portfolio.items():
        #         self.context.policy_variables["to_create_portfolio"][key] = self.context.policy_variables["to_create_portfolio"].get(key, 0) + value

        #     self.context.set_policy(policy.CustomPortfolioBuilder())

        #     return


        strategy_args = self.context.strategy_args
        ref_IV = strategy_args["refIV"]
        hedge_amount = strategy_args["hedge_amount"]

        self.context.hedge_by_atm_forwards(
            spot, self.context.greeks["portfolio_delta"]*hedge_amount, ref_IV
        )

class StraddlebyThree_HedgebyForwards(StraddlebyThree, ThetaGamma_HedgebyForwards):
    pass

class TG_STD3_2DTE_HedgebyForwards(TG_STD3_2DTE, ThetaGamma_HedgebyForwards):
    pass


class TG_STD3_2DTE_Forwards_CutWings(TG_STD3_2DTE_HedgebyForwards):
    def existing_position_handler(self, spot) -> None:
        # self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["construction_lots_per_cycle"]

        # self.context.policy_variables["to_create_portfolio"] = {}

        options = []
        sell = []
        quantities = []
        for key, value in self.context.portfolio.items():
            if value > 0:
                options.append(key)
                sell.append(True)
                quantities.append(value)
                # self.context.policy_variables["to_create_portfolio"][key] = value

        # self.context.set_policy(policy.CustomPortfolioBuilder())
        self.context.make_orders(options, sell, quantities)
    pass

class DataStorage(Strategy):
    def position_management(self, spot) -> None:
        strike_gap = self.context.movement
        ceil_option = int(math.ceil(spot / float(strike_gap))) * strike_gap
        flr_option = int(math.floor(spot / float(strike_gap))) * strike_gap


        # options = []
        # for i in range(5):
        #     options.append(f"{ceil_option+i*strike_gap}CE"),
        #     options.append(f"{ceil_option+i*strike_gap}PE"),

        #     options.append(f"{flr_option-i*strike_gap}CE"),
        #     options.append(f"{flr_option-i*strike_gap}PE"),
        
        # OIs = self.context.get_OI(options)
        # Volumes = self.context.get_Volumes(options)

        options = []
        # for i in range(20):
        #     options.append(f"{ceil_option+i*strike_gap}CE"),

        #     options.append(f"{flr_option-i*strike_gap}PE"),
        
        gcalc = Greeks()
        
        IVs = self.context.get_IVs(spot, options)

        spot_option = int(round(spot / float(self.context.movement))) * self.context.movement

        # Adding the IV instrument to hash map
        # in case it is not present already 
        # spread_instruments = [
        #     self._get_option(f'{spot_option}CE'),
        #     self._get_option(f'{spot_option}PE'),
        # ]

        # prices = self.MD._get_price(spread_instruments)

        prices = self.context.get_current_price([
            f'{spot_option}CE',
            f'{spot_option}PE',
        ])

        ttm = self.context.timeToMaturity()
        IVC = gcalc.Call_IV(spot, spot_option, self.context.rfr, ttm, prices[0])
        IVP = gcalc.Put_IV(spot, spot_option, self.context.rfr, ttm, prices[1])

        
        atm_IV = self.context.straddle_IV(spot)
        IVs = [atm_IV]

        data = []
        data.append(spot) 
        data.extend(IVs)
        data.append(prices[0])
        data.append(prices[1])
        
        # data.extend(OIs)
        # data.extend(Volumes)

        self.context.strategy_args["DataStorage"].append(data)

        pass

    def hedge(self, spot) -> None:
        pass

    def hedge_point(self, spot) -> bool:
        pass

    def new_position_handler(self, spot) -> None:
        self.context.strategy_args["DataStorage"] = []
        pass

    def existing_position_handler(self, spot):
        pass