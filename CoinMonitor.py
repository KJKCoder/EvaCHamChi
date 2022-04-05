import time
import pyupbit
import pandas as pd
import requests
from os import system
from collections import defaultdict
import schedule

# 슬랙 토큰 입력
myToken = ""
# 존버 전략 코인
LongStrategyCoin = ["KRW-SOL","KRW-SAND"]
# access키와 secret키 입력
access = "XZq3Elq9i9xWk4dBgdmxRNrzorZiGkEGckL9o7Mo"
secret = "pVVVa1oNNgGzCDadIU9cqxkCbYOna5RU2SEBZMKQ"
upbit = pyupbit.Upbit(access, secret)


#초기화
def initialize() :
    global CoinInfo

    temp = get_My_CoinList()
    temp_to_add = []

    for curCoin in temp :
        if not(curCoin in CoinInfo) :
            temp_to_add.append(curCoin)
            
    for curCoin in temp_to_add :
        CoinInfo[curCoin]["HighPrice"] = 0
        CoinInfo[curCoin]["BuyPrice"] = 0
        CoinInfo[curCoin]["StopLoss"] = -1
        CoinInfo[curCoin]["TimeProfit"] = -1

    Set_CoinInfo()
    return True

# 코인 팔기
def sell(coin, currentprice): 
    global CoinInfo
    amount = get_balance(coin.split("-")[1])
    time.sleep(0.2)
    upbit.sell_market_order(coin, amount) 
    time.sleep(0.2)

    #수익 Output
    tempProfit = Calculate_Profit(CoinInfo[coin]["BuyPrice"],currentprice)*100
    Profit = format(tempProfit,'f')
    message = coin + " is all Sold. Profit: " + str(Profit) + "%"
    Prt_and_Slack(message)

    CoinInfo.pop(coin)

    return True

#수익 계산
def Calculate_Profit(buyprice, soldprice) :
    return (soldprice-buyprice)/buyprice

# 잔고 조회
def get_balance(currency):                          
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == currency:
            if b['balance'] is not None:
                return float(b['balance'])
            else:
                return 0

# 현재 가격 가져오기
def get_current_price(ticker):      
    result = pyupbit.get_current_price(ticker = ticker)  
    time.sleep(0.1) 
    return result

# 매수 평균가격 가져오기
def get_buy_avg_Price(ticker):
    result = upbit.get_avg_buy_price(ticker)
    time.sleep(0.1) 
    return result

# CoinInfo값들 설정
def Set_CoinInfo():
    global CoinInfo
    for curCoin in CoinInfo :
        curPrice = get_current_price(curCoin)

        if CoinInfo[curCoin]["HighPrice"] <= curPrice :
            CoinInfo[curCoin]["HighPrice"] = curPrice
        CoinInfo[curCoin]["BuyPrice"] = get_buy_avg_Price(curCoin)
        CoinInfo[curCoin]["StopLoss"] = CoinInfo[curCoin]["BuyPrice"]*0.9
        if CoinInfo[curCoin]["BuyPrice"]*1.08 < curPrice :
            CoinInfo[curCoin]["TimeProfit"] = (CoinInfo[curCoin]["HighPrice"] + CoinInfo[curCoin]["BuyPrice"])*0.5

        if curCoin in LongStrategyCoin:
            CoinInfo[curCoin]["StopLoss"] = CoinInfo[curCoin]["BuyPrice"]*0.8
            CoinInfo[curCoin]["TimeProfit"] = -1
    return True

#현재 보유 중인 코인 목록 조회
def get_My_CoinList():
    temp = pd.DataFrame(upbit.get_balances()).iloc[:,0].values.tolist()
    result = []
    time.sleep(0.2)

    if "KRW" in temp :
        temp.remove("KRW")
    for cur in temp :
        result.append("KRW-" + cur)

    return result

# 슬랙 메시지 보내기
def post_message(token, channel, text):
    requests.post("https://slack.com/api/chat.postMessage",
        headers={"Authorization": "Bearer "+token},
        data={"channel": channel,"text": text}
    )
def Prt_and_Slack(message):
    print(message)
    post_message(myToken,"#cointrade",message)

def check_running_right() :
    message = "Now Monitoring... " 
    Prt_and_Slack(message)
schedule.every(3).hours.do(check_running_right)



CoinInfo = defaultdict(dict)

Prt_and_Slack("Start Program")

while(True) :
    try:
        schedule.run_pending()
        initialize()

        for curCoin in CoinInfo :
            curPrice = get_current_price(curCoin)
        
            if CoinInfo[curCoin]["TimeProfit"] > curPrice :
                sell(curCoin, curPrice)
            elif CoinInfo[curCoin]["StopLoss"] > curPrice :
                sell(curCoin, curPrice)

    except Exception as e :
        message = str(e) + " is Error Occured"
        Prt_and_Slack(message)
