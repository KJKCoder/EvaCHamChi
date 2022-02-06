import requests
import pyupbit 
import pandas 
import time 
import datetime

# 로그인
access = "OfAOARc0bcf71Gt1pgxExfLE7YavYTBLbU3WxuqF"
secret = "Ix4UbQvwyxOQ3Gj7WgzeMCHQ4B0J2Ae7JIiN7jzR"

upbit = pyupbit.Upbit(access, secret)
print("Login OK")

#업비트 데이터 가져오기
url = "https://api.upbit.com/v1/market/all?isDetails=false" #업비트 주소
headers = {"Accept": "application/json"}

# 자본금
total = 60000
N_Counter = 0
HaveCoin = {}

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
    

#매매코드
def buy(coin): 
    #money = upbit.get_balance("KRW") 
    print(coin, "을 매수합니다")
    global N_Counter
    if N_Counter <= 9:
        money = total
        if money < 20000 : 
            res = upbit.buy_market_order(coin, money*0.1) 
        elif money < 50000: 
            res = upbit.buy_market_order(coin, money*0.1) 
        elif money < 100000 : 
            res = upbit.buy_market_order(coin, money*0.1) 
        elif money < 5000 :
            print("잔고가 없습니다.")
        else : res = upbit.buy_market_order(coin, money*0.1) 
        N_Counter += 1
    else :
        print("10차 매수를 이미 실행했습니다.")
    print()
    return 

def sell(coin, HaveCoin): 
    print(coin, " 을 ", HaveCoin, "개 매도합니다")
    amount = upbit.get_balance(coin) 
    cur_price = pyupbit.get_current_price(coin) 
    total = amount * cur_price 
    if total < 20000 : 
        res = upbit.sell_market_order(coin, amount) 
    elif total < 50000: 
        res = upbit.sell_market_order(coin, amount) 
    elif total < 100000:
        res = upbit.sell_market_order(coin, amount) 
    else : res = upbit.sell_market_order(coin, amount) 
    global N_Counter
    N_Counter -= HaveCoin
    if N_Counter < 0 : N_Counter = 0
    print()
    return

#코인 관리 데이터
coinlist = [] 
lower28 = {}
higher70 = {}
CoinPriceMyBuy = {}

# 초기화 및 매수 매도
while(True): 

    #초기화
    response_df = pandas.DataFrame(requests.request("GET", url, headers=headers).json())
    KrwCoinList_InUpbit = response_df.loc[response_df['market'].str.contains('KRW')].loc[:,"market"].to_list()
    time.sleep(1)
    coinlist = KrwCoinList_InUpbit

    #누락 코인 추가
    for i in range(len(coinlist)): 
        if not(coinlist[i] in lower28) : 
            lower28[coinlist[i]] = False 
            higher70[coinlist[i]] = False 
    #매수, 매도 주문 시작
    for i in range(len(coinlist)): 
        try:
            curCoin = coinlist[i]
            data = pyupbit.get_ohlcv(ticker=coinlist[i], interval="minute30") 
            time.sleep(0.1)
            curPrice = pyupbit.get_current_price(curCoin)
            time.sleep(0.1)
            now_rsi = rsi(data, 14).iloc[-1] 
            
            if now_rsi <= 25 : 
                lower28[curCoin] = True 
                print(curCoin," 이 과매도 상태입니다. 매수를 준비합니다.")
            elif now_rsi >= 37 and lower28[curCoin] == True: 
                buy(curCoin) 
                CoinPriceMyBuy[curCoin] = curPrice

                print("\n코인명: ", curCoin) 
                print("RSI :", now_rsi) 
                print(datetime.datetime.now())
                print("매수 가격 :", CoinPriceMyBuy[curCoin],"\n") 
                
                if not(curCoin in HaveCoin) :
                    HaveCoin[curCoin] = 0
                HaveCoin[curCoin] += 1

                lower28[curCoin] = False 

            elif now_rsi >= 70 and higher70[curCoin] == False and HaveCoin[curCoin] > 0: 
                print(curCoin, " 코인이 과매수 상태입니다. 매도를 준비합니다.")
                higher70[curCoin] = True 
            elif now_rsi <= 65 and higher70[curCoin] == True and HaveCoin[curCoin] > 0:         
                sell(curCoin, HaveCoin[curCoin]) 
                HaveCoin[curCoin] = 0
                higher70[curCoin] = False 
            elif CoinPriceMyBuy[curCoin] >= curPrice*1.07 :
                sell(curCoin, HaveCoin[curCoin]) 
                print(curCoin, " 코인의 손해가 7% 이상입니다. 손절합니다.")
                HaveCoin[curCoin] = 0
                lower28[curCoin] = False 
                higher70[curCoin] = False 
                del CoinPriceMyBuy[curCoin]
        except KeyError:
            pass
    print("모니터링 중...")
    time.sleep(1800 - len(coinlist)*0.2-1-0.3)