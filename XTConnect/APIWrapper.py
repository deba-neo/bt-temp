# from XTConnect.Connect import XTSConnect
import time
from datetime import datetime, timedelta
import json
import requests

from decimal import Decimal
import warnings
import yaml

import pandas as pd

import math

import re
import csv
from pathlib import Path
from typing import List, Any

# takes index and returns relevant information
class MarketData():
    
    data_file : pd.DataFrame = None
    current_date = None
    current_time = None
    instruments = None
    
    
    def __init__(self, indices, dates) -> None:

        self.indices = indices
        self.dates = dates
        pass

    @staticmethod
    def set_current_time(ctime):
        MarketData.current_time = ctime

    @staticmethod
    def set_file(file):
        MarketData.data_file = file

    @staticmethod
    def set_current_date(date):
        MarketData.current_date = date

    def get_instruments(self):
        if self.instruments == None:
            self.instruments = self._find_all_instruments()
        return self.instruments
        # make

    def _find_all_instruments(self):
        all_instruments = []
        for i,index in enumerate(self.indices):
            ins = self._findinstruments(index, self.dates[i])
            all_instruments.append(ins)

        return all_instruments
    
    def _findinstruments(self, index, date):
        ins = {
            "options" : self._options(index, date),
            "futures" : self._futures(index, date)
        }
        return ins

    def _futures(self, index, date):
        # date = self.date
        # print(date)
        # date = "23JUN"
        futures = []
        keys = ['DisplayName', 'ExchangeInstrumentID', 'InstrumentID', 'ExchangeSegment']

        df = self.data_file
        intruments = df[df.keys()[0]].keys()

        for ins in intruments:
            if "FUT" in ins:
                d = {k:0 for k in keys}
                d['DisplayName'] = ins
                futures.append(ins)

        return futures

    def _options(self, index, date):
        # date = self.date
        calls = []
        puts = []
        keys = ['DisplayName', 'ExchangeInstrumentID', 'InstrumentID', 'ExchangeSegment']

        df = self.data_file
        intruments = df[df.keys()[0]].keys()
        
        for ins in intruments:
            if date in ins and "PE" in ins:
                d = {k:0 for k in keys}
                d['DisplayName'] = ins
                puts.append(d)
                continue
            if date in ins and "CE" in ins:
                d = {k:0 for k in keys}
                d['DisplayName'] = ins
                calls.append(d)
                continue
        
        if len(calls) == 0:
            raise Exception(f"\nInvalid Inputs: {index}, {date}")
        
        return {
            'calls' : calls,
            'puts' : puts,
        }
    
    def _get_price(self, instruments, keys=None):
        """
        Get list of bids and asks.
        Takes instruments list containing as input

        Parameters
        ----------
        instruments: list[dict]
            dictionary must contain keys:
                - ExchangeSegment
                - ExchangeInstrumentID
            Throws key error if these two are missing

        Returns
        -------
        list[float]
            List of prices

        """
        if len(instruments) == 0:
            return []
        
        price_list = []

        # print(instruments)
        for i in range(len(instruments)):
            # print(ins)
            # if ins == None:
            #     price = math.nan
            # else:
            if instruments[i]!=None:
                price = self.get_price_from_file(instruments[i]['DisplayName'])
                #print("get prices",ins['DisplayName'],price)
                price_list.append(price)
            elif instruments[i]==None:
                if "FUT" in keys[i]:
                    price=self.get_price_from_file(self.get_expiry(self._futures()))
                else:
                    price="XX"
                price_list.append(price)
            pass
            # price = self.get_price_from_file(ins['DisplayName'])
            
            # price_list.append(price)
            pass
        
        # print(price_list)
        return price_list
    
    def get_expiry(date_list):
        def parse_date(date_str):
            return datetime.strptime(date_str[-10:-3], '%d%b%y')
        sorted_dates = sorted(date_list, key=parse_date)
        return sorted_dates[0]
    
    def _get_oi(self, instruments):
        if len(instruments) == 0:
            return []
                
        oi_list = []

        for ins in instruments:
            # print(ins)
            price = self.get_oi_from_file(ins['DisplayName'])
            oi_list.append(price)
            pass

        return oi_list
    
    def _get_volumes(self, instruments):
        if len(instruments) == 0:
            return []
                
        volume_list = []

        for ins in instruments:
            # print(ins)
            price = self.get_volume_from_file(ins['DisplayName'])
            volume_list.append(price)
            pass

        return volume_list
    
    def get_price_from_file(self, instrument_name):
        # print(instrument_name)
        data = self.data_file[self.current_time][instrument_name]
        required_data = (data[0] + data[1] + data[2] + data[3])/4
        return float(required_data)
        pass

    def get_oi_from_file(self, instrument_name):
        # print(instrument_name)
        data = self.data_file[self.current_time][instrument_name]

        required_data = data[5]
        
        return float(required_data)
        pass

    def get_volume_from_file(self, instrument_name):
        data = self.data_file[self.current_time][instrument_name]

        required_data = data[4]
        
        return float(required_data)
        pass
    

class Interaction():    
    pass
        
    def __init__(self) -> None:
        pass
        
        pass

    def place_order(self, instrument, sell, ouid, QUANTITY):
        # Default order configuration is limit orders,
        # config needs to be changed in code to send market orders 
        # configuration_ = "Market"
        pass
    
    def modify_order(
        self,
        order_ID: int,
        unique_ID: str,
        QUANTITY: int,
        orderType: str = "M",
        order_price: float = 0,
    ):
        pass
    
    def confirm_order_statuses(self, order_id_list: list, order_id_to_opt: dict, index, expiry, name):
        
        complete_list = []
        incomplete_list = order_id_list.copy()

        while True:
            num_left = len(incomplete_list)
            count = 0

            order_book  = self.get_order_book()
            for order in order_book:
                if order["AppOrderID"] in incomplete_list:
                    count += 1
                    if order["OrderStatus"] == "Filled":
                        incomplete_list.remove(order["AppOrderID"])
                        complete_list.append(order["AppOrderID"])
                    elif order["OrderStatus"] == "Rejected":
                        warnings.warn(f"Rejected Order : {order['CancelRejectReason']}")
                        # resend order
                        pass
                    pass
                
                if count == num_left:
                    break
            if count != num_left:
                warnings.warn("Missing orders")
            
            if len(incomplete_list) == 0:
                break

            time.sleep(1)
        
        pass
        pass


    def log_orders(
        self,
        options: List[Any],
        sell: List[Any],
        quantities: List[Any],
        current_time: Any,
        index: Any,
        expiry: Any,
        name: str,
    ) -> None:
        """
        Append order rows to a CSV named `<name>_<index>_orders.csv`.

        Columns: time, index, expiry, option, side, quantity
        - Creates file and header if it doesn't exist.
        - Validates equal-length list inputs (options/sell/quantities).
        - Uses `self.order_log_dir` as directory if present, else current dir.
        """
        # Choose directory
        base_dir = Path(getattr(self, "order_log_dir", "."))
        base_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize components
        def sanitize(s: str) -> str:
            return re.sub(r"[^A-Za-z0-9._-]+", "_", s).strip("_")

        safe_name = sanitize(Path(name).stem) or "orders"
        safe_index = sanitize(str(index)) or "index"

        # Build filename: <name>_<index>_orders.csv
        base = f"{safe_name}_{safe_index}"
        if not base.lower().endswith("_orders"):
            base = f"{base}_orders"
        path = base_dir / f"{base}.csv"

        # Validate inputs
        if not (len(options) == len(sell) == len(quantities)):
            raise ValueError(
                f"Length mismatch: options={len(options)}, sell={len(sell)}, quantities={len(quantities)}"
            )

        file_exists = path.exists()

        with path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["time", "index", "expiry", "option", "side", "quantity"])

            for opt, side, qty in zip(options, sell, quantities):
                side_str = ("SELL" if side else "BUY") if isinstance(side, bool) else side
                writer.writerow([current_time, index, expiry, opt, side_str, qty])


    
    def get_order_book(self) -> list[dict]:
        pass
    def handle_token_error(self):
        pass