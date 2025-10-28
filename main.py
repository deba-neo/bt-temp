from datetime import datetime
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
    smartstraddle,
    smart_expiry,
    delneutralspreads,
    risk,
)

import signal

import sys, os

import pika

class Logger(object):
    def __init__(self):
        self.terminal = sys.stdout
        self.log = open("logfile.log", "a")
        self.stdfileno = sys.stdout.fileno()
   
    def fileno(self):
        return self.stdfileno

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)  

    def flush(self):
        pass    

connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

channel.queue_declare(queue='hello')

sys.stdout = Logger()

strategy_config_file = "configs\strategyconfigs.yml"

with open(strategy_config_file, 'r') as f:
    strategy_configs = yaml.safe_load(f)

strategy_configs_backup = strategy_configs

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


strategy_mapper = {
    'straddle' : BaseStraddle,
    'deltagammav1' : delta_gamma.DeltaGammav1,
    'deltagammav2' : delta_gamma.DeltaGammav2,
    'deltagammav3' : delta_gamma.DeltaGammav3,
    'deltagammav4' : delta_gamma.DeltaGammav4,
    'rollingtheta' : delta_gamma.RollingThetaRetention,
}

strategy_mapper = {
    'ThetaGamma' : strategy.ThetaGamma,
    'StraddlebyThree' : strategy.StraddlebyThree,
    'ThetaGamma_HedgebyBuying' : strategy.ThetaGamma_HedgebyBuying,
    'StraddlebyThree_HedgebyBuying' : strategy.StraddlebyThree_HedgebyBuying,
    'Risk' : risk.Risk,

    'RollingStraddle' : rollingstraddle.RollingStraddle,
    'RollingStraddle_StraddlebyThree' : rollingstraddle.RollingStraddle_StraddlebyThree,
    'RollingStraddle_TG_STD3_2DTE' : rollingstraddle.RollingStraddle_TG_STD3_2DTE,
    'RollingStraddle_ATM' : rollingstraddle_atm.RollingStraddle_ATM,
    'RollingStraddle_ATM_StraddlebyThree' : rollingstraddle_atm.RollingStraddle_ATM_StraddlebyThree,
    'RollingStraddle_ATM_TG_STD3_2DTE' : rollingstraddle_atm.RollingStraddle_ATM_TG_STD3_2DTE,
    
    'smartstraddle': smartstraddle.SmartStraddle,
    'SmartStraddleNoExit' : smartstraddle.SmartStraddleNoExit,
    'SmartStraddlConservative' : smartstraddle.SmartStraddlConservative,
    'SmartStraddle_HedgebyBuying' : smartstraddle.SmartStraddle_HedgebyBuying,
    'SmartStraddle_Expiry': smart_expiry.SmartStraddle_Expiry,
    'SmartStraddle_Expiry_HedgebyBuying': smart_expiry.SmartStraddle_Expiry_HedgebyBuying,

    "DeltaNeutralBundle_ExecAlgo" : delneutralspreads.DeltaNeutralBundle_ExecAlgo,
}

rate = 5.64e-2/250
rate = 0
instrument_finder = MarketData(indices, dates)
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
        name = names[i]
    )
    # trader = Straddle(indices[i], dates[i], rate, tracker.get_instruments(i), order_placer, demands[i])
    traders.append(trader)


user_interface = UIManager(traders, strategy_mapper)

print("Ready")
while(datetime.now()
            < datetime.now().replace(hour=9, minute=15, second=10, microsecond=0)):
    pass




print("===================================================================", flush=True)
print("Setting Up...")
print(f"Time: {datetime.now().time().isoformat(timespec='milliseconds')}")
# get current spot
spot_price = tracker.current_spot()
for i in range(len(spot_price)):
    traders[i].set_up(spot_price[i], strategy_args[i]["position_exists"])










def exit_handler(signum, frame):
    os.write(sys.stdout.fileno(), b"Closing all positions....\n")
    # print('Closing all positions....', flush=True)
    for i in range(len(indices)):
        ret = traders[i].square_off_all(suppress_print=True)
        os.write(sys.stdout.fileno(), str.encode(ret + "\n"))
        pass
    exit(0)

signal.signal(signal.SIGINT, exit_handler)


def callback(method, properties, body):
    print(f" [x] Received Input")
    user_interface.config_reader(json.loads(body))
    print(" [x] Done")



while(True):
    print("===================================================================", flush=True)
    print(f"Time: {datetime.now().time().isoformat(timespec='milliseconds')}")
    # print(f"Current MTM :  {order_placer.get_current_mtm()}")
    
    # get current spot
    spot_price = tracker.current_spot()

    while(True):
        try:
            method, properties, body = channel.basic_get(queue='hello', auto_ack=True)
            if method == None:
                print("No New Data")
                break
            else:
                callback(method, properties, body)
            pass
        except Exception as e:
            print(e)
            pass



    for i in range(len(spot_price)):
        print("----------------------------------------------------------------", flush=True)
        print(f"{indices[i]} : {spot_price[i] :.2f}", flush=True)

        position = traders[i].monitor_and_trade(spot_price[i])
        
        # back up file
        strategy_configs_backup[i]['strategy_args'] = position
        with open(strategy_config_file, 'w') as f:
            yaml.dump(strategy_configs_backup, f)
        
        # print(f"Position: {position :.2f}", flush=True)

        # PnL = traders[i].PnL()
        # print(f"PnL: {PnL}")
    
    # position = straddle.adjust(spot_price)
    # print(f"Position: {position}")