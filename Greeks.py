import math
import numpy as np
import scipy as sq


from scipy.special import ndtr
from scipy.stats import norm

class Greeks():
    def __init__(self) -> None:
        pass

    #Calculating d1 in BS
    def dOne(self, stockPrice, strikePrice, timeToMaturity, volatility, riskFreeRate):
        return (math.log(stockPrice/strikePrice) + ((riskFreeRate + math.pow(volatility,2)/2)*timeToMaturity/365)) / (volatility*math.sqrt(timeToMaturity/365))

    #Calculating d2 in BS
    def dTwo(self, dOne, timeToMaturity, volatility):
        return dOne - volatility*math.sqrt(timeToMaturity/365)

    #Calculating theoretical Call Price in BS
    def Call_BS_Value(self, stockPrice, strikePrice, riskFreeRate, timeToMaturity, volatility):
        d1 = self.dOne(stockPrice, strikePrice, timeToMaturity, volatility, riskFreeRate)
        d2 = self.dTwo(d1, timeToMaturity, volatility)
        return stockPrice * ndtr(d1) - strikePrice * math.exp(-riskFreeRate * timeToMaturity) * ndtr(d2)

    #Calculating theoretical Put Price in BS
    def Put_BS_Value(self, stockPrice, strikePrice, riskFreeRate, timeToMaturity, volatility):
        d1 = self.dOne(stockPrice, strikePrice, timeToMaturity, volatility, riskFreeRate)
        d2 = self.dTwo(d1, timeToMaturity, volatility)
        return strikePrice * np.exp(-riskFreeRate * timeToMaturity) * ndtr(-d2) - stockPrice * ndtr(-d1)

    #Helper function to calculate Call IV - Calculates difference between current market call price and theoretical call price
    def Call_IV_Obj_Function(self, stockPrice, strikePrice, riskFreeRate, timeToMaturity, volatility, Call_Price):
        return Call_Price - self.Call_BS_Value(stockPrice, strikePrice, riskFreeRate, timeToMaturity, volatility)

    #Helper function to calculate Put IV - Calculates difference between current market put price and theoretical put price
    def Put_IV_Obj_Function(self, stockPrice, strikePrice, riskFreeRate, timeToMaturity, volatility, Put_Price):
        return Put_Price - self.Put_BS_Value(stockPrice, strikePrice, riskFreeRate, timeToMaturity, volatility)

    #Calculating Call IV through Brent method
    def Call_IV(self, stockPrice, strikePrice, riskFreeRate, timeToMaturity, Call_Price, a=-2, b=2, xtol=0.000001):
        def fcn(volatility):
            return self.Call_IV_Obj_Function(stockPrice, strikePrice, riskFreeRate, timeToMaturity, volatility, Call_Price)
        
        try:
            result = sq.optimize.brentq(fcn, a=a, b=b, xtol=xtol)
            return np.nan if result <= xtol else result
        except ValueError:
            return np.nan

    #Calculating Put IV through Brent method
    def Put_IV(self, stockPrice, strikePrice, riskFreeRate, timeToMaturity, Put_Price, a=-2, b=2, xtol=0.000001):
        def fcn(volatility):
            return self.Put_IV_Obj_Function(stockPrice, strikePrice, riskFreeRate, timeToMaturity, volatility, Put_Price)

        try:
            result = sq.optimize.brentq(fcn, a=a, b=b, xtol=xtol)
            return np.nan if result <= xtol else result
        except ValueError:
            return np.nan
    
    def IV(self, stockPrice, strikePrice, riskFreeRate, timeToMaturity, Price, Option_Type, a=-2, b=2, xtol=0.000001):
        if Option_Type == "CE":
            return self.Call_IV(stockPrice, strikePrice, riskFreeRate, timeToMaturity, Price, a, b, xtol)
        else:
            return self.Put_IV(stockPrice, strikePrice, riskFreeRate, timeToMaturity, Price, a, b, xtol)
    
    #Calculating Delta of an Option
    def delta(self, type, stockPrice, strikePrice, timeToMaturity, volatility, riskFreeRate):
        if(type == 'CE'):
            return ndtr(self.dOne(stockPrice, strikePrice, timeToMaturity, volatility, riskFreeRate))
        else:
            return ndtr(self.dOne(stockPrice, strikePrice, timeToMaturity, volatility, riskFreeRate)) - 1

    #Calculating Gamma of an Option
    def gamma(self, type, stockPrice, strikePrice, timeToMaturity, volatility, riskFreeRate):
            return (norm.pdf(self.dOne(stockPrice, strikePrice, timeToMaturity, volatility, riskFreeRate)))/(stockPrice*volatility*math.sqrt(timeToMaturity/365))

    #Calculating Theta of an Option
    def theta(self, type, stockPrice, strikePrice, timeToMaturity, volatility, riskFreeRate):
        if(type == 'CE'):
            return ((stockPrice*(norm.pdf(self.dOne(stockPrice, strikePrice, timeToMaturity, volatility, riskFreeRate)))*(volatility)*(-1))/(2*(math.sqrt(timeToMaturity/365))) - riskFreeRate*strikePrice*(math.exp(-1*timeToMaturity/365*riskFreeRate))*ndtr(self.dTwo(self.dOne(stockPrice, strikePrice, timeToMaturity, volatility, riskFreeRate), timeToMaturity, volatility)))/365
        else:
            return ((stockPrice*(norm.pdf(self.dOne(stockPrice, strikePrice, timeToMaturity, volatility, riskFreeRate)))*(volatility)*(-1))/(2*(math.sqrt(timeToMaturity/365))) + riskFreeRate*strikePrice*(math.exp(-1*timeToMaturity/365*riskFreeRate))*ndtr(-self.dTwo(self.dOne(stockPrice, strikePrice, timeToMaturity, volatility, riskFreeRate), timeToMaturity, volatility)))/365       

    #Calculating Vega of an Option
    def vega(self, type, stockPrice, strikePrice, timeToMaturity, volatility, riskFreeRate):
            return (stockPrice*(norm.pdf(self.dOne(stockPrice, strikePrice, timeToMaturity, volatility, riskFreeRate)))*math.sqrt(timeToMaturity/365))/100

    #Calculating Rho of an Option
    def rho(self, type, stockPrice, strikePrice, timeToMaturity, volatility, riskFreeRate):
        if(type == 'CE'):
            return (strikePrice*timeToMaturity/365*(math.exp(-1*timeToMaturity/365*riskFreeRate))*ndtr(self.dTwo(self.dOne(stockPrice, strikePrice, timeToMaturity, volatility, riskFreeRate), timeToMaturity, volatility)))/100
        else:
            return (-strikePrice*timeToMaturity/365*(math.exp(-1*timeToMaturity/365*riskFreeRate))*ndtr(-self.dTwo(self.dOne(stockPrice, strikePrice, timeToMaturity, volatility, riskFreeRate), timeToMaturity, volatility)))/100
