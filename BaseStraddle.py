from XTConnect.APIWrapper import MarketData, Interaction
from Greeks import Greeks
from strategies.strategy import Strategy
from strategies.policy import (
    Policy,
    CustomPortfolioBuilder,
)

import yaml
import datetime
import math

import pandas as pd
import os

import numpy as np

class BaseStraddle():    
    MD = MarketData(None, None)

    global_order_tracker = 0

    def __init__(
            self,
            index : str,
            expiry : str,
            adjustment : int,
            rfr: float,
            instruments : list,
            Order : Interaction,
            strategy_args : dict,
            strategy : Strategy,
            policy : Policy,
            name : str,
        ) -> None:
        
        self.index = index
        self.expiry = expiry
        self.adjustment = adjustment
        self.rfr = rfr
        self.name = name


        # ATR tracking
        self.previous_close = strategy_args["previous_close"]
        self.open = None
        self.close = None
        self.high = None
        self.low = None
        
        # self.helper = Ins_Find
        self.instruments = instruments
        self.order_placer = Order

        index_config_file = f"{os.path.dirname(os.path.realpath(__file__))}\configs\index_configs.yml"

        with open(index_config_file, 'r') as f:
            index_configs = yaml.safe_load(f)
        
        self.movement = index_configs[index]['movement']
        self.lot_size = index_configs[index]['lot_size']
        self.limit = index_configs[index]['limit']

        # Strategy Configurations
        self.demand = strategy_args["demand"]
        self.wings = strategy_args['wings']

        if strategy_args.get("modify_strike_gap", 0) != 0:
            self.movement = strategy_args["modify_strike_gap"]
            print(self.movement)

        # order management
        self.orders = {}
        self.instrument_prices = {}
        self.portfolio = {}
        self.order_book = None
        self.total_pnl = 0
        self.net_value = 0

        self.position = None

        self.greeks = {}

        # Strategy
        self._strategy = None
        self.set_strategy(strategy)
        self.strategy_args = strategy_args

        # Policy
        self._policy = None
        self.set_policy(policy)
        self.policy_variables = {}

        # Stop Loss
        self.hit_stop_loss = False

        self.buy_qty = 0
        self.sell_qty = 0
        self.buy_value = 0
        self.sell_value = 0
        self.total_lot_sizes_traded = 0

    
    '''
    ##########################
    Defined Standard Entry Point
    To excute one step of strategy
    ##########################
    '''
    
    def set_up(self, spot, existing_position = False):
        self.open = spot
        self.close = spot
        self.high = spot
        self.low = spot
        
        if not existing_position:
            self.new_position_handler(spot)
        else:
            strategy_args = self.strategy_args
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
            
            self.existing_position_handler(spot)
        

    def monitor_and_trade(self, spot):
        self.update_prices(spot)

        self.track_high_low_close(spot)
        
        if self.strategy_args["IVCalc"] == "Reference":
            self.greeks = self.get_portfolio_greeks(spot, refIV=self.strategy_args["refIV"])
        else:
            self.greeks = self.get_portfolio_greeks(spot)

        self.strategy_args["MaxPnl"] = max(self.strategy_args.get("MaxPnl", 0), self.PnL())
        self.strategy_args["MinPNL"] = min(self.strategy_args.get("MinPNL", 0), self.PnL())
        
        self.pretty_print(self.greeks)
        print(self.portfolio)
        
        self.position_management(spot)

        if self.hedge_point(spot) :
            self.hedge(spot)
        

        if self.total_pnl < self.strategy_args["stop_loss"]:
            self.hit_stop_loss = True
        else:
            self.hit_stop_loss = False
        
        self.execute_policy(spot)

        self.strategy_args["position_exists"] = True
        self.strategy_args["existing_pf"] = self.portfolio
        self.strategy_args["existing_pf_value"] = self.net_value - self.total_pnl

        return self.strategy_args

    '''
    ##########################
    Strategy Related Functions
    ##########################
    '''

    def set_strategy(self, strategy : Strategy):
        # print(f"Context: Transitioning to {type(strategy).__name__}")
        self._strategy = strategy
        self._strategy.context = self
        pass

    def position_management(self, spot):
        self._strategy.position_management(spot)

    def hedge(self, spot):
        self._strategy.hedge(spot)

    def hedge_point(self, spot):
        return self._strategy.hedge_point(spot)
    
    def new_position_handler(self, spot):
        self._strategy.new_position_handler(spot)

    def existing_position_handler(self, spot):
        self._strategy.existing_position_handler(spot)
    
    '''
    ##########################
    Policy Related Functions
    ##########################
    '''

    def set_policy(self, policy : Policy):
        # print(f"Context: Transitioning to {type(policy).__name__}")
        self._policy = policy
        self._policy.context = self
        pass

    def execute_policy(self, spot):
        self._policy.execute_policy(spot)
    
    '''
    ##########################
    General Functions
    ##########################
    '''
    def adjust(self, spot, strategy_args):
        if self.position == None:
            position = int(round(spot / float(self.movement))) * self.movement
            self.create_position(position, spot)
            return self.position
         
        # if spot - 50 > position
        # move position up by 100 (add)
        if (spot - self.movement/2 > self.position):
            self.position_up(spot)
    
        # if spot + 50 < position
        # move position down by 100 (subtract)
        elif (spot + self.movement/2 < self.position):
            self.position_down(spot)

        else:
            return self.position

        print(self.portfolio, flush=True)

        return self.position

    def insert_trades(self, trade_df : pd.DataFrame):
        if trade_df.empty:
            return
        
        print("here")
        for option in trade_df.index:
            qty = trade_df.loc[option]["Qty"]
            self.portfolio[option] = self.portfolio.get(option,0) + qty
            # print(item)
            self.net_value += trade_df.loc[option]["Prod"]*(qty/abs(qty))
            self.orders[option] = self._get_option(option)
        pass
    
    def pretty_print(self, greeks):
        # print(f"P&L: {greeks['portfolio_price'] - self.net_value  :.2f}", flush=True)
        print(flush=True)
        print(f"P&L: {self.PnL()  :.2f}", flush=True)
        print(f"Market Price: {greeks['portfolio_price']  :.2f}", flush=True)
        print(f"BS Price: {greeks['portfolio_BSprice']  :.2f}", flush=True)
        print(f"Delta: {greeks['portfolio_delta']  :.2f}", flush=True)
        print(f"Gamma: {greeks['portfolio_gamma']  :.2f}", flush=True)
        print(f"Theta: {greeks['portfolio_theta']  :.2f}", flush=True)
        print(f"Vega: {greeks['portfolio_vega']  :.2f}", flush=True)
        print(flush=True)
        print(f"Portfolio IV: {greeks['portfolio_IVs']*100  :.2f}%", flush=True)
        print(flush=True)
        pass

    def get_portfolio_greeks(self, spot, refIV = None):
        gcalc = Greeks()

        pricinginstruments = []
        options = []

        for key in self.portfolio:
            # ignores portfolio entries that are empty
            if self.portfolio[key] == 0:
                continue
            options.append(key)
            pricinginstruments.append(self.orders[key])
        
        # prices = self.MD._get_price(pricinginstruments)

        prices = self.get_current_price(options)


        ttm = self.timeToMaturity()
        k = len(prices)

        pfprice = 0
        IVs = []
        BSprices = []
        deltas = [] 
        gammas = []
        thetas = []
        vegas = []

        # we find each greek
        # for every item in the portfolio
        
        for i in range(k):
            type = options[i][-2:]
            strike = int(options[i][:-2])
            # Implied Volatility and Price
            if type == 'CE':
                IV = gcalc.Call_IV(spot, strike, self.rfr, ttm, prices[i])
                if np.isnan(IV):
                    IV =  gcalc.Put_IV(spot, strike, self.rfr, ttm, self.get_current_price([str(strike)+"PE"])[0])
                    # print(f"Corrected IV : {IV}")
                    # if np.isnan(IV):
                        # print("???")
                        # print(spot, strike, self.rfr, ttm, self.get_current_price([str(strike)+"PE"]))
                # IV = gcalc.Call_IV(spot, strike, self.rfr, ttm, prices[i])
                BSprice = gcalc.Call_BS_Value(spot, strike, self.rfr, ttm, IV)*self.portfolio[options[i]]
            elif type == 'PE':
                IV = gcalc.Put_IV(spot, strike, self.rfr, ttm, prices[i])
                if np.isnan(IV):
                    IV = gcalc.Call_IV(spot, strike, self.rfr, ttm, self.get_current_price([str(strike)+"CE"])[0])
                    # print(f"Corrected IV : {IV}")
                    
                    # if np.isnan(IV):
                        # print("???")
                        # print(spot, strike, self.rfr, ttm, self.get_current_price([str(strike)+"PE"]))
                # IV = gcalc.Put_IV(spot, strike, self.rfr, ttm, prices[i])
                BSprice = gcalc.Put_BS_Value(spot, strike, self.rfr, ttm, IV)*self.portfolio[options[i]]
            else:
                print("Error")

            # print(spot, strike, self.rfr, ttm, prices[i])
            # print(IV)
            
            calc_IV = IV if refIV == None else refIV
            delta = gcalc.delta(type, spot, strike, ttm, calc_IV, self.rfr)*self.portfolio[options[i]]
            gamma = gcalc.gamma(type, spot, strike, ttm, calc_IV, self.rfr)*self.portfolio[options[i]]
            theta = gcalc.theta(type, spot, strike, ttm, calc_IV, self.rfr)*self.portfolio[options[i]]
            vega = gcalc.vega(type, spot, strike, ttm, calc_IV, self.rfr)*self.portfolio[options[i]]
            pfprice += prices[i]*self.portfolio[options[i]]

            IVs.append(IV)
            BSprices.append(BSprice)
            deltas.append(delta)
            gammas.append(gamma)
            thetas.append(theta)
            vegas.append(vega)
        
        return {
            "portfolio_price" : pfprice,
            "portfolio_BSprice" : sum(BSprices),
            "portfolio_delta" : sum(deltas),
            "portfolio_gamma" : sum(gammas),
            "portfolio_theta" : sum(thetas),
            "portfolio_vega" : sum(vegas),
            "portfolio_IVs" : sum(IVs)/len(IVs) if len(IVs) != 0 else 0,
        }

    def track_high_low_close(self, spot):
        
        if spot > self.high:
            self.high = spot
        elif spot < self.low:
            self.low = spot
        else:
            pass
        
        self.close = spot
    
    def straddle_IV(self, spot):
        gcalc = Greeks()

        spot_option = int(round(spot / float(self.movement))) * self.movement

        # Adding the IV instrument to hash map
        # in case it is not present already 
        # spread_instruments = [
        #     self._get_option(f'{spot_option}CE'),
        #     self._get_option(f'{spot_option}PE'),
        # ]

        # prices = self.MD._get_price(spread_instruments)

        prices = self.get_current_price([
            f'{spot_option}CE',
            f'{spot_option}PE',
        ])

        ttm = self.timeToMaturity()
        IVC = gcalc.Call_IV(spot, spot_option, self.rfr, ttm, prices[0])
        IVP = gcalc.Put_IV(spot, spot_option, self.rfr, ttm, prices[1])

        return (IVC+IVP)/2

    def find_straddle_price(self, spot, tte, IV):
        gcalc = Greeks()

        atm_option = int(round(spot / float(self.movement))) * self.movement
        call_price = gcalc.Call_BS_Value(spot, atm_option, self.rfr, tte, IV)
        put_price = gcalc.Put_BS_Value(spot, atm_option, self.rfr, tte, IV)
        
        return call_price+put_price
    
    def find_strangle_price(self, spot, tte, IV):
        gcalc = Greeks()

        atm_option = int(round(spot / float(self.movement))) * self.movement
        call_position, put_position = self.find_strangle_strikes(atm_option, spot)

        call_price = gcalc.Call_BS_Value(spot, call_position, self.rfr, tte, IV)
        put_price = gcalc.Put_BS_Value(spot, put_position, self.rfr, tte, IV)
        
        return call_price+put_price

    def timeToMaturity(self):
        '''
        UPDATE TTM IN INDEX TRACKER
        In the future TTM needs:
        - Exchange Timings
        - Year
        '''
        date_str = self.expiry
        # date_str +='23'     # Year, needs to be set
        exp1 = datetime.datetime.strptime(date_str, '%d%b%y')
        expiry_date = exp1.strftime('%d-%m-%y')
        # t1 = datetime.datetime.now().date()
        t1 = self.MD.current_date
        t1 = datetime.datetime.strptime(t1, '%d-%m-%Y').date()
        t2 = datetime.datetime.strptime(expiry_date, "%d-%m-%y").date()
        t3 = self.MD.current_time
        t3 = datetime.datetime.strptime(str(t3), "%Y-%m-%d %H:%M:%S").time()
        # t3 = datetime.datetime.now().time()
        t4 = datetime.time(15, 30, 0)
        ttm = (t2 - t1).days
        
        print(t1,t2,t3,ttm)
        # Adjusting for holidays and weekends
        ttm -= self.adjustment
        
        time_in_day = self.timeinDay()
        # if time_in_day > 0:
        ttm += time_in_day
        return ttm

    def timeinDay(self):
        """
        Returns time left in day
        """
        t_now = self.MD.current_time
        t_now = datetime.datetime.strptime(str(t_now), "%Y-%m-%d %H:%M:%S").time()
        t_end = datetime.time(15, 30, 0)
        
        # 22500 is the number of seconds in the trading day
        tid = ((datetime.datetime.combine(datetime.date.min, t_end) - datetime.datetime.combine(datetime.date.min, t_now)).total_seconds() + 60 )/ 22500
        
        return tid

    def PnL(self):
        curr_val = self.get_current_value(self.orders)
        PnL = curr_val - self.net_value
        self.total_pnl += PnL
        self.net_value = curr_val
        return self.total_pnl
    
    def square_off_all(self, suppress_print = False):
        instruments = self.orders
        
        options_list = []
        is_sell_list = []
        quantity_list = []

        final_value = self.PnL()
        for key in self.portfolio:
            # ignores portfolio entries that are empty
            if self.portfolio[key] == 0:
                continue
            ins = instruments[key]
            quantity = abs(self.portfolio[key])
            to_be_sold = True if self.portfolio[key] > 0 else False
            options_list.append(key)
            is_sell_list.append(to_be_sold)
            quantity_list.append(quantity)
            # self.create_sized_position(ins, sell=to_be_sold, quantity=quantity)
        
        self.make_orders(options_list, is_sell_list, quantity_list)

        if suppress_print:
            return f"Squared off {self.index}, PNL = {final_value}"
        else: 
            print(f"Squared off {self.index}, PNL = {final_value}")
    
    def create_position(self, position, spot):
        # selling straddle

        instruments = {}

        # straddle or strangle
        
        if position > spot:
            call_position = position
            if position - spot > self.movement//4:
                put_position = position-self.movement
            else:
                put_position = position
        else:
            put_position = position
            if spot - position > self.movement//4:
                call_position = position+self.movement
            else:
                call_position = position


        adjusted_quantity = (self.demand//self.lot_size)*self.lot_size

        options_list = [f'{put_position}PE', f'{call_position}CE', f'{put_position-self.wings}PE', f'{call_position+self.wings}CE']
        is_sell_list = [True, True, False, False]
        quantity_list = [adjusted_quantity]*4

        self.make_orders(options_list, is_sell_list, quantity_list)

        print(f"Sold Put at {put_position}", flush=True)
        print(f"Sold Call at {call_position}", flush=True)
        print(f"Bought Put at {put_position-self.wings}", flush=True)        
        print(f"Bought Call at {call_position+self.wings}", flush=True)

        self.position = position


        pass

    
    
    '''
    ##########################
    Option Chain Monitoring
    ##########################
    '''

    def IV_ratio_at_distance(self, spot, position, distance):
        call_position, put_position = self.find_strangle_strikes(position, spot)

        call_position = call_position + distance
        put_position = put_position - distance

        gcalc = Greeks()

        call_price, put_price = self.get_current_price(
            [
                f"{call_position}CE",
                f"{put_position}PE",
            ]
        )

        Call_IV = gcalc.Call_IV(spot, call_position, self.rfr, self.timeToMaturity(), call_price)
        Put_IV = gcalc.Put_IV(spot, put_position, self.rfr, self.timeToMaturity(), put_price)

        ratio = Put_IV/Call_IV

        return ratio

    def IV_ratio_at_delta(self, spot, position, delta):
        call_position, put_position = self.find_strangle_strikes(position, spot)

        options = []
        #  delta for nearest 20 options
        for i in range(10):
            strike = call_position+i*self.movement
            options.append(f"{strike}CE")

        for i in range(10):
            strike = put_position-i*self.movement
            options.append(f"{strike}PE")

        prices = self.get_current_price(options)

        for i in range(10):
            pass
    
    '''
    ##########################
    Straddle Building Related Functions
    ##########################
    '''
    def find_strangle_strikes(self, position, spot):
        if position > spot:
            call_position = position
            if position - spot > self.movement//4:
                put_position = position-self.movement
            else:
                put_position = position
        else:
            put_position = position
            if spot - position > self.movement//4:
                call_position = position+self.movement
            else:
                call_position = position
        
        return call_position, put_position

    def buy_wings(self, call_position, put_position, wing_distance, adjusted_quantity):
        options_list = [f'{put_position-wing_distance}PE', f'{call_position+wing_distance}CE']
        is_sell_list = [False, False]
        quantity_list = [adjusted_quantity]*2

        self.make_orders(options_list, is_sell_list, quantity_list)
        pass

    def sell_strangle(self, call_position, put_position, adjusted_quantity):
        
        options_list = [f'{put_position}PE', f'{call_position}CE']
        is_sell_list = [True, True]
        quantity_list = [adjusted_quantity]*2

        self.make_orders(options_list, is_sell_list, quantity_list)
        pass

    def _buy_strangle(self, call_position, put_position, adjusted_quantity):
        
        options_list = [f'{put_position}PE', f'{call_position}CE']
        is_sell_list = [False, False]
        quantity_list = [adjusted_quantity]*2

        self.make_orders(options_list, is_sell_list, quantity_list)
        pass
    
    def strangle_with_wings(self, position, spot):
        call_position, put_position = self.find_strangle_strikes(position, spot)
        adjusted_quantity = (self.demand//self.lot_size)*self.lot_size
        
        self.buy_wings(call_position, put_position, self.wings, adjusted_quantity)
        self.sell_strangle(call_position, put_position, adjusted_quantity)
        
        self.position = position
        pass
    
    def naked_straddle(self, position, spot, sizing = None):
        if not sizing:
            sizing = self.demand
        else:
            sizing = min(sizing, self.demand)
        
        call_position, put_position = self.find_strangle_strikes(position, spot)
        adjusted_quantity = (sizing//self.lot_size)*self.lot_size
        self.sell_strangle(call_position, put_position, adjusted_quantity)
        self.position = position

    def strangle_long(self, position, spot):
        call_position, put_position = self.find_strangle_strikes(position, spot)
        adjusted_quantity = (self.demand//self.lot_size)*self.lot_size

        self._buy_strangle(call_position, put_position, adjusted_quantity)
        self.position = position

    def otm_strangle_long(self, spot, quantity, strikes_away = 1):
        call_option = int(math.ceil(spot / float(self.movement))) * self.movement + self.movement*(strikes_away-1) 
        put_option = int(math.floor(spot / float(self.movement))) * self.movement - self.movement*(strikes_away-1)
        self._buy_strangle(call_option, put_option, quantity)
        pass

    def get_current_value(self, instruments):
        # uses the self.portfolio to gather the value of the portfolio
        curr_val = 0
        pricinginstruments = []
        keys = []
        for key in self.portfolio:
            # ignores portfolio entries that are empty
            if self.portfolio[key] == 0:
                continue
            keys.append(key)
            pricinginstruments.append(instruments[key])
        
        if len(pricinginstruments) == 0:
            return 0
        
        # prices = self.MD._get_price(pricinginstruments)

        prices = self.get_current_price(keys)

        for i in range(len(prices)):
            curr_val += prices[i]*self.portfolio[keys[i]]
        
        return curr_val
    
    def close_position(self, position):
        '''
        Depreciation
        '''

        # lot_size = 25
        # limit = 901
        # demand = 5000

        '''
        ==================================
        BUY STRADDLE PUT
        ==================================
        '''
        ins = self._get_put(strike=position)
        self.create_sized_position(ins, sell=False, quantity=self.demand)
        print(f"Bought Put at {position}", flush=True)

        '''
        ==================================
        BUY STRADDLE CALL
        ==================================
        '''
        ins = self._get_call(strike=position)
        self.create_sized_position(ins, sell=False, quantity=self.demand)
        print(f"Bought Call at {position}", flush=True)
        
        
        '''
        ==================================
        SELL WING PUT
        ==================================
        '''
        ins = self._get_put(strike=position-self.wings)
        self.create_sized_position(ins, sell=True, quantity=self.demand)
        print(f"Sold Put at {position-self.wings}", flush=True)
        
        
        '''
        ==================================
        SELL WING CALL
        ==================================
        '''
        ins = self._get_call(strike=position+self.wings)
        self.create_sized_position(ins, sell=True, quantity=self.demand)
        print(f"Sold Call at {position+self.wings}", flush=True)
        

        self.position = None
        self.portfolio[f'{position}PE'] =  self.portfolio.get(f'{position}PE', 0) + self.demand
        self.portfolio[f'{position}CE'] =  self.portfolio.get(f'{position}CE', 0) + self.demand
        self.portfolio[f'{position-self.wings}PE'] =  self.portfolio.get(f'{position-self.wings}PE', 0) - self.demand
        self.portfolio[f'{position+self.wings}CE'] =  self.portfolio.get(f'{position+self.wings}CE', 0) - self.demand

        curr_val = self.get_current_value(self.orders)

        self.total_pnl += curr_val - self.net_value

        self.orders = None
        self.net_value = 0

        pass

    def position_up(self, spot):
        new_position = self.position + self.movement
        self.close_position(self.position)
        self.create_position(new_position, spot)
        pass

    def position_down(self, spot):
        new_position = self.position - self.movement
        self.close_position(self.position)
        self.create_position(new_position, spot)
        pass

    def atm_straddle_price(self, spot) -> tuple[int, int]:
        '''
        Finds the At the Money Options and the ATM straddle price

        Returns: ATM straddle price, ATM option strikeprice
        '''
        atm_option = int(round(spot / float(self.movement))) * self.movement
        ceil_option = int(math.ceil(spot / float(self.movement))) * self.movement
        flr_option = int(math.floor(spot / float(self.movement))) * self.movement

        prices = self.get_current_price(
            [
                f"{ceil_option}CE",
                f"{ceil_option}PE",
                f"{flr_option}CE",
                f"{flr_option}PE",
                # f"{ceil_option+self.movement}CE",
                # f"{ceil_option+self.movement}PE",
                # f"{flr_option-self.movement}CE",
                # f"{flr_option-self.movement}PE",
            ]
        )

        ceil_straddle = prices[0] + prices[1]
        flr_straddle = prices[2] + prices[3]
        # ceil_straddle2 = prices[4] + prices[5]
        # flr_straddle2= prices[6] + prices[7]

        # straddle_price = (
        #     (spot - flr_option) * ceil_straddle + (ceil_option - spot) * flr_straddle
        # ) / self.movement
        # straddle_price = min(ceil_straddle, flr_straddle, ceil_straddle2, flr_straddle2)
        straddle_price = min(ceil_straddle, flr_straddle)
        return straddle_price, atm_option

    def call_bull_spread(self, spot, pfdelta, hedge_amount, ref_IV):

        straddle_price, atm_option = self.atm_straddle_price(spot)

        tolerance = 0.1
        spread = int(math.ceil(( straddle_price + self.movement*(tolerance)) / float(self.movement))) * self.movement
        spread = max(spread, self.movement)
        spread_opt = atm_option + spread

        
        '''
        FInding Delta of the spread at the moment
        '''
        # spread_instruments = [self._get_call(strike=atm_option), self._get_call(strike=spread_opt)]
        # prices = self.MD._get_price(spread_instruments)

        prices = self.get_current_price([
            f'{atm_option}CE',
            f'{spread_opt}CE',
        ])
        
        gcalc = Greeks()
        ttm = self.timeToMaturity()
        IV = gcalc.Call_IV(spot, atm_option, self.rfr, ttm, prices[0])
        # ignoring implied vol and calculating delta at ref IV due to np.nan
        IV = ref_IV
        delta1 = gcalc.delta('CE', spot, atm_option, ttm, IV, self.rfr)
        
        IV = gcalc.Call_IV(spot, spread_opt, self.rfr, ttm, prices[1])
        IV = ref_IV
        delta2 = gcalc.delta('CE', spot, spread_opt, ttm, IV, self.rfr)

        delta = delta1-delta2
        quantity = abs(pfdelta/delta)*hedge_amount
        quantity = (quantity//self.lot_size)*self.lot_size

        options_list = [f'{atm_option}CE', f'{spread_opt}CE']
        is_sell_list = [False, True]
        quantity_list = [quantity, quantity]

        self.make_orders(options_list, is_sell_list, quantity_list)

        print(f"Bought Call at {atm_option}, Quantity: {quantity}", flush=True)
        print(f"Sold Call at {spread_opt}, Quantity: {quantity}" , flush=True)

        pass
    
    def call_bear_spread(self, spot, pfdelta, hedge_amount, ref_IV):
        
        straddle_price, atm_option = self.atm_straddle_price(spot)

        tolerance = 0.1
        spread = int(math.ceil(( straddle_price + self.movement*(tolerance)) / float(self.movement))) * self.movement
        spread = max(spread, self.movement)
        spread_opt = atm_option + spread


        '''
        FInding Delta of the spread at the moment
        '''
        # spread_instruments = [self._get_call(strike=atm_option), self._get_call(strike=spread_opt)]
        # prices = self.MD._get_price(spread_instruments)

        prices = self.get_current_price([
            f'{atm_option}CE',
            f'{spread_opt}CE',
        ])

        gcalc = Greeks()
        ttm = self.timeToMaturity()
        IV = gcalc.Call_IV(spot, atm_option, self.rfr, ttm, prices[0])
        IV = ref_IV
        delta1 = gcalc.delta('CE', spot, atm_option, ttm, IV, self.rfr)
        
        IV = gcalc.Call_IV(spot, spread_opt, self.rfr, ttm, prices[1])
        IV = ref_IV
        delta2 = gcalc.delta('CE', spot, spread_opt, ttm, IV, self.rfr)

        delta = delta1-delta2
        quantity = abs(pfdelta/delta)*hedge_amount
        quantity = (quantity//self.lot_size)*self.lot_size

        options_list = [f'{atm_option}CE', f'{spread_opt}CE']
        is_sell_list = [True, False]
        quantity_list = [quantity, quantity]

        self.make_orders(options_list, is_sell_list, quantity_list)

        print(f"Sold Call at {atm_option}, Quantity: {quantity}", flush=True)
        print(f"Bought Call at {spread_opt}, Quantity: {quantity}", flush=True)        

        pass

    def put_bull_spread(self, spot, pfdelta, hedge_amount, ref_IV):
        
        straddle_price, atm_option = self.atm_straddle_price(spot)

        tolerance = 0.1
        spread = int(math.ceil(( straddle_price + self.movement*(tolerance)) / float(self.movement))) * self.movement
        spread = max(spread, self.movement)
        spread_opt = atm_option - spread


        '''
        FInding Delta of the spread at the moment
        '''

        # spread_instruments = [self._get_put(strike=atm_option), self._get_put(strike=spread_opt)]
        # prices = self.MD._get_price(spread_instruments)

        prices = self.get_current_price([
            f'{atm_option}PE',
            f'{spread_opt}PE',
        ])

        gcalc = Greeks()
        ttm = self.timeToMaturity()
        IV = gcalc.Put_IV(spot, atm_option, self.rfr, ttm, prices[0])
        IV = ref_IV
        delta1 = gcalc.delta('PE', spot, atm_option, ttm, IV, self.rfr)
        
        IV = gcalc.Put_IV(spot, spread_opt, self.rfr, ttm, prices[1])
        IV = ref_IV
        delta2 = gcalc.delta('PE', spot, spread_opt, ttm, IV, self.rfr)

        delta = delta1-delta2
        quantity = abs(pfdelta/delta)*hedge_amount
        quantity = (quantity//self.lot_size)*self.lot_size


        options_list = [f'{atm_option}PE', f'{spread_opt}PE']
        is_sell_list = [True, False]
        quantity_list = [quantity, quantity]

        self.make_orders(options_list, is_sell_list, quantity_list)
        
        print(f"Sold Put at {atm_option}, Quantity: {quantity}", flush=True)
        print(f"Bought Put at {spread_opt}, Quantity: {quantity}", flush=True)

        pass
    
    def put_bear_spread(self, spot, pfdelta, hedge_amount, ref_IV):
        
        straddle_price, atm_option = self.atm_straddle_price(spot)

        tolerance = 0.1
        spread = int(math.ceil(( straddle_price + self.movement*(tolerance)) / float(self.movement))) * self.movement
        spread = max(spread, self.movement)
        spread_opt = atm_option - spread

        '''
        FInding Delta of the spread at the moment
        '''

        # spread_instruments = [self._get_put(strike=atm_option), self._get_put(strike=spread_opt)]
        # prices = self.MD._get_price(spread_instruments)

        prices = self.get_current_price([
            f'{atm_option}PE',
            f'{spread_opt}PE',
        ])

        gcalc = Greeks()
        ttm = self.timeToMaturity()
        IV = gcalc.Put_IV(spot, atm_option, self.rfr, ttm, prices[0])
        IV = ref_IV
        delta1 = gcalc.delta('PE', spot, atm_option, ttm, IV, self.rfr)
        
        IV = gcalc.Put_IV(spot, spread_opt, self.rfr, ttm, prices[1])
        IV = ref_IV
        delta2 = gcalc.delta('PE', spot, spread_opt, ttm, IV, self.rfr)

        delta = delta1-delta2
        quantity = abs(pfdelta/delta)*hedge_amount
        quantity = (quantity//self.lot_size)*self.lot_size


        options_list = [f'{atm_option}PE', f'{spread_opt}PE']
        is_sell_list = [False, True]
        quantity_list = [quantity, quantity]

        self.make_orders(options_list, is_sell_list, quantity_list)

        print(f"Bought Put at {atm_option}, Quantity: {quantity}", flush=True)
        print(f"Sold Put at {spread_opt}, Quantity: {quantity}", flush=True)

        pass

    '''
    ##########################
    Functions to hedge by buying already sold options
    
    ##########################
    '''

    def hedge_by_buying_calls(self, spot, pfdelta, ref_IV):
        candidates = self._hedge_candidates("CE")
        closest = self._find_closest_candidate(spot, list(candidates.keys()))
        self._get_quantity_and_make_order(spot, pfdelta, ref_IV, closest)
        pass

    def hedge_by_buying_puts(self, spot, pfdelta, ref_IV):
        candidates = self._hedge_candidates("PE")
        closest = self._find_closest_candidate(spot, list(candidates.keys()))
        self._get_quantity_and_make_order(spot, pfdelta, ref_IV, closest)
        pass

    def _hedge_candidates(self, opttype):
        candidates = {}
        for key, value in self.portfolio.items():
            if value < 0 and key[-2:] == opttype:
                candidates[key] = value
            pass
        return candidates
    
    def _find_closest_candidate(self, spot, candidates):
        closest = candidates[0]
        minimum = abs(int(closest[:-2])-spot)
        for item in candidates:
            if abs(int(item[:-2])-spot) < minimum:
                minimum = abs(int(item[:-2])-spot)
                closest = item
        
        return closest
    
    def _get_quantity_and_make_order(self, spot, pfdelta, ref_IV, closest):
        prices = self.get_current_price([
            closest,
        ])

        gcalc = Greeks()
        ttm = self.timeToMaturity()
        IV = ref_IV
        delta_opt = gcalc.delta(closest[-2:], spot, int(closest[:-2]), ttm, IV, self.rfr)
        
        quantity = min(abs(pfdelta/delta_opt), abs(self.portfolio[closest]))
        quantity = (quantity//self.lot_size)*self.lot_size

        # self.make_orders([closest], sell=[False], quantities=[quantity])
        self.make_orders_in_multiple_cycles([closest], sell=[False], quantities=[quantity], lots_per_cycle=self.strategy_args["construction_lots_per_cycle"])
        pass


    '''
    ##########################
    Functions to hedge by selling already bought options
    ##########################
    '''

    def hedge_by_selling_calls(self, spot, pfdelta, ref_IV):
        candidates = self._hedge_candidates_sell("CE")
        closest = self._find_closest_candidate(spot, list(candidates.keys()))
        self._get_quantity_and_make_order_sell(spot, pfdelta, ref_IV, closest)
        pass

    def hedge_by_selling_puts(self, spot, pfdelta, ref_IV):
        candidates = self._hedge_candidates_sell("PE")
        closest = self._find_closest_candidate(spot, list(candidates.keys()))
        self._get_quantity_and_make_order_sell(spot, pfdelta, ref_IV, closest)
        pass

    def _hedge_candidates_sell(self, opttype):
        candidates = {}
        for key, value in self.portfolio.items():
            if value > 0 and key[-2:] == opttype:
                candidates[key] = value
            pass
        return candidates
    
    def _get_quantity_and_make_order_sell(self, spot, pfdelta, ref_IV, closest):
        prices = self.get_current_price([
            closest,
        ])

        gcalc = Greeks()
        ttm = self.timeToMaturity()
        IV = ref_IV
        delta_opt = gcalc.delta(closest[-2:], spot, int(closest[:-2]), ttm, IV, self.rfr)
        
        quantity = min(abs(pfdelta/delta_opt), abs(self.portfolio[closest]))
        quantity = (quantity//self.lot_size)*self.lot_size

        # self.make_orders([closest], sell=[False], quantities=[quantity])
        self.make_orders_in_multiple_cycles([closest], sell=[True], quantities=[quantity], lots_per_cycle=self.strategy_args["construction_lots_per_cycle"])
        pass
        
    
    '''
    ##########################
    Functions to hedge by buying already sold spreads
    
    ##########################
    '''
    def hedge_by_buying_call_spreads(self, spot, pfdelta, ref_IV):
        candidates_to_buy = self._hedge_candidates("CE")
        candidates_to_sell = self._hedge_candidates_to_sell("CE")

        closest = self._find_closest_candidate(spot, list(candidates_to_buy.keys()))
        furthest = self._find_furthest_candidate(spot, list(candidates_to_sell.keys()))

        self._get_quantity_and_make_order_for_spreads(spot, pfdelta, ref_IV, closest, furthest)
        pass

    def hedge_by_buying_put_spreads(self, spot, pfdelta, ref_IV):
        candidates_to_buy = self._hedge_candidates("PE")
        candidates_to_sell = self._hedge_candidates_to_sell("PE")

        closest = self._find_closest_candidate(spot, list(candidates_to_buy.keys()))
        furthest = self._find_furthest_candidate(spot, list(candidates_to_sell.keys()))

        self._get_quantity_and_make_order_for_spreads(spot, pfdelta, ref_IV, closest, furthest)
        pass

    def _hedge_candidates_to_sell(self, opttype):
        candidates = {}
        for key, value in self.portfolio.items():
            if value > 0 and key[-2:] == opttype:
                candidates[key] = value
            pass
        return candidates
    
    def _find_furthest_candidate(self, spot, candidates):
        furthest = candidates[0]
        maximum = abs(int(furthest[:-2])-spot)
        for item in candidates:
            if abs(int(item[:-2])-spot) > maximum:
                maximum = abs(int(item[:-2])-spot)
                furthest = item
        
        return furthest
    

    def _get_quantity_and_make_order_for_spreads(self, spot, pfdelta, ref_IV, closest, furthest):
        prices = self.get_current_price([
            closest,
            furthest,
        ])

        gcalc = Greeks()
        ttm = self.timeToMaturity()
        IV = ref_IV

        delta_opt_close = gcalc.delta(closest[-2:], spot, int(closest[:-2]), ttm, IV, self.rfr)
        delta_opt_far = gcalc.delta(furthest[-2:], spot, int(furthest[:-2]), ttm, IV, self.rfr)
        
        delta_spread = delta_opt_close - delta_opt_far

        # print(ttm)
        # print(IV)
        # print(self.rfr)

        quantity = min(abs(pfdelta/delta_spread), abs(self.portfolio[closest]), abs(self.portfolio[furthest]))

        # print(delta_opt_close)
        # print(delta_opt_far)
        # print(pfdelta)

        quantity = (quantity//self.lot_size)*self.lot_size


        # self.make_orders([closest], sell=[False], quantities=[quantity])
        self.make_orders_in_multiple_cycles([closest, furthest], sell=[False, True], quantities=[quantity, quantity], lots_per_cycle=self.strategy_args["construction_lots_per_cycle"])
        pass


    '''
    ##########################
    Functions to hedge by Forwards
    First Iteration
    ##########################
    '''
    def hedge_by_atm_forwards(self, spot, pfdelta, ref_IV):
        straddle_price, atm_option = self.atm_straddle_price(spot)
        qty = abs(pfdelta)

        # if delta positive, sell call buy put
        # if delta negative, buy call sell put
        sell = [True, False] if pfdelta > 0 else [False, True]

        quantity = [qty, qty]
        opts = [
            f"{atm_option}CE",
            f"{atm_option}PE"
        ]

        self.make_orders_in_multiple_cycles(opts, sell, quantity, lots_per_cycle=self.strategy_args["construction_lots_per_cycle"])
        pass

    '''
    ##########################
    Functions to control position size
    First Iteration
    ##########################
    '''
    # objective is to decrease delta
    # take the two most ITM options and cut them off (min pf delta = 0)

    def decrease_position_size_by_spread(self, spot, pfdelta, ref_IV, hedge_amount):
        
        pfdelta = pfdelta*hedge_amount
        is_pfdelta_pos = True if pfdelta > 0 else False

        target = pfdelta
        target_reached = False

        while not target_reached:
            options, delta, quantity = self.find_pairwise_delta(spot, ref_IV, is_pfdelta_pos)

            # in case it is no longer possible to decrease pf size
            if delta == 0:
                if pfdelta > 0:
                    self.call_bear_spread(spot, pfdelta, hedge_amount, ref_IV)
                else:
                    self.put_bull_spread(spot, pfdelta, hedge_amount, ref_IV)
                break
            
            # in case we reach our target delta
            if abs(delta) > abs(target):
                target_reached = True
                quantity = abs(target/delta*quantity)

            # make the required trade
            self.make_orders(options, [False, True], [quantity, quantity])


        pass

    def find_pairwise_delta(
            self, spot: int, ref_IV: float, is_pfdelta_pos: bool
    ) -> tuple[list[str, str], float, float]:
        '''
        Finds maximum pairwise delta of options in portfolio
        Such that it definitely decreases the size of the portfolio

        Returns:
            Option 1 : BUY
            Option 2 : SELL
            Delta Generated by trade
        '''

        calls = []
        puts = []

        for key in self.portfolio.keys():
            if 'CE' in key:
                calls.append(key)
            if 'PE' in key:
                puts.append(key)
        
        calls.sort()
        puts.sort()

        ttm = self.timeToMaturity()
        gcalc = Greeks()

        quantity = 0
        opts = []
        max_delta = 0

        nc = len(calls)
        for i in range(nc):
            for j in range(i, nc):
                if not (is_pfdelta_pos and self.portfolio[calls[i]] > 0 and self.portfolio[calls[j]] < 0 \
                or not is_pfdelta_pos and self.portfolio[calls[i]] < 0 and self.portfolio[calls[j]] > 0) :
                    continue

                # if portfolio delta is positive, we want 
                # ITM Calls to be more than 0 (since we want to sell them)
                # OTM to be less than 0 (since we want to buy them)
                # and vice versa for portfolio delta negative 

                # if pf delta is positive, the higher strike call is bought, else opposite
                buy_call, sell_call = (calls[j], calls[i]) if is_pfdelta_pos else (calls[i], calls[j])
                
                d1 = gcalc.delta('CE', spot, int(buy_call[:-2]), ttm, ref_IV, self.rfr)
                d2 = gcalc.delta('CE', spot, int(sell_call[:-2]), ttm, ref_IV, self.rfr)

                q = min(abs(self.portfolio[buy_call]), abs(self.portfolio[sell_call]))

                # buy - sell
                diff = (d1-d2)*q

                if abs(diff) > abs(max_delta):
                    max_delta = diff
                    opts = [buy_call, sell_call]
                    quantity = q
                pass
            pass
        
        
        # FOR PUTS
        np = len(puts)
        for i in range(np):
            for j in range(np):
                if not (is_pfdelta_pos and self.portfolio[puts[i]] > 0 and self.portfolio[puts[j]] < 0 \
                or not is_pfdelta_pos and self.portfolio[puts[i]] < 0 and self.portfolio[puts[j]] > 0) :
                    continue

                # if pf delta is positive, the higher strike call is bought, else opposite
                buy_put, sell_put = (puts[j], puts[i]) if is_pfdelta_pos else (puts[i], puts[j])

                d1 = gcalc.delta('PE', spot, int(buy_put[:-2]), ttm, ref_IV, self.rfr)
                d2 = gcalc.delta('PE', spot, int(sell_put[:-2]), ttm, ref_IV, self.rfr)

                q = min(abs(self.portfolio[buy_put]), abs(self.portfolio[sell_put]))

                # buy - sell
                diff = (d1-d2)*q

                if abs(diff) > abs(max_delta):
                    max_delta = diff
                    opts = [buy_put, sell_put]
                    quantity = q
                pass
            pass

        return opts, max_delta, quantity

    # making orders by ratio of quantities
    def make_orders(self, options, sell, quantities):
        # print(options)
        spread_instruments = [self._get_option(option) for option in options]
        # prices = self.MD._get_price(spread_instruments)

        prices = self.get_current_price(options)

        full_order_id_list = []
        order_id_to_option = {}

        for i in range(len(spread_instruments)):
            ins = spread_instruments[i]
            quantities[i] = (int(quantities[i]/self.lot_size))*self.lot_size
            oids = self.create_sized_position(ins, sell=sell[i], quantity=quantities[i])
            full_order_id_list.extend(oids)
            d = dict.fromkeys(oids, options[i])
            order_id_to_option.update(d)

            print(f"Options Bought: {options[i]}, Quantity: {quantities[i]}, Sell: {sell[i]}")
            # print(f"Sold Call at {atm_option}, Quantity: {quantity}", flush=True)
            self.orders[
                f'{options[i]}'
            ] = ins

            self.portfolio[options[i]] =  self.portfolio.get(options[i], 0) + (quantities[i] if sell[i]==False else (-quantities[i]))



            self.net_value += (quantities[i] if sell[i]==False else (-quantities[i]))*prices[i]
        

            # slippage = 0.05
            # impact_cost = 0
            # transation_charge = [0.0065, 0.0035]
            # brokerage = 0.5 # per lot

            # slippages = slippage*quantities[i]
            # impact_costs = abs(quantities[i]*prices[i]*impact_cost)
            # transation_charges = quantities[i]*prices[i]*transation_charge[0 if sell[i] else 1]
            # brokerages = int(quantities[i]/self.lot_size)*brokerage

            if sell[i]:
                self.sell_qty += quantities[i]
                self.sell_value += quantities[i]*prices[i]
            else:
                self.buy_qty += quantities[i]
                self.buy_value += quantities[i]*prices[i]

            self.total_lot_sizes_traded += int(quantities[i]/self.lot_size)
        
        self.order_placer.log_orders(options, sell, quantities, self.MD.current_time, self.index, self.expiry, self.name)
        # self.order_placer.confirm_order_statuses(full_order_id_list, order_id_to_option, self.index, self.expiry, self.name)
        pass

    def make_orders_in_multiple_cycles(self, options, sell, quantities, lots_per_cycle):
        n = len(options)
        if len(sell) != n or len(quantities) != n:
            return
        if sum(quantities) == 0:
            return

        self.policy_variables["lots_per_cycle"] = lots_per_cycle
        self.policy_variables["to_create_portfolio"] = dict()
        
        for i in range(n):
            self.policy_variables["to_create_portfolio"][options[i]] = (
                +quantities[i] if sell[i] == True else -quantities[i]
            )
        
        self.set_policy(CustomPortfolioBuilder())
        pass
    
    def change_position_size(self, maximum_number_of_lots_per_cycle, decrease, portfolio = None):
        if portfolio == None:
            portfolio = self.portfolio
        
        lot_size = self.lot_size
        maximum_quantity = 0

        for key in portfolio.keys():
            q = abs(portfolio[key])
            maximum_quantity = max(maximum_quantity, q)
        
        if maximum_quantity == 0:
            return
        multiplier = maximum_number_of_lots_per_cycle*lot_size/maximum_quantity
        
        # never increase position size more than double
        # Also useful when fully closing position sizes
        if multiplier > 1:
            multiplier = 1
        
        options = []
        quantities = []
        sell = []
        for option in portfolio.keys():
            if portfolio[option] == 0:
                pass
            options.append(option)
            
            q = portfolio[option] * multiplier
            q = (int(q/self.lot_size))*self.lot_size

            quantities.append(abs(q))
            
            # if decrease is True and q > 0 then sell
            # if decrease is False and q < 0 then sell
            # otherwise buy
            # XOR function 
            sell.append(not (decrease ^ (q>0)) )
            
        self.make_orders(options, sell, quantities)
        
        return (options, sell, quantities)

    # def make_straddle_by
    
    def create_sized_position(self, instrument, sell, quantity = None):
        order_id_list = []
        to_be_executed = quantity
        while(to_be_executed >= self.lot_size):
            # if to_be_executed is greated than the limit, order limit, else order to_be_executed 
            order_size = self.limit if to_be_executed//self.limit else to_be_executed 
            # rounding off as per lot_size
            order_size = (int(order_size/self.lot_size))*self.lot_size
            to_be_executed -= order_size

            id = self.order_placer.place_order(instrument,
                                          sell=sell,
                                          ouid=str(self.global_order_tracker),
                                          QUANTITY = order_size)
            order_id_list.append(id)
            self.global_order_tracker+=1
        
        return order_id_list
        pass


    def find_delta_strike(self, spot, delta):
        gcalc = Greeks()

        atm_straddle_price, atm_strike = self.atm_straddle_price(spot)
        atm_IV = self.straddle_IV(spot)

        put_deltas_and_ivs = []
        call_deltas_and_ivs = []
        
        n = 5
        m = 0
        # n = 4
        calls, call_prices = self.get_n_otm_call_prices(atm_strike, n)
        puts, put_prices = self.get_n_otm_put_prices(atm_strike, n)

        # calls, call_prices = None, None
        # puts, put_prices = None, None
        # for n in range(4, 12, 2):
        #     try:
        #         calls_temp, call_prices_temp = self.get_n_otm_call_prices(atm_strike, n)
        #         puts_temp, put_prices_temp = self.get_n_otm_put_prices(atm_strike, n)

        #         calls, call_prices = calls_temp, call_prices_temp
        #         puts, put_prices = puts_temp, put_prices_temp
                
        #     except Exception as e:
        #         break
            
        # print(calls, call_prices)
        tte = self.timeToMaturity()

        for i, strike in enumerate(calls):
            option_price = call_prices[i]

            option_IV = gcalc.Call_IV(spot, strike, 0, tte, option_price)
            option_delta = gcalc.delta("CE", spot, strike, tte, option_IV, 0)
            call_deltas_and_ivs.append((option_delta, option_IV))
        
        for i, strike in enumerate(puts):
            option_price = put_prices[i]

            option_IV = gcalc.Put_IV(spot, strike, 0, tte, option_price)
            option_delta = gcalc.delta("PE", spot, strike, tte, option_IV, 0)
            put_deltas_and_ivs.append((option_delta, option_IV))

        
        min_diff = math.inf
        put_min_diff = None
        for i, (put_delta, put_iv) in enumerate(put_deltas_and_ivs):
            try:
                if abs(abs(put_delta) - delta) < min_diff:
                    min_diff = abs(abs(put_delta) - delta)
                    put_min_diff = puts[i]
            except Exception as e:
                pass
            pass

        # print(min_diff)

        min_diff = math.inf
        call_min_diff = None
        for i, (call_delta, call_iv) in enumerate(call_deltas_and_ivs):
            try:
                if abs(abs(call_delta) - delta) < min_diff:
                    min_diff = abs(abs(call_delta) - delta)
                    call_min_diff = calls[i]
            except Exception as e:
                pass
            pass
        
        # print(min_diff)
        return call_min_diff, put_min_diff

    '''
    ##########################
    Helper Functions
    ##########################
    '''

    def update_prices(self, spot):
        opts = self.straddle_distance_options(spot)
        self.aditional_instruments_to_track(opts)
        self.update_order_book_prices()
        pass
        

    def update_order_book_prices(self):
        keys = []
        options_list = []
        for key in self.orders:
            keys.append(key)
            options_list.append(self.orders[key])
            
        prices = self.MD._get_price(options_list, keys)
        
        for j in range(len(keys)):
            #print(j)
            if prices[j]=="XX":
                if keys[j][-2:]=="CE":
                    # prices[j]=self.MD.get_price_from_file(self.index+self.expiry+"FUT")-float(keys[j][:-2]) + self.MD.get_price_from_file(self.index+self.expiry+f'{keys[j][:-2]}PE')
                    prices[j]=self.close -float(keys[j][:-2]) + self.MD.get_price_from_file(self.index+self.expiry+f'{keys[j][:-2]}PE')
                elif keys[j][-2:]=="PE":
                    # prices[j]=-self.MD.get_price_from_file(self.index+self.expiry+"FUT")+float(keys[j][:-2]) + self.MD.get_price_from_file(self.index+self.expiry+f'{keys[j][:-2]}CE')
                    prices[j]=-self.close + float(keys[j][:-2]) + self.MD.get_price_from_file(self.index+self.expiry+f'{keys[j][:-2]}CE')
        
        for i,key in enumerate(keys):
            self.instrument_prices[key] = prices[i]

        pass

    def straddle_distance_options(self, spot):
        # atm options
        # straddle +
        # straddle -
        option_list = []

        straddle_price, spot_option =  self.atm_straddle_price(spot)
        straddle_price = int(round(straddle_price / float(self.movement))) * self.movement

        # option_list = [
        #     f'{spot_option}CE',
        #     f'{spot_option}PE',
        #     f'{spot_option+self.movement}CE',
        #     f'{spot_option-self.movement}PE',
        #     f'{spot_option+straddle_price}CE',
        #     f'{spot_option+straddle_price}PE',
        #     f'{spot_option-straddle_price}CE',
        #     f'{spot_option-straddle_price}PE',
        # ]

        return option_list
    
    def get_current_price(self, options_list):
        new_options = []
        prices = []
        for option in options_list:
            if option not in self.instrument_prices:
                new_options.append(option)
            else:
                prices.append(self.instrument_prices[option])
        
        if len(new_options) != 0:
            self.aditional_instruments_to_track(new_options)
            self.update_order_book_prices()
        else:
            # no new optins, all prices have been found, return
            return prices
        
        # in case new options are there
        prices = []
        for option in options_list:
            prices.append(self.instrument_prices[option])
        return prices
    
    def get_OI(self, options_list):

        ins_list = [self._get_option(option) for option in options_list]

        oi= self.MD._get_oi(ins_list)

        return oi
    

    def get_Volumes(self, options_list):

        ins_list = [self._get_option(option) for option in options_list]

        vol= self.MD._get_volumes(ins_list)

        return vol
    
    def get_IVs(self, spot, options_list):
        
        gcalc = Greeks()
        
        IVs = []

        ttm = self.timeToMaturity()

        prices = self.get_current_price(options_list)

        for i, option in enumerate(options_list):
            strike = int(option[:-2])
            option_type = option[-2:]

            IV = gcalc.IV(spot, strike, self.rfr, ttm, prices[i], option_type)

            IVs.append(IV)

        
        return IVs

    def aditional_instruments_to_track(self, options):
        """
        Add additional instruments to 
        self.orders to ensure their prices
        are also being tracked
        """
        spread_instruments = [self._get_option(option) for option in options]
        for i, ins in enumerate(spread_instruments):
            self.orders[options[i]] = ins
        pass

    def full_portfolio_size(self):
        total = 0
        for key in self.portfolio:
            total+= abs(self.portfolio[key])
        return total
    
    def number_of_calls(self):
        total = 0
        for key in self.portfolio:
            if key[-2:] == "CE":
                total+= abs(self.portfolio[key])
            else:
                continue
        return total
    
    def number_of_puts(self):
        total = 0
        for key in self.portfolio:
            if key[-2:] == "PE":
                total+= abs(self.portfolio[key])
            else:
                continue
        return total

    def zero_gamma_handler(self, numerator):
        return numerator

    def _get_call(self, strike):
        calls = self.instruments['options']['calls']
        for item in calls:
            if str(strike) in item['DisplayName']:
                return(item)
        pass

    def _get_put(self, strike):
        puts = self.instruments['options']['puts']
        # puts = sorted(puts, key=lambda x: x['DisplayName'])
        for item in puts:
            if str(strike) in item['DisplayName']:
                return(item)
        pass

    def get_n_otm_call_prices(self, spot_strike, n):
        strike_gap = self.movement
        # if self.timeToMaturity() > 10:
        #     n = 5
        #     spot_strike = math.ceil(spot_strike/500)*500
        #     strike_gap = 500

        calls = [*range(spot_strike, spot_strike+n*strike_gap, strike_gap)]
        calls_strs = list(map(lambda x : f"{x}CE", calls))
        print(calls_strs)
        prices = self.get_current_price(calls_strs)
        return calls, prices
    
    def get_n_otm_put_prices(self, spot_strike, n):
        strike_gap = self.movement
        
        # spot_strike = math.floor(spot_strike/500)*500
        # strike_gap = 500
        
        puts = [*range(spot_strike, spot_strike-n*strike_gap, -strike_gap)]
        puts_strs = list(map(lambda x : f"{x}PE", puts))
        prices = self.get_current_price(puts_strs)
        return puts, prices

    def get_n_call_prices(self, spot_strike, n, m):
        strike_gap = self.movement
        calls = [*range(spot_strike-m*strike_gap, spot_strike+n*strike_gap, strike_gap)]
        calls_strs = list(map(lambda x : f"{x}CE", calls))
        prices = self.get_current_price(calls_strs)
        return calls, prices
    
    def get_n_put_prices(self, spot_strike, n, m):
        strike_gap = self.movement
        puts = [*range(spot_strike+m*strike_gap, spot_strike-n*strike_gap, -strike_gap)]
        puts_strs = list(map(lambda x : f"{x}PE", puts))
        prices = self.get_current_price(puts_strs)
        return puts, prices
    
    def get_all_calls(self):
        calls = []
        ins = self.instruments['options']['calls']
        for item in ins:
            calls.append(item['DisplayName'])

    def get_all_puts(self):
        puts = []
        ins = self.instruments['options']['puts']
        for item in ins:
            puts.append(item['DisplayName'])

    def _get_option(self, option):

        if option in self.orders:
            return self.orders[option]
        
        if option[-2:] == "CE":
            ins = self.instruments['options']['calls']
        else:
            ins = self.instruments['options']['puts']

        strike = option[:-2]
        for item in ins:
            if strike in item['DisplayName']:
                self.orders[option] = item
                return(item)
        