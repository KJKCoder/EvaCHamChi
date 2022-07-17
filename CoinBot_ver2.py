import time
import pyupbit
import pandas as pd
import requests
from os import system
from collections import defaultdict
import schedule

# 슬랙 토큰 입력
myToken = ""
LongStrategyCoin = ["KRW-IQ","KRW-SRM","KRW-SAND"]
total = 60000
left = 60000
# access키와 secret키 입력
access = "XZq3Elq9i9xWk4dBgdmxRNrzorZiGkEGckL9o7Mo"
secret = "pVVVa1oNNgGzCDadIU9cqxkCbYOna5RU2SEBZMKQ"
upbit = pyupbit.Upbit(access, secret)
# K값, 동시 구매 가능한 코인 개수
K_value = 0.5
Limit_Value = 10 ; buy_Persent = 0.1

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

#매수
def buy(coin, rate): 
    global CoinInfo
    global CoinList
    global left
    global NomoneyBool
    time.sleep(0.2)
    
    if left >= total * rate - 100:
        NomoneyBool = False
        upbit.buy_market_order(coin, total * rate)
        time.sleep(0.2)

        left -= total * rate
        
        message = coin + " buy " + str(total * rate) + "won "
        Prt_and_Slack(message)

        CoinList.remove(coin)
    else :

        if NomoneyBool == False :
            message = "No Money"
            Prt_and_Slack(message)
        NomoneyBool = True

    return


# 코인 팔기
def sell(coin, currentprice): 
    global total
    global left

    amount = get_balance(coin.split("-")[1])
    time.sleep(0.2)
    upbit.sell_market_order(coin, amount) 
    time.sleep(0.2)

    #수익 Output
    tempProfit = Calculate_Profit(CoinInfo[coin]["BuyPrice"],currentprice)*100
    Profit = format(tempProfit,'f')
    message = coin + " is all Sold. Profit: " + str(Profit) + "%"
    Prt_and_Slack(message)

    left += currentprice*amount
    total += (currentprice*amount - CoinInfo[coin]["BuyPrice"]*amount)
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
        CoinInfo[curCoin]["StopLoss"] = CoinInfo[curCoin]["BuyPrice"]*0.97
        if CoinInfo[curCoin]["BuyPrice"]*1.03 < curPrice :
            CoinInfo[curCoin]["TimeProfit"] = (CoinInfo[curCoin]["HighPrice"] + CoinInfo[curCoin]["BuyPrice"])*0.5

        if curCoin in LongStrategyCoin :
            CoinInfo[curCoin]["TimeProfit"] = -1
            CoinInfo[curCoin]["StopLoss"] = -1
            if CoinInfo[curCoin]["BuyPrice"]*1.05 < curPrice :
                CoinInfo[curCoin]["TimeProfit"] = (CoinInfo[curCoin]["HighPrice"] + CoinInfo[curCoin]["BuyPrice"])*0.5
    return True

#현재 보유 중인 코인 목록 조회
def get_My_CoinList():
    temp = pd.DataFrame(upbit.get_balances()).iloc[:,0].values.tolist()
    time.sleep(0.3)
    result = []

    if "KRW" in temp :
        temp.remove("KRW")
    for cur in temp :
        result.append("KRW-" + cur)

    return result

# CoinList 초기화
def Get_CoinList_acc_trade() :
    global CoinList

    CoinList = []

    krw_tickers = pyupbit.get_tickers("KRW")
    querystring = {"markets":krw_tickers}
    url = "https://api.upbit.com/v1/ticker" #업비트 주소2
    headers = {"Accept": "application/json"}
    response = requests.request("GET", url, headers=headers,params=querystring)
    time.sleep(0.2)

    df = pd.DataFrame(response.json()).loc[:,["acc_trade_price_24h","market"]]
    sorteddf = df.sort_values(by=df.columns[0],ascending=False).reset_index(drop=True)
    templist = sorteddf["market"].tolist()
    
    temp = get_My_CoinList()

    if get_start_price("KRW-BTC", "day") >= get_ma15("KRW-BTC") :

        for curCoin in templist:
            start_price = get_start_price(curCoin, "day")
            Ma15 = get_ma15(curCoin)
            if not(curCoin in temp) and start_price >= Ma15:
                CoinList.append(curCoin)
            if len(CoinList) >= Limit_Value :
                break

        message = "It's Trading day!" 
        Prt_and_Slack(message)
        message = "Today's Target : \n" + str(CoinList) 
        Prt_and_Slack(message)

    else :
        message = "Watching Day" 
        Prt_and_Slack(message)

    return 1

#15일 이동 평균선 조회
def get_ma15(ticker,interval = "day", count = 15):
    df = pyupbit.get_ohlcv(ticker, interval = interval, count = count)
    time.sleep(0.1)
    ma15 = df['close'].rolling(count).mean().iloc[-1]
    return ma15

# 시작 가격 조회
def get_start_price(ticker, interval):             
    df = pyupbit.get_ohlcv(ticker, interval=interval, count=1)     
    time.sleep(0.1)
    start_price = df.iloc[0]['open']   
    return start_price


# 변동성 돌파 전략으로 매수 목표가 정하기 
def get_target_price(ticker, interval, k):        
    df = pyupbit.get_ohlcv(ticker, interval=interval, count=2)     
    time.sleep(0.1)
    target_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * k       
    return target_price

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
schedule.every().day.at("09:00:30").do(Get_CoinList_acc_trade)

CoinInfo = defaultdict(dict)
CoinList = []

Get_CoinList_acc_trade()
Prt_and_Slack("Start Program")

while(True) :
    try:
        schedule.run_pending()
        
        #print(CoinList)

        for curCoin in CoinList :
            curPrice = get_current_price(curCoin)
            Ma15 = get_ma15(curCoin)
            targetPrice = get_target_price(curCoin,"day", K_value)

            print(curCoin, curPrice, Ma15, targetPrice)
            if curPrice > targetPrice and curPrice > Ma15 :
                buy(curCoin, buy_Persent)

        initialize()

        for curCoin in CoinInfo :
            curPrice = get_current_price(curCoin)
            
            if CoinInfo[curCoin]["TimeProfit"] > curPrice :
                sell(curCoin, curPrice)
            elif CoinInfo[curCoin]["StopLoss"] > curPrice :
                sell(curCoin, curPrice)
               
        #print(CoinInfo)
        
    except Exception as e :
        message = str(e) + " is Error Occured"
        Prt_and_Slack(message)
