# from XTConnect.Connect import XTSConnect
import math
from XTConnect import APIWrapper
import datetime
import yaml

class IndexTracker():
    

    def __init__(self, indices, expiries, adjustments, rate, Ins_Find, initial_spots) -> None:
        self.indices = indices
        self.expiries = expiries
        self.adjustments = adjustments
        self.rate = rate
        self.spots = initial_spots
        self.n = len(indices)

        self.helper = Ins_Find
        self.instruments = self.helper.get_instruments()
        # print('here')
        # print(self.instruments)

        index_config_file = "configs\index_configs.yml"

        with open(index_config_file, 'r') as f:
            index_configs = yaml.safe_load(f)

        self.strike_gaps = [index_configs[index]['movement'] for index in indices]

        pass

    def current_spot(self):
        # closest future
        # fut = self._get_closest_future()
        # fut = self.instruments['futures']
        
        # if len(fut) == 0:
        #     if self.spot == None:
        #         strikeprice = 43700
        #     else:
        #         strikeprice = self.spot
        # else:
        # # works for single future search only
        #     fut = fut[0]
        #     fprice = self.helper._get_price(fut)
        #     strikeprice = fprice

        strikeprices = self.spots
        
        # round off
        # strikeprice = int(math.ceil(strikeprice / 100.0)) * 100

        strikeprices = [
            int(math.ceil(strikeprice / self.strike_gaps[i])) * self.strike_gaps[i]
            for i, strikeprice in enumerate(strikeprices)
        ]
        
        # print(strikeprices)

        calls = self._get_calls(strikeprices)
        puts = self._get_puts(strikeprices)
        options = puts
        options.extend(calls)
        option_prices = self.helper._get_price(options)
        
        # while True:
        #     try:
        #         strikeprices = list(strikeprices)
        #         # print(f"Strike : {strikeprices[0]}")

        #         calls = self._get_calls(strikeprices)
        #         puts = self._get_puts(strikeprices)
        #         options = puts
        #         options.extend(calls)
                
        #         option_prices = self.helper._get_price(options)
        #         break
            
        #     except Exception as e:
        #         strikeprices = map(lambda x: x+100, strikeprices)
        #         pass

        # print(fut)
        # print(call)
        # print(put)
        
        # cprice = self.helper._get_price(call)
        # pprice = self.helper._get_price(put)

        # print(strikeprice)
        # print(cprice)
        # print(pprice)
        
        spots = []
        for i in range(self.n):
            strikeprice = strikeprices[i]
            pprice = option_prices[i]
            cprice = option_prices[self.n + i]
            sp = self._put_call_parity(pprice, cprice, strikeprice, self.expiries[i], self.adjustments[i])
            spots.append(sp)

        self.spots = spots
        return spots

    def get_instruments(self, idx):
        return self.instruments[idx]
    
    def _put_call_parity(self, put, call, strike, expiry, adjustment):
        # time = self.ttm(expiry, adjustment)
        return strike + call - put

    def ttm(self, expiry, adjustment):
        date_str = expiry
        # date_str +='23'     # Year, needs to be set
        exp1 = datetime.datetime.strptime(date_str, '%d%b%Y')
        expiry_date = exp1.strftime('%d-%m-%y')
        t1 = datetime.datetime.now().date()
        t2 = datetime.datetime.strptime(expiry_date, "%d-%m-%y").date()
        t3 = datetime.datetime.now().time()
        t4 = datetime.time(15, 30, 0)
        ttm = (t2 - t1).days
        
        # Adjusting for holidays and weekends
        ttm -= adjustment

        if (datetime.datetime.combine(datetime.date.min, t4) - datetime.datetime.combine(datetime.date.min, t3)).total_seconds() > 0:
            ttm += (datetime.datetime.combine(datetime.date.min, t4) - datetime.datetime.combine(datetime.date.min, t3)).total_seconds() / 22500
        return ttm

    def _get_closest_future():
        pass

    def _get_calls(self, strikeprices):
        calls = []
        for i in range(self.n):
            lis = self.instruments[i]['options']['calls']
            calls.append(self._get_opt(strikeprices[i], lis))
            pass
        return calls
    
    def _get_puts(self, strikeprices):
        puts = []
        for i in range(self.n):
            lis = self.instruments[i]['options']['puts']
            puts.append(self._get_opt(strikeprices[i], lis))
            pass
        # print(self.instruments[0]['options']['puts'])
        return puts

    def _get_opt(self, strike, calls):
        for item in calls:
            if f"{strike}PE" in item['DisplayName'] or f"{strike}CE" in item['DisplayName']:
                return(item)
        pass

    # def _get_put(self, strike):
    #     puts = self.instruments['options']['puts']
    #     for item in puts:
    #         if str(strike) in item['DisplayName']:
    #             return(item)
    #     pass

