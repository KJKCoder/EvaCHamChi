from logging import exception
from collections import defaultdict
import time
import pyupbit
import datetime
import pandas
import requests
import schedule

#초기화
def initialize() :
    global CoinInfo
    global RSIMonitor_AllCoin
    global Satisfied_Coin
    global coinlist

    # 상장된 코인들 List 불러옴
    Satisfied_Coin = defaultdict(set)
    response = requests.request("GET", url, headers=headers, params=querystring).json()
    time.sleep(1)
    response_df = pandas.DataFrame(response)
    KrwCoinList_InUpbit = response_df.loc[:,"market"].to_list()

    # 내 coinlist(관심 종목) 중 상장되지 않은 코인들 제거
    temp = []
    for curCoin in coinlist :
        if not(curCoin in KrwCoinList_InUpbit) :
            temp.append(curCoin)
    for curCoin in temp :
        coinlist.remove(curCoin)
        del CoinInfo[curCoin]

    # RSIMonitor_AllCoin의 RSI값 초기화
    for curCoin in KrwCoinList_InUpbit : 
        data = pyupbit.get_ohlcv(ticker=curCoin, interval=interval_time) 
        time.sleep(0.1)
        rsi_df = rsi(data, 14)
        RSIMonitor_AllCoin[curCoin] = rsi_df.iloc[-1]

        #coinlist에 있는 종목들 CoinInfo에 RSI값 등록
        if curCoin in coinlist:
            CoinInfo[curCoin]["RSINow"] = RSIMonitor_AllCoin[curCoin]
            CoinInfo[curCoin]["RSIBef"] = rsi_df.iloc[-2]

#RSI가져오기
def rsi(ohlc: pandas.DataFrame, period: int = 14): 
    delta = ohlc["close"].diff() 
    time.sleep(0.2)
    ups, downs = delta.copy(), delta.copy() 
    ups[ups < 0] = 0 
    downs[downs > 0] = 0 
    AU = ups.ewm(com = period-1, min_periods = period).mean() 
    AD = downs.abs().ewm(com = period-1, min_periods = period).mean() 
    RS = AU/AD 
    return pandas.Series(100 - (100/(1 + RS)), name = "RSI") 
    
#매수
def buy(coin, rate): 
    global left
    global CoinInfo
    krw = get_balance("KRW") - 6000
    time.sleep(0.2)
    
    if krw > 0:
        upbit.buy_market_order(coin, krw * rate)
        time.sleep(0.2)
        CoinInfo[coin]["CoinPriceMyBuy"] += krw * rate
        CoinInfo[coin]["BuyTime"] = datetime.datetime.now()
        CoinInfo[curCoin]["lower"] = False
        message = coin + " buy " + str(CoinInfo[coin]["CoinPriceMyBuy"]) + "won " + str(krw - CoinInfo[coin]["CoinPriceMyBuy"]) + "left. Time: " + str(CoinInfo[coin]["BuyTime"])
        Prt_and_Slack(message)
    else :
        message = "No Money"
        Prt_and_Slack(message)
    return

#매도
def sell(coin, currentprice): 
    global CoinInfo
    global left
    amount = get_balance(coin.split("-")[1])
    time.sleep(0.2)
    upbit.sell_market_order(coin, amount) 
    time.sleep(0.2)

    #수익 Output
    message = coin + " is all Sold. Profit: " + str(Calculate_Profit(coin,currentprice*amount)*100) + "%"
    Prt_and_Slack(message)

    left += currentprice*amount
    CoinInfo[coin]["BuyTime"] = -1
    CoinInfo[coin]["CoinPriceMyBuy"] = -1
    CoinInfo[coin]["RSIHighest"] = -1
    CoinInfo[coin]["higher"] = False
    CoinInfo[coin]["SellPermitTime"] = datetime.datetime.now()
    return

#수익 계산
def Calculate_Profit(coin, soldprice) :
    return round(soldprice - CoinInfo[coin]["CoinPriceMyBuy"],4) / CoinInfo[coin]["CoinPriceMyBuy"]

#변동성 돌파
def get_target_price(ticker, k):
    df = pyupbit.get_ohlcv(ticker, interval="day", count=2)
    time.sleep(0.2)
    target_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * k
    return target_price

#15일 이동 평균선 조회
def get_ma15(ticker):
    df = pyupbit.get_ohlcv(ticker, interval="day", count=15)
    time.sleep(0.2)
    ma15 = df['close'].rolling(15).mean().iloc[-1]
    return ma15

#잔고 조회
def get_balance(ticker):
    balances = upbit.get_balances()
    time.sleep(0.2)
    for b in balances:
        if b['currency'] == ticker:
            if b['balance'] is not None:
                return float(b['balance'])
            else:
                return 0
    return 0

#코인 현재가 조회
def get_current_price(ticker):
    result = pyupbit.get_orderbook(ticker=ticker)["orderbook_units"][0]["ask_price"]
    time.sleep(0.2)
    return result

#시장 RSI 상황 체크
def check_Market_RSI(RSIMonitor) :
    tempList = list(RSIMonitor.values())
    if 0 in tempList  :
        print("Need To First Cycle")
        result = "None"
    else :
        countlow = 0
        counthigh = 0
        for cur in tempList  :
            if cur < 40 :
                countlow += 1
            elif cur > 60 :
                counthigh += 1
        if countlow/len(RSIMonitor) > 0.5 :
            result = "Down_Market_RSI"
        elif counthigh/len(RSIMonitor) > 0.5:
            result = "Up_Market_RSI"
        else :
            result = "Usually_Market_RSI"
            
    return result

#코인 Sell 후 4시간 동안 구입 금지 
def BanSoldCoin4Hour(curCoin, Nowtime):
    global CoinInfo
    if Nowtime >= CoinInfo[curCoin]["SellPermitTime"] + datetime.timedelta(hours=4) :
        CoinInfo[curCoin]["SellPermitTime"] = 0
        CoinInfo[curCoin]["CoinPriceMyBuy"] = 0
        return False
    else :
        CoinInfo[curCoin]["CoinPriceMyBuy"] = -1
        return True
    

# 슬랙 메시지 보내기
def post_message(token, channel, text):
    response = requests.post("https://slack.com/api/chat.postMessage",
        headers={"Authorization": "Bearer "+token},
        data={"channel": channel,"text": text}
    )
def Prt_and_Slack(message):
    print(message)
    post_message(myToken,"#cointrade",message)

def check_running_right() :
    message = "Now Monitoring..."
    Prt_and_Slack(message)
schedule.every(3).hours.do(check_running_right)


# access키와 secret키 입력
access = "OfAOARc0bcf71Gt1pgxExfLE7YavYTBLbU3WxuqF"
secret = "Ix4UbQvwyxOQ3Gj7WgzeMCHQ4B0J2Ae7JIiN7jzR"

# 슬랙 토큰 입력
myToken = ""

# 자본금
total = 18000
left = 18000

#로그인 및 request 변수
upbit = pyupbit.Upbit(access, secret)
print("autotrade start")

krw_tickers = pyupbit.get_tickers("KRW")
url = "https://api.upbit.com/v1/ticker" #업비트 주소
headers = {"Accept": "application/json"}
querystring = {"markets":krw_tickers}

#관심 코인 리스트, RSI변동 시간 간격 설정
coinlist = ["KRW-BTC","KRW-ETH","KRW-XRP","KRW-ADA","KRW-SOL","KRW-AVAX","KRW-DOT","KRW-DOGE","KRW-MATIC","KRW-CRO", "KRW-LTC","KRW-ATOM","KRW-LINK","KRW-TRX","KRW-NEAR","KRW-BCH","KRW-ALGO"]
interval_time = "minute240"
Market_RSI_Bef = "Usually_Market_RSI"
Market_RSI_Count = 0

# Dictionary 모음
CoinInfo = defaultdict(dict)
RSIMonitor_AllCoin = {}
TargetTouchCoin_Count = defaultdict(int)
Satisfied_Coin = defaultdict(set)

#CoinInfo 초기화
#CoinInfo 딕셔너리에는 하위 딕셔너리가 다수 포함됨.
for curCoin in coinlist: 
    if not(curCoin in CoinInfo) : 
        CoinInfo[curCoin]["RSINow"] = 0
        CoinInfo[curCoin]["RSIBef"] = 1000
        CoinInfo[curCoin]["RSIHighest"] = -1
        CoinInfo[curCoin]["lower"] = False
        CoinInfo[curCoin]["higher"] = False
        CoinInfo[curCoin]["BuyTime"] = -1
        CoinInfo[curCoin]["CoinPriceMyBuy"] = 0
        CoinInfo[curCoin]["SellPermitTime"] = 0 

Prt_and_Slack("Start Program")

# 자동매매 시작
while True:
    try :
        #초기화
        initialize()
        schedule.run_pending()

        Market_RSI = check_Market_RSI(RSIMonitor_AllCoin)

        if Market_RSI == Market_RSI_Bef :
            Market_RSI_Count += 1
            if Market_RSI_Count == 50 :
                message = "Market RSI " + Market_RSI + " is continue"
                Prt_and_Slack(message)
        else :
            message = "Market RSI changed " + Market_RSI_Bef + "=>" + Market_RSI
            Prt_and_Slack(message)
            if Market_RSI_Count > 50 :
                message = "Long lasted Market RSI changed " + Market_RSI_Bef + "=>" + Market_RSI
                Prt_and_Slack(message)
            Market_RSI_Bef = Market_RSI
            Market_RSI_Count = 0
            
        # print(Market_RSI , Market_RSI_Count)
        

        #매수 or 매도 조건 확인
        for curCoin in coinlist :  

            # 판매후 4시간이 지나지 않은 코인은 건너뜀
            Nowtime = datetime.datetime.now()
            if BanSoldCoin4Hour(curCoin,Nowtime) == True : continue
            
            #조정 변수 불러오기
            target_price = get_target_price(curCoin, 0.3)
            ma15 = get_ma15(curCoin)
            current_price = get_current_price(curCoin)
            now_rsi = CoinInfo[curCoin]["RSINow"]

            # 매수 조건만 확인, 실제 매수는 따로 진행
            if CoinInfo[curCoin]["CoinPriceMyBuy"] == 0:
                
                #변동성 돌파 원칙, 15일 평균선, RSI가 상승 모두 만족할 경우
                if target_price < current_price and ma15 < current_price and now_rsi >= CoinInfo[curCoin]["RSIBef"]:
                    
                    #TargetTouchCoin_Count에 등록, TargetTouchCoin_Count코인이 3개 이상일 때 Satisfied_Coin에 등록
                    TargetTouchCoin_Count[curCoin] += 1
                    if len(TargetTouchCoin_Count) >= 2 :

                        # 구매 추천 정도(Very Strongly ~ Very Weakly)에 따라 Satisfied_Coin에 등록
                        # Down Market일 때는 등록하지 않음
                        if  Market_RSI == "Down_Market_RSI" :
                            message = curCoin +  " Target Strategy Satisfied But It is Down Market"
                            Prt_and_Slack(message)
                        elif  65 < now_rsi :
                            Satisfied_Coin["Very Weakly"].add(curCoin)
                            print(curCoin + "add Satified Coin Very Weakly Recommed")
                        elif 50 < now_rsi <= 65 :
                            Satisfied_Coin["Weakly"].add(curCoin)
                            print(curCoin + "add Satified Coin Weakly Recommed")
                        elif now_rsi <= 50 and CoinInfo[curCoin]["lower"] == True:
                            Satisfied_Coin["Very Strongly"].add(curCoin)
                            print(curCoin + "add Satified Coin Very Strongly Recommed")
                        elif now_rsi <= 50:
                            Satisfied_Coin["Strongly"].add(curCoin)
                            print(curCoin + "add Satified Coin Strongly Recommed")

                    else :
                        print(curCoin , " Target Strategy Satisfied, Keep an eye on to Buy")
        

                #과매도 상태인 코인(RSI < 28) 탐색
                elif now_rsi < 28 : 
                    CoinInfo[curCoin]["lower"] = True
                    print(curCoin," is lower than RSI: 28. Over Selling State")

                    #TargetPrice에 도달했다가 떨어진 코인 TargetTouchCoin_Count에서 삭제
                    if curCoin in TargetTouchCoin_Count :
                        del TargetTouchCoin_Count[curCoin]
                    
                else :
                    #TargetPrice에 도달했다가 떨어진 코인 TargetTouchCoin_Count에서 삭제
                    if curCoin in TargetTouchCoin_Count :
                        del TargetTouchCoin_Count[curCoin]
                        


            # 매도 조건 확인, 조건 달성 시 바로 매도 진행
            elif CoinInfo[curCoin]["CoinPriceMyBuy"] > 0 :
                
                # RSI가 Highest일 때 등록
                if now_rsi >= CoinInfo[curCoin]["RSIHighest"] : CoinInfo[curCoin]["RSIHighest"] = now_rsi

                # 구매 후 하루가 지나지 않았을 때
                if Nowtime <= CoinInfo[curCoin]["BuyTime"]  + datetime.timedelta(days = 1) :

                    # RSI가 70이상일 때
                    if now_rsi >= 70 and CoinInfo[curCoin]["higher"] == False:
                        CoinInfo[curCoin]["higher"] = True
                        print(curCoin ," RSI is over 70, Ready To Sell")
                    elif CoinInfo[curCoin]["RSIHighest"] - 5 and CoinInfo[curCoin]["higher"] == True:
                        sell(curCoin,current_price)
                        print("By RSI over 70 when: ", now_rsi)

                    # RSI가 70까지 도달 못하고 가격이 떨어질 때
                    elif CoinInfo[curCoin]["RSIHighest"] - 7 > now_rsi and CoinInfo[curCoin]["higher"] == False and target_price > current_price:
                        sell(curCoin,current_price)
                        print("By RSI Drop Shock: ", now_rsi)


                # 구매 후 하루가 지났을 때
                else:
                    # RSI가 상승세일 때 Hold
                    if now_rsi >= CoinInfo[curCoin]["RSIBef"] - 1:
                        message = curCoin + " Hold. expect UP"
                        Prt_and_Slack(message)
                        # 추가 매수 실행
                        if target_price < current_price and ma15 < current_price :
                            buy(curCoin,0.2)
                            message = curCoin + " Add Buy, Touch Target Price again"
                            Prt_and_Slack(message)
                    else :
                        sell(curCoin,current_price)
                        message = curCoin+" Sold Because One Day Later. when: " + str(datetime.datetime.now())
                        Prt_and_Slack(message)

            #print(curCoin , " nowRSI: ",now_rsi ," BefRSI: ", CoinInfo[curCoin]["RSIBef"], target_price , current_price , ma15)        




        # Satisfied_Coin 매수 실행
        if not(Satisfied_Coin == defaultdict(set)) :
            for recommend in Satisfied_Coin.keys() :
                for curCoin in Satisfied_Coin[recommend] :
                    #curCoin이 3회 이상 매수 조건 연속으로 만족했을 경우 매수 실행
                    if TargetTouchCoin_Count[curCoin] >= 3 :

                        if recommend == "Very Strongly" :
                            buy(curCoin,0.6)
                            message = "By Target Strategy Very Strongly Recommed"
                            Prt_and_Slack(message)
                        elif recommend == "Strongly" :
                            buy(curCoin,0.4)
                            message = "By Target Strategy Strongly Recommed"
                            Prt_and_Slack(message)
                        elif recommend == "Weakly" :
                            buy(curCoin,0.2)
                            message = "By Target Strategy Weakly Recommed"
                            Prt_and_Slack(message)
                        else :
                            buy(curCoin,0.1)
                            message = "By Target Strategy Very Weakly Recommed"
                            Prt_and_Slack(message)

    except Exception as e :
        message = e + " is Error Occured"
        Prt_and_Slack(message)

    time.sleep(600)