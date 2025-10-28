import datetime
import yaml, json

from IndexTracker import IndexTracker
from BaseStraddle import BaseStraddle
from UImanager import UIManager
from XTConnect.APIWrapper import MarketData, Interaction

from strategies import delta_gamma
from strategies import strategy, policy

from strategies.custom import (
    rollingstraddle,
    rollingstraddle_atm,
    rollingstraddle_lhs,
    smartstraddle,
    rollingstrangle,
    gammalong,
    smart_expiry,
    spreads,
    std1_w3,
    strangle_lg,
    track_spreads,
    skew,
    gammashort,
    morningOTMs,
)

from strategies.straddle_variants import (
    timely_straddle,
    condor_hedged_by_wings,
    dynamic_5stage,
)

from strategies.gammalongstrats import (
    day_range,
    day_range_hedged,
)

from strategies.spread_variants import (
    twofivespreads,
    otmspreads,
)

import sys, os
import pandas as pd
import numpy as np

suppress_outputs = True

global_terminal = sys.stdout
class Logger(object):
    def __init__(self, filename):
        self.terminal = global_terminal
        self.log = open(filename, "a")
        self.suppress_all = suppress_outputs

    def write(self, message, ):
        if not self.suppress_all:
            self.terminal.write(message)
            self.log.write(message)
        else:
            pass

    def always_output(self, message):
        self.terminal.write(message)
        self.log.write(message)
        pass

    def flush(self):
        pass

def unified_strategy_mapping():
    strategy_mapper = {
        'ThetaGamma' : strategy.ThetaGamma,
        'StraddlebyThree' : strategy.StraddlebyThree,
        'ThetaGamma_HedgebyBuying' : strategy.ThetaGamma_HedgebyBuying,
        'StraddlebyThree_HedgebyBuying' : strategy.StraddlebyThree_HedgebyBuying,
        'TG_STD3_2DTE_HedgebyBuying' : strategy.TG_STD3_2DTE_HedgebyBuying,
        'ThetaGamma_HedgebyForwards' : strategy.ThetaGamma_HedgebyForwards,
        'StraddlebyThree_HedgebyForwards' : strategy.StraddlebyThree_HedgebyForwards,
        'TG_STD3_2DTE_HedgebyForwards' : strategy.TG_STD3_2DTE_HedgebyForwards,
        "TG_STD3_2DTE_Forwards_CutWings" : strategy.TG_STD3_2DTE_Forwards_CutWings,
        'ThetaGamma_DeltaWings' : strategy.ThetaGamma_DeltaWings,

        'RollingStraddle' : rollingstraddle.RollingStraddle,
        'RollingStraddle_StraddlebyThree' : rollingstraddle.RollingStraddle_StraddlebyThree,
        'RollingStraddle_TG_STD3_2DTE' : rollingstraddle.RollingStraddle_TG_STD3_2DTE,
        'RollingStraddle_NewHedge' : rollingstraddle.RollingStraddle_NewHedge,
        'RollingStraddle_ATM' : rollingstraddle_atm.RollingStraddle_ATM,
        'RollingStraddle_ATM_StraddlebyThree' : rollingstraddle_atm.RollingStraddle_ATM_StraddlebyThree,
        'RollingStraddle_ATM_TG_STD3_2DTE' : rollingstraddle_atm.RollingStraddle_ATM_TG_STD3_2DTE,
        'RollingStraddle_ATM_NewHedge' : rollingstraddle_atm.RollingStraddle_ATM_NewHedge,
        'RollingStraddle_LHS' : rollingstraddle_lhs.RollingStraddle_LHS,


        'RollingStrangle_TG_STD3_2DTE' : rollingstrangle.RollingStrangle_TG_STD3_2DTE,
        'RollingStrangle_FWD_TG_STD3_2DTE' : rollingstrangle.RollingStrangle_FWD_TG_STD3_2DTE,

        "MorningOTMs" : morningOTMs.MorningOTMs,
        "MorningOTMSpread" : morningOTMs.MorningOTMSpread,
        
        'Smartstraddle': smartstraddle.SmartStraddle,
        'SmartStraddleNoExit' : smartstraddle.SmartStraddleNoExit,
        'SmartStraddlConservative' : smartstraddle.SmartStraddlConservative,
        'SmartStraddle_HedgebyBuying' : smartstraddle.SmartStraddle_HedgebyBuying,
        'SmartStraddle_Expiry': smart_expiry.SmartStraddle_Expiry,
        'SmartStraddle_Expiry_HedgebyBuying': smart_expiry.SmartStraddle_Expiry_HedgebyBuying,
        'Dynamic5Stage': dynamic_5stage.Dynamic5Stage,

        "GammaLong" : gammalong.GammaLong,
        "GammaLong_DayEnd" : gammalong.GammaLong_DayEnd,
        "TwoLegSpread" : spreads.TwoLegSpread,
        "GammaShort_Hedged" : gammashort.GammaShort_Hedged,

        "STDWingRatio" : std1_w3.STDWingRatio,

        "OTMSpreads" : otmspreads.OTMSpreads,
        "OTMSpreads_FirstLegHedge" : otmspreads.OTMSpreads_FirstLegHedge,

        "Strangle_LG" : strangle_lg.Strangle_LG,

        "Dynamic_Ratio_Spreads" : track_spreads.Dynamic_Ratio_Spreads,
        "TwoFiveSpreads" : twofivespreads.TwoFiveSpreads,

        "Delta_Skew" : skew.Delta_Skew,

        "TimelyStraddle" : timely_straddle.TimelyStraddle,
        "Condor_with_Wings" : condor_hedged_by_wings.Condor_with_Wings,
        
        "GammaLong_ATR" : day_range.GammaLong_ATR,
        "GammaLong_ATR_Hedged" : day_range_hedged.GammaLong_ATR_Hedged,
        
    }
    return strategy_mapper

def run_one_day(day_file: pd.DataFrame, strategy_configs, date, starttime):
    indices = []
    dates = []
    initial_spots = []
    adjustments = []
    strategies = []
    strategy_args = []
    names = []
    for i in range(len(strategy_configs)):
        idx = strategy_configs[i]['index']
        indices.append(idx['Ticker'])
        dates.append(idx['Expiry'])
        initial_spots.append(idx['Init'])
        adjustments.append(idx['Adjustment'])
        strategies.append(strategy_configs[i]['strategy'])
        strategy_args.append(strategy_configs[i]['strategy_args'])
        names.append(strategy_configs[i]['name'])


    strategy_mapper = unified_strategy_mapping()

    rate = 5.64e-2 / 250
    rate = 0
    instrument_finder = MarketData(indices, dates)
    instrument_finder.set_current_time(day_file.keys()[0])
    instrument_finder.set_file(day_file)
    instrument_finder.set_current_date(date)

    order_placer = Interaction()

    tracker = IndexTracker(
        indices, dates, adjustments, rate, instrument_finder, initial_spots
    )


    traders : list[BaseStraddle] = []
    for i in range(len(indices)):
        # trader = strategy_mapper[strategies[i]](indices[i], dates[i], adjustments[i], rate, tracker.get_instruments(i), order_placer, strategy_args[i])
        trader = BaseStraddle(
            indices[i],
            dates[i],
            adjustments[i],
            rate,
            tracker.get_instruments(i),
            order_placer,
            strategy_args[i],
            strategy=strategy_mapper[strategies[i]](),
            policy=policy.DefaultPolicy(),
            name = strategies[i]
        )
        traders.append(trader)

    print("===================================================================", flush=True)
    print("Setting Up...")
    print(f"Time: {instrument_finder.current_time}")

    set_up = False
    # get current spot
    spot_price = tracker.current_spot()

    for time in day_file.keys():
        # Setting the current time across all data objects
        instrument_finder.set_current_time(time)

        print(
            "===================================================================",
            flush=True,
        )
        print(f"Time: {time}")
        # Logger.always_output(sys.stdout, f"Time: {time}\n")

        # get current spot
        spot_price = tracker.current_spot()

        t = instrument_finder.current_time
        h,m,s = starttime
        if instrument_finder.current_time < t.replace(hour=h, minute=m, second=s, microsecond=0):
            continue

        if not set_up:
            for i in range(len(spot_price)):
                traders[i].set_up(spot_price[i], strategy_args[i]["position_exists"])
            set_up = True
            get_initial_conditions = True


        for i in range(len(spot_price)):
            print(
                "----------------------------------------------------------------",
                flush=True,
            )
            print(f"{indices[i]} : {spot_price[i] :.2f}", flush=True)

            position = traders[i].monitor_and_trade(spot_price[i])
            # Logger.always_output(sys.stdout, f"PF : {traders[0].portfolio}\n")
            if get_initial_conditions:
                get_initial_conditions = False
                greeks = traders[0].get_portfolio_greeks(spot_price[0])
        #         Logger.always_output(sys.stdout, f"{greeks['portfolio_theta']}\n")
        

    transations = [traders[0].total_pnl, traders[0].buy_qty, traders[0].sell_qty, traders[0].buy_value, traders[0].sell_value, traders[0].total_lot_sizes_traded, traders[0].strategy_args["MaxPnl"], traders[0].strategy_args["MinPNL"], traders[0].total_pnl/strategy_configs[0]["strategy_args"]["demand"], strategy_configs[0]["strategy_args"]["demand"]]
    # Logger.always_output(sys.stdout, f"Avg Util : {sum(util)/len(util)}\n")   
    
    columns = ['Time', 'Spot', 'PnL', 'DTE', 'ATM IV', 'ATM Straddle', 'ATM Strike', 'Call OI', 'Put OI', 'Call Vol', 'Put Vol']

    df = pd.DataFrame(traders[0].strategy_args["DataStorage"], columns=columns)

    init =  int(round(spot_price[0] / float(traders[0].movement))) * traders[0].movement
    return init, transations, df

def run_one_night_position(day_file: pd.DataFrame, strategy_configs, date, starttime):
    indices = []
    dates = []
    initial_spots = []
    adjustments = []
    strategies = []
    strategy_args = []
    names = []
    for i in range(len(strategy_configs)):
        idx = strategy_configs[i]['index']
        indices.append(idx['Ticker'])
        dates.append(idx['Expiry'])
        initial_spots.append(idx['Init'])
        adjustments.append(idx['Adjustment'])
        strategies.append(strategy_configs[i]['strategy'])
        strategy_args.append(strategy_configs[i]['strategy_args'])
        names.append(strategy_configs[i]['name'])


    strategy_mapper = unified_strategy_mapping()

    rate = 5.64e-2 / 250
    rate = 0
    instrument_finder = MarketData(indices, dates)
    instrument_finder.set_current_time(day_file.keys()[0])
    instrument_finder.set_file(day_file)
    instrument_finder.set_current_date(date)

    order_placer = Interaction()

    tracker = IndexTracker(
        indices, dates, adjustments, rate, instrument_finder, initial_spots
    )


    traders : list[BaseStraddle] = []
    for i in range(len(indices)):
        trader = BaseStraddle(
            indices[i],
            dates[i],
            adjustments[i],
            rate,
            tracker.get_instruments(i),
            order_placer,
            strategy_args[i],
            strategy=strategy_mapper[strategies[i]](),
            policy=policy.DefaultPolicy(),
            name = names[i]
        )
        # trader = Straddle(indices[i], dates[i], rate, tracker.get_instruments(i), order_placer, demands[i])
        traders.append(trader)

    print("===================================================================", flush=True)
    print("Setting Up...")
    print(f"Time: {instrument_finder.current_time}")

    set_up = False
    # get current spot
    spot_price = tracker.current_spot()

    for time in day_file.keys():
        # Setting the current time across all data objects
        instrument_finder.set_current_time(time)

        print(
            "===================================================================",
            flush=True,
        )
        print(f"Time: {time}")

        # get current spot
        spot_price = tracker.current_spot()

        t = instrument_finder.current_time
        h,m,s = starttime
        if instrument_finder.current_time < t.replace(hour=h, minute=m, second=s, microsecond=0):
            continue

        if not set_up:
            for i in range(len(spot_price)):
                traders[i].set_up(spot_price[i], strategy_args[i]["position_exists"])
            set_up = True
            # get_initial_conditions = True


        for i in range(len(spot_price)):
            print(
                "----------------------------------------------------------------",
                flush=True,
            )
            print(f"{indices[i]} : {spot_price[i] :.2f}", flush=True)

            position = traders[i].monitor_and_trade(spot_price[i])
            # Logger.always_output(sys.stdout, f"PF : {traders[0].portfolio}\n")
            
            traders[0].pretty_print(traders[0].get_portfolio_greeks(spot_price[0]))
            transations = [0, traders[0].buy_qty, traders[0].sell_qty, traders[0].buy_value, traders[0].sell_value, traders[0].total_lot_sizes_traded]
            return traders[0].portfolio, traders[0].net_value - traders[0].total_pnl, transations


    transations = [traders[0].total_pnl, traders[0].buy_qty, traders[0].sell_qty, traders[0].buy_value, traders[0].sell_value, traders[0].total_lot_sizes_traded]
    # Logger.always_output(sys.stdout, f"Avg Util : {sum(util)/len(util)}\n")   
    init =  int(round(spot_price[0] / float(traders[0].movement))) * traders[0].movement
    return init, transations

def get_sizing(index, new_init):
    if index == "nif":
        ticker = "NIFTY"
        multiplier = 24000/new_init
        norm_quantity = 3100*multiplier
    if index == "bnnif":
        ticker = "BANKNIFTY"
        multiplier = 53000/new_init
        norm_quantity = 1250*multiplier
    if index == "fn":
        ticker = "FINNIFTY"
        multiplier = 23700/new_init
        norm_quantity = 2800*multiplier
    if index == "midc":
        ticker = "MIDCPNIFTY"
        multiplier = 12000/new_init
        norm_quantity = 6000*multiplier
    if index == "bsx":
        ticker = "SENSEX"
        multiplier = 75000/new_init
        norm_quantity = 1000*multiplier
    
    return ticker, norm_quantity

def backtest_dynamic_one_day(df, date, expiry, new_init, atr, adjustment, index, strat, starttime, endtime, excess_strat_args):
    ticker, norm_quantity = get_sizing(index, new_init)

    strats = [
        {
            "index": {
                "Ticker": ticker,
                "Expiry": expiry,
                "Init": new_init,
                "Adjustment": adjustment,
            },
            "strategy": strat,
            "name": "bnf1",
            "strategy_args": {
                "stop_loss": -200000,
                "previous_close" : new_init,
                "Average_ATR" : atr,
                "refIV": 0.13,
                "demand": norm_quantity,
                "wings": False if "Wings" not in strat else 2.5,
                "IVCalc": "Actual",
                "hedge_amount": 0.5,
                "target": "size",
                "size_target": norm_quantity*2,
                "position_size_limit" : 14400,
                "close_position_time" : endtime,
                "close_position": False,
                "decrease_position": False,
                "construction_lots_per_cycle": 10000 if "RollingStraddle" not in strat else 500,
                "destruction_lots_per_cycle": 10000 if "RollingStraddle" not in strat else 500,
                "quantity_limit": 5,
                "position_exists": False,
                # "stop_loss": -900000,
                "hedge_point_multiplier" : 1,
            },
        },
    ]

    strats[0]["strategy_args"].update(excess_strat_args)
    
    return run_one_day(df, strats, date, starttime)

def backtest_ON_position(df, date, expiry, new_init, atr, adjustment, index, strat, starttime, endtime, excess_strat_args):
    ticker, norm_quantity = get_sizing(index, new_init)

    strats = [
        {
            "index": {
                "Ticker": ticker,
                "Expiry": expiry,
                "Init": new_init,
                "Adjustment": adjustment,
            },
            "strategy": strat,
            "name": "bnf1",
            "strategy_args": {
                "stop_loss": -450000,
                "previous_close" : new_init,
                "Average_ATR" : atr,
                "refIV": 0.13,
                "demand": norm_quantity,
                "wings": False if "Wings" not in strat else 2.5,
                "IVCalc": "Actual",
                "hedge_amount": 0.5,
                "target": "size",
                "size_target": norm_quantity*2,
                "position_size_limit" : 14400,
                "close_position_time" : endtime,
                "close_position": False,
                "decrease_position": False,
                "construction_lots_per_cycle": 10000,
                "destruction_lots_per_cycle": 10000,
                "quantity_limit": 5,
                "position_exists": False,
                "hedge_point_multiplier" : 1,
            },
        },
    ]

    strats[0]["strategy_args"].update(excess_strat_args)
    
    return run_one_night_position(df, strats, date, starttime)

def get_index_specs(index, weekly, no_expiries):
    if index == "nif":
        rootdir = "//10.211.8.76/GFD MBM Data/GFD MBM Parquet Files/NIFTY"
        sheet_name = "Nifty 50"
        column = "Nifty"
    
    if index == "bnnif":
        rootdir = "//10.211.8.76/GFD MBM Data/GFD MBM Parquet Files/BANKNIFTY"
        sheet_name = "Nifty Bank"
        column = "Banknifty"
    
    if index == "fn":
        rootdir = "//10.211.8.76/GFD MBM Data/GFD MBM Parquet Files/FINNIFTY"
        sheet_name = "Nifty Financial Services"
        column = "Finnifty"

    if index == "midc":
        rootdir = "//10.211.8.76/GFD MBM Data/GFD MBM Parquet Files/MIDCPNIFTY"
        sheet_name = "Nifty Midcap Select"
        column = "Midcpnifty"

    if index == "bsx":
        rootdir = "//10.211.8.76/GFD MBM Data/GFD MBM Parquet Files BSE/SENSEX"
        sheet_name = "BSE SENSEX"
        column = "Sensex"

    if not no_expiries:
        if weekly:
            dictkey = "Current Week"
            adjustment_key = "Current Week Adjustment "
        else:
            dictkey = "Current Month"
            adjustment_key = "Current Month Adjustment"
    else:
        if weekly:
            dictkey = "Current Week Non-Expiry"
            adjustment_key = "Current Week Non-Expiry Adjustment"
        else:
            dictkey = "Current Month Non-Expiry"
            adjustment_key = "Current Month Non-Expiry Adjustment"
    
    return rootdir, sheet_name, column, dictkey, adjustment_key

def one_loop_ON(index, strategy, test_start_date, test_stop_date, new_init, starttime, endtime, weekly = True, excess_strat_args = {}, no_expiries = False, datafile = None):
    
    rootdir, sheet_name, column, dictkey, adjustment_key = get_index_specs(index, weekly, no_expiries)

    expiries_df = pd.read_excel(f"//10.211.8.76/GFD MBM Data/Auxiliary Data/Expiry File_2025.xlsx", sheet_name=sheet_name)
    index_historical_data = pd.read_excel("//10.211.8.76/GFD MBM Data/Auxiliary Data/Index Historical Data.xlsx", sheet_name = "Index Open Prices",index_col=0)

    from Greeks import Greeks
    g = Greeks()

    test_start_date = datetime.datetime.strptime(test_start_date, '%d-%m-%Y')
    test_stop_date = datetime.datetime.strptime(test_stop_date, '%d-%m-%Y')

    day_one = True

    import time
    t1 = time.time()
    util = []

    dates = []

    for subdir, dirs, files in os.walk(rootdir):
        for file in files:
            filepath = subdir + os.sep + file
            if filepath.endswith(".parquet"):
                day_file = filepath
                date = day_file[-18:-8]
                key = date
                d1 = datetime.datetime.strptime(date, '%d-%m-%Y')

                if d1 < test_start_date:
                    continue
                elif d1 > test_stop_date:
                    return new_init
                
                
                if len(dates) == 0:
                    dates.append(day_file)
                    continue
                

                prev_day_file = dates[-1]
                # print(prev_day_file)
                
                day_file_df = pd.read_parquet(day_file)
                prev_day_file_df = pd.read_parquet(prev_day_file)
                                
                dates.append(day_file)
                
                if datafile is not None:
                    try:
                        day_data = datafile.loc[date].to_dict()
                        excess_strat_args.update(day_data)
                    except Exception as e:
                        continue
                
                try:
                    expiry = expiries_df.loc[expiries_df ["Date"] == d1].reset_index()[dictkey][0]
                    expiry = datetime.datetime.strftime(expiry, '%d-%b-%y').upper()
                    adjustment = expiries_df.loc[expiries_df ["Date"] == d1].reset_index()[adjustment_key][0]
                except Exception as e:
                    # raise Exception
                    continue
                
                d2 = datetime.datetime.strptime(expiry, '%d-%b-%y')
                expiry = datetime.datetime.strftime(d2, '%d%b%y').upper()
                atr = 0

                try:
                    new_init = index_historical_data.loc[str(d1)[:10]][column]
                    print(new_init)
                except Exception as e:
                    new_init = new_init

                try:
                    # create portfolio
                    Position_Creation_Time = (15, 19, 0)
                    Return_time = "15:20:00"
                    additional_args = {
                        "wings" : False,
                        # "wings" : 2,
                        # "wing_delta" : 0.10,
                    }
                    ON_strategy = "TG_STD3_2DTE_HedgebyBuying"
                    # ON_strategy = "ThetaGamma_DeltaWings"
                    # ON_strategy = "RollingRiskRev"
                    
                    pf, pf_val, tr = backtest_ON_position(prev_day_file_df, prev_day_file[-18:-8], expiry, new_init, atr, adjustment, index, ON_strategy, Position_Creation_Time, Return_time, additional_args)

                    additional_args = {
                        "position_exists" : True,
                        "existing_pf" : pf,
                        'existing_pf_value' : pf_val,
                    }
                    additional_args.update(excess_strat_args)
                    new_init, transactions = backtest_dynamic_one_day(day_file_df, date, expiry, new_init, atr, adjustment, index, strategy, starttime, endtime, additional_args)

                    new_transations = []
                    for i in range(len(transactions)):
                        new_transations.append(transactions[i]+tr[i])
                    transactions = new_transations

                    total_string = ",".join(map(str, transactions))
                    Logger.always_output(sys.stdout, f"{date},{total_string}\n")
                except Exception as e:
                    # raise Exception
                    # Logger.always_output(sys.stdout, str(e))
                    continue
    
    t2 = time.time()

    return new_init
    pass

def one_loop_ID(index, strategy, test_start_date, test_stop_date, new_init, starttime, endtime, weekly = True, excess_strat_args = {}, no_expiries = False, datafile = None, only_expiries = False):
    
    rootdir, sheet_name, column, dictkey, adjustment_key = get_index_specs(index, weekly, no_expiries)

    expiries_df = pd.read_excel(f"//10.211.8.76/GFD MBM Data/Auxiliary Data/Expiry File_2025.xlsx", sheet_name=sheet_name)
    index_historical_data = pd.read_excel("//10.211.8.76/GFD MBM Data/Auxiliary Data/Index Historical Data.xlsx", sheet_name = "Index Open Prices",index_col=0)


    from Greeks import Greeks
    g = Greeks()

    test_start_date = datetime.datetime.strptime(test_start_date, '%d-%m-%Y')
    test_stop_date = datetime.datetime.strptime(test_stop_date, '%d-%m-%Y')

    day_one = True

    import time
    t1 = time.time()
    util = []

    dates = []

    df_list = []

    for subdir, dirs, files in os.walk(rootdir):
        for file in files:
            filepath = subdir + os.sep + file
            if filepath.endswith(".parquet"):
                day_file = filepath
                date = day_file[-18:-8]
                key = date
                d1 = datetime.datetime.strptime(date, '%d-%m-%Y')

                if d1 < test_start_date:
                    continue
                elif d1 > test_stop_date:
                    combined_df = pd.concat(df_list, ignore_index=True)
                    combined_df.to_csv(f"{strategy}-ID-Weekly-CombinedData.csv", index=False)
                    return new_init
                
                
                if len(dates) == 0:
                    dates.append(day_file)
                    continue
                

                prev_day_file = dates[-1]
                # print(prev_day_file)
                
                day_file_df = pd.read_parquet(day_file)
                prev_day_file_df = pd.read_parquet(prev_day_file)
                                
                dates.append(day_file)
                
                if datafile is not None:
                    try:
                        day_data = datafile.loc[date].to_dict()
                        excess_strat_args.update(day_data)
                    except Exception as e:
                        continue
                
                try:
                    expiry = expiries_df.loc[expiries_df ["Date"] == d1].reset_index()[dictkey][0]
                    # expiry = df.loc[df ["Date"] == d1].reset_index()["Finnifty Weekly Expiry"][0].upper()
                    expiry = datetime.datetime.strftime(expiry, '%d-%b-%y').upper()
                    adjustment = expiries_df.loc[expiries_df ["Date"] == d1].reset_index()[adjustment_key][0]
                    # print(adjustment)
                except Exception as e:
                    # raise Exception
                    continue
                
                d2 = datetime.datetime.strptime(expiry, '%d-%b-%y')
                expiry = datetime.datetime.strftime(d2, '%d%b%y').upper()

                if only_expiries and d1 != d2:
                    continue

                atr = 0

                try:
                    new_init = index_historical_data.loc[str(d1)[:10]][column]
                except Exception as e:
                    new_init = new_init


                try:
                    new_init, transactions, df = backtest_dynamic_one_day(day_file_df, date, expiry, new_init, atr, adjustment, index, strategy, starttime, endtime, excess_strat_args)
                    total_string = ",".join(map(str, transactions))
                    Logger.always_output(sys.stdout, f"{date},{total_string}\n")

                    df_list.append(df)
                
                except Exception as e:
                    # raise Exception
                    Logger.always_output(sys.stdout, str(e))
                    continue
    t2 = time.time()

    combined_df = pd.concat(df_list, ignore_index=True)
    combined_df.to_csv(f"{strategy}-ID-Weekly-CombinedData.csv", index=False)
    return new_init
    pass


if __name__ == "__main__":
    # '%d-%m-%Y' format
    # example: 01-01-2022

    test_stop_date = "31-12-2025"

    strategies = ["TG_STD3_2DTE_HedgebyBuying"]
    # strategies = ["TG_STD3_2DTE_Forwards_CutWings"]
    # strategies = ["RollingRiskRev"]
    strategies = ["TG_STD3_2DTE_HedgebyForwards"]
    

    starttime = (9,16,0)
    endtime = "15:25:00"

    test_start_date = "01-04-2019"

    new_init = 80000

    '''
    Intraday Data Gen
    '''
    # strategies = ["OTMSpreads"]
    # strategies = ["OTMSpreads_FirstLegHedge"]

    # excess_strat_args = {
    #     "stop_loss": -75000,
    #     "option_type" : "CE",
    # }

    # for strat in strategies:
    #     sys.stdout = Logger(f"{strat}-ID-Weekly-CE-nf.csv")
    #     Logger.always_output(sys.stdout, "Date, PnL, Buy Quantity, Sell Quantity, Buy Value, Sell Value, Total Lots\n")
    #     one_loop_ID("nif", strat, test_start_date, test_stop_date, new_init, starttime, endtime, weekly=True, excess_strat_args=excess_strat_args)

    # excess_strat_args = {
    #     "stop_loss": -75000,
    #     "option_type" : "PE",
    # }

    # for strat in strategies:
    #     sys.stdout = Logger(f"{strat}-ID-Weekly-PE-nf.csv")
    #     Logger.always_output(sys.stdout, "Date, PnL, Buy Quantity, Sell Quantity, Buy Value, Sell Value, Total Lots\n")
    #     one_loop_ID("nif", strat, test_start_date, test_stop_date, new_init, starttime, endtime, weekly=True, excess_strat_args=excess_strat_args)

    # exit(0)

    # strategies = ["TG_STD3_2DTE_HedgebyForwards"]   

    # strategies = ["GammaLong_ATR"]
    # excess_strat_args = {
    #     "stop_loss": -100000,
    #     "Kind" : "d",
    #     "Exit_Dist" : 0.33,
    #     "Range_Multiplier" : 0.8,
    #     "Exit_Condition" : "Entry"
    # }

    # test_start_date = "01-03-2019"
    # strategies = ["TG_STD3_2DTE_HedgebyForwards"]   
    # strategies = ["RollingStraddle_TG_STD3_2DTE"]
    # excess_strat_args = {
    #     "stop_loss": -20000000,
    # }

    # rat_list = ["CE_1", "CE_2", "CE_3", "PE_1", "PE_2", "PE_3"]
    # df_data = pd.read_parquet('df_swapped.parquet')

    strategies = ["MorningOTMs"]
    strategies = ["MorningOTMSpread"]

    excess_strat_args = {
        "stop_loss": -90000000,
    }

    # test_start_date = "05-05-2020"
    # # test_start_date = "01-01-2025"
    # test_stop_date = "05-12-2025"

    
    # for strat in strategies:
    #     sys.stdout = Logger(f"{strat}-ID-Weekly-nf.csv")
    #     Logger.always_output(sys.stdout, "Date, PnL, Buy Quantity, Sell Quantity, Buy Value, Sell Value, Total Lots, MaxPNL, MinPNL\n")
    #     one_loop_ID("nif", strat, test_start_date, test_stop_date, new_init, starttime, endtime, weekly=True, excess_strat_args=excess_strat_args, only_expiries=True)

    # for strat in strategies:
    #     sys.stdout = Logger(f"{strat}-ID-Weekly-bsx.csv")
    #     Logger.always_output(sys.stdout, "Date, PnL, Buy Quantity, Sell Quantity, Buy Value, Sell Value, Total Lots, MaxPNL, MinPNL\n")
    #     one_loop_ID("bsx", strat, test_start_date, test_stop_date, new_init, starttime, endtime, weekly=True, excess_strat_args=excess_strat_args, only_expiries=True)

    # exit(0)

    # #1
    strategies = ["TimelyStraddle"]
    excess_strat_args = {
        "stop_loss": -600000,
        "profit_book" : 300000,
    }

    # #2
    strategies = ["RollingStrangle_TG_STD3_2DTE"]
    excess_strat_args = {
        "stop_loss": -10000000,
        "profit_book" : 7500000,
    }

    strategies = ["TG_STD3_2DTE_HedgebyForwards"]
    excess_strat_args = {
        "stop_loss": -15000000,
        # "profit_book" : 7500000,
    }

    # # #3
    # strategies = ["RollingStrangle_FWD_TG_STD3_2DTE"]
    # excess_strat_args = {
    #     "stop_loss": -100000,
    #     "profit_book" : 75000,
    # }

    # strategies = ["RollingStrangle_TG_STD3_2DTE", "RollingStrangle_FWD_TG_STD3_2DTE"]

    # #4
    # strategies = ["GammaLong_ATR"]
    # excess_strat_args = {
    #     "stop_loss": -400000,
    #     "Range_Multiplier" : 0.8,
    #     "Kind" : "d",
    #     "Exit_Condition" : "Entry",
    #     "Exit_Dist" : 0.33,
    # }



    test_start_date = "01-02-2019"
    # test_start_date = "01-01-2025"
    test_stop_date = "05-12-2025"

    test_start_date = "29-01-2025"
    test_stop_date = "01-02-2025"

    
    for strat in strategies:
        sys.stdout = Logger(f"{strat}-ID-Weekly-nf.csv")
        Logger.always_output(sys.stdout, "Date, PnL, Buy Quantity, Sell Quantity, Buy Value, Sell Value, Total Lots, MaxPNL, MinPNL, Points, Qty\n")
        one_loop_ID("nif", strat, test_start_date, test_stop_date, new_init, starttime, endtime, weekly=True, excess_strat_args=excess_strat_args)

    # for strat in strategies:
    #     sys.stdout = Logger(f"{strat}-ID-Weekly-bsx.csv")
    #     Logger.always_output(sys.stdout, "Date, PnL, Buy Quantity, Sell Quantity, Buy Value, Sell Value, Total Lots, MaxPNL, MinPNL\n")
    #     one_loop_ID("bsx", strat, test_start_date, test_stop_date, new_init, starttime, endtime, weekly=True, excess_strat_args=excess_strat_args)

    # for strat in strategies:
    #     sys.stdout = Logger(f"{strat}-ID-Monthly-bnf.csv")
    #     Logger.always_output(sys.stdout, "Date, PnL, Buy Quantity, Sell Quantity, Buy Value, Sell Value, Total Lots, MaxPNL, MinPNL\n")
    #     one_loop_ID("bnnif", strat, test_start_date, test_stop_date, new_init, starttime, endtime, weekly=False, excess_strat_args=excess_strat_args)

    # for strat in strategies:
    #     sys.stdout = Logger(f"{strat}-ID-Monthly-nf.csv")
    #     Logger.always_output(sys.stdout, "Date, PnL, Buy Quantity, Sell Quantity, Buy Value, Sell Value, Total Lots, MaxPNL, MinPNL\n")
    #     one_loop_ID("nif", strat, test_start_date, test_stop_date, new_init, starttime, endtime, weekly=False, excess_strat_args=excess_strat_args)


    # for strat in strategies:
    #     sys.stdout = Logger(f"ID-Monthly-midc.csv")
    #     Logger.always_output(sys.stdout, "Date, PnL, Buy Quantity, Sell Quantity, Buy Value, Sell Value, Total Lots, MaxPNL, MinPNL\n")
    #     one_loop_ID("midc", strat, test_start_date, test_stop_date, new_init, starttime, endtime, weekly=False, excess_strat_args=excess_strat_args)


    '''
    Overnight Data Gen
    '''

    # for strat in strategies:
    #     sys.stdout = Logger(f"ON-Weekly-nf.csv")
    #     Logger.always_output(sys.stdout, "Date, PnL, Buy Quantity, Sell Quantity, Buy Value, Sell Value, Total Lots, MaxPNL, MinPNL\n")
    #     one_loop_ON("nif", strat, test_start_date, test_stop_date, new_init, starttime, endtime, weekly=True, excess_strat_args=excess_strat_args)

    # for strat in strategies:
    #     sys.stdout = Logger(f"ON-Weekly-bsx.csv")
    #     Logger.always_output(sys.stdout, "Date, PnL, Buy Quantity, Sell Quantity, Buy Value, Sell Value, Total Lots, MaxPNL, MinPNL\n")
    #     one_loop_ON("bsx", strat, test_start_date, test_stop_date, new_init, starttime, endtime, weekly=True, excess_strat_args=excess_strat_args)

    # for strat in strategies:
    #     sys.stdout = Logger(f"ON-Monthly-bnf.csv")
    #     Logger.always_output(sys.stdout, "Date, PnL, Buy Quantity, Sell Quantity, Buy Value, Sell Value, Total Lots, MaxPNL, MinPNL\n")
    #     one_loop_ON("bnnif", strat, test_start_date, test_stop_date, new_init, starttime, endtime, weekly=False, excess_strat_args=excess_strat_args)

    # for strat in strategies:
    #     sys.stdout = Logger(f"ON-Monthly-midc.csv")
    #     Logger.always_output(sys.stdout, "Date, PnL, Buy Quantity, Sell Quantity, Buy Value, Sell Value, Total Lots, MaxPNL, MinPNL\n")
    #     one_loop_ON("midc", strat, test_start_date, test_stop_date, new_init, starttime, endtime, weekly=False, excess_strat_args=excess_strat_args)

    

    
       
    