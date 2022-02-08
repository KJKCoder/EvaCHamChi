from logging import exception
import time
import pyupbit
import datetime
import pandas
import requests

access = "OfAOARc0bcf71Gt1pgxExfLE7YavYTBLbU3WxuqF"
secret = "Ix4UbQvwyxOQ3Gj7WgzeMCHQ4B0J2Ae7JIiN7jzR"

# 자본금
total = 30000
totalRSI = 30000
N_Counter = 0

#RSI가져오기
def rsi(ohlc: pandas.DataFrame, period: int = 14): 
    delta = ohlc["close"].diff() 
    ups, downs = delta.copy(), delta.copy() 
    ups[ups < 0] = 0 
    downs[downs > 0] = 0 
    AU = ups.ewm(com = period-1, min_periods = period).mean() 
    AD = downs.abs().ewm(com = period-1, min_periods = period).mean() 
    RS = AU/AD 
    return pandas.Series(100 - (100/(1 + RS)), name = "RSI") 
    

#Rsi 매매코드
def buy(coin): 
    #money = upbit.get_balance("KRW") 
    print(coin, "buy")
    global N_Counter
    if N_Counter <= 2:
        money = totalRSI
        upbit.buy_market_order(coin, money*0.3) 
        N_Counter += 1
    else :
        print("3 times buying already done")
    print()
    return 

def sell(coin, HaveCoin): 
    print(coin, " is ", HaveCoin, "Sold")
    amount = upbit.get_balance(coin) 
    cur_price = pyupbit.get_current_price(coin) 
    
    upbit.sell_market_order(coin, amount) 
    
    global N_Counter
    N_Counter -= HaveCoin
    if N_Counter < 0 : N_Counter = 0
    print()
    return


#변동성 돌파
def get_target_price(ticker, k):
    """변동성 돌파 전략으로 매수 목표가 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=2)
    target_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * k
    return target_price

def get_start_time(ticker):
    """시작 시간 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=1)
    start_time = df.index[0]
    return start_time

def get_ma15(ticker):
    """15일 이동 평균선 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=15)
    ma15 = df['close'].rolling(15).mean().iloc[-1]
    return ma15

def get_balance(ticker):
    """잔고 조회"""
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == ticker:
            if b['balance'] is not None:
                return float(b['balance'])
            else:
                return 0
    return 0

def get_current_price(ticker):
    """현재가 조회"""
    return pyupbit.get_orderbook(ticker=ticker)["orderbook_units"][0]["ask_price"]

# 로그인
upbit = pyupbit.Upbit(access, secret)
print("autotrade start")
url = "https://api.upbit.com/v1/market/all?isDetails=false" #업비트 주소
headers = {"Accept": "application/json"}

#변동성돌파
coinlistTarget = ["KRW-BTC","KRW-ETH","KRW-ADA","KRW-SOL","KRW-DOT","KRW-DOGE"] 
CoinPriceMyBuy = {}
for current in coinlistTarget :
    CoinPriceMyBuy[current] = 0

#RSI
coinlist = [] 
lower28 = {}
higher70 = {}
interval_time = "minute60"
HaveCoin = {}
CoinPriceMyBuyRSI= {}



# 자동매매 시작
while True:
    
    #변동성 돌파 전략
    for curCoin in coinlistTarget : 
        try:
            now = datetime.datetime.now()
            start_time = get_start_time(curCoin) - datetime.timedelta(hours=4)
            time.sleep(0.2)
            end_time = start_time + datetime.timedelta(days=1)
            if start_time < now < end_time - datetime.timedelta(seconds=10):
                target_price = get_target_price(curCoin, 0.3)
                time.sleep(0.2)
                ma15 = get_ma15(curCoin)
                time.sleep(0.2)
                current_price = get_current_price(curCoin)
                time.sleep(0.2)
                if target_price < current_price and ma15 < current_price and CoinPriceMyBuy[curCoin]==0:
                    #krw = get_balance(curCoin)
                    krw =  30000
                    if total > 5000 and CoinPriceMyBuy[curCoin] == 0:
                        upbit.buy_market_order(curCoin, krw*0.3)
                        time.sleep(0.2)
                        CoinPriceMyBuy[curCoin] = krw*0.3
                        total -= krw*0.3
                        print(curCoin," buy ", CoinPriceMyBuy[curCoin] , "won ", total , " left")
            else:
                coinBalance = get_balance(curCoin.split("-")[1])
                time.sleep(0.2)
                if coinBalance > 0.00008:
                    upbit.sell_market_order(curCoin, coinBalance)
                    time.sleep(0.2)
                    CoinPriceMyBuy[curCoin] = 0
                    total += krw*0.3
                    print(curCoin," sold ")
                    
        except Exception as e :
            pass
            time.sleep(1)
                    
          
#매수, 매도 주문 시작 RSI   
         
    #초기화
    response_df = pandas.DataFrame(requests.request("GET", url, headers=headers).json())
    KrwCoinList_InUpbit = response_df.loc[response_df['market'].str.contains('KRW')].loc[:,"market"].to_list()
    time.sleep(1)
    coinlist = KrwCoinList_InUpbit

    #누락 코인 추가 RSI
    for i in range(len(coinlist)): 
        if not(coinlist[i] in lower28) : 
            lower28[coinlist[i]] = False 
            higher70[coinlist[i]] = False 
            HaveCoin[coinlist[i]] = 0    
            
    for curCoin in coinlist :           
        try:
            if HaveCoin[curCoin] > 0:
                interval_time = "minute30"
            elif HaveCoin[curCoin] == 0:
                interval_time = "minute60"
            
            data = pyupbit.get_ohlcv(ticker=coinlist[i], interval=interval_time) 
            time.sleep(0.1)
            curPrice = pyupbit.get_current_price(curCoin)
            time.sleep(0.1)
            now_rsi = rsi(data, 14).iloc[-1] 
            
            if now_rsi <= 28 : 
                lower28[curCoin] = True 
                print(curCoin," is overSelling state. ready for Buying")
            elif now_rsi >= 33 and lower28[curCoin] == True: 
                buy(curCoin) 
                CoinPriceMyBuyRSI[curCoin] = curPrice

                print("\CoinName: ", curCoin) 
                print("RSI :", now_rsi) 
                print(datetime.datetime.now())
                print("Price :", CoinPriceMyBuyRSI[curCoin],"\n") 
                
                if not(curCoin in HaveCoin) :
                    HaveCoin[curCoin] = 0
                HaveCoin[curCoin] += 1

                lower28[curCoin] = False 

            elif now_rsi >= 68 and higher70[curCoin] == False and HaveCoin[curCoin] > 0: 
                print(curCoin, " is overBuying state. ready for selling.")
                higher70[curCoin] = True 
            elif now_rsi <= 65 and higher70[curCoin] == True and HaveCoin[curCoin] > 0:         
                sell(curCoin, HaveCoin[curCoin]) 
                HaveCoin[curCoin] = 0
                higher70[curCoin] = False 
        except KeyError:
            pass
    time.sleep(600)
