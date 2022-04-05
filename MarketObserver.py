from collections import defaultdict
import time
import pyupbit
import datetime
import pandas
import requests
import schedule

def initialize():
    global RSIMonitor_AllCoin

    response = requests.request("GET", url, headers=headers, params=querystring).json()
    time.sleep(1)
    response_df = pandas.DataFrame(response)
    KrwCoinList_InUpbit = response_df.loc[:,"market"].to_list()

    for curCoin in KrwCoinList_InUpbit : 
        data = pyupbit.get_ohlcv(ticker=curCoin, interval="minutes10") 
        time.sleep(0.1)
        rsi_df = rsi(data, 14)
        RSIMonitor_AllCoin[curCoin] = rsi_df.iloc[-1]

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
        if countlow/len(RSIMonitor) > 0.4 :
            result = "Down_Market_RSI"
        elif counthigh/len(RSIMonitor) > 0.4:
            result = "Up_Market_RSI"
        else :
            result = "Usually_Market_RSI"
            
    return result

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
    message = "Now Monitoring... "
    Prt_and_Slack(message)
schedule.every(3).hours.do(check_running_right)


krw_tickers = pyupbit.get_tickers("KRW")
url = "https://api.upbit.com/v1/ticker" #업비트 주소
headers = {"Accept": "application/json"}
querystring = {"markets":krw_tickers}

# 슬랙 토큰 입력
myToken = ""
RSIMonitor_AllCoin = {}
Market_RSI_Bef = "Usually_Market_RSI"
Market_RSI_Count = 0

Prt_and_Slack("Start Program")

while True :
    try:
        schedule.run_pending()
        initialize()
        Market_RSI = check_Market_RSI(RSIMonitor_AllCoin)

        if Market_RSI == Market_RSI_Bef :
            Market_RSI_Count += 1
            if (Market_RSI_Count % 50) == 0 :
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
        print(Market_RSI , Market_RSI_Count)
    except Exception as e :
        message = e + " is Error Occured"
        Prt_and_Slack(message)

    time.sleep(600)