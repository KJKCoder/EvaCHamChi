import time
import pyupbit
import datetime
import pandas
import requests
import schedule
from collections import defaultdict

def initialize() :
    global coinlist
    global CoinInfo
    """
    krw_tickers = pyupbit.get_tickers("KRW")
    querystring = {"markets":krw_tickers}

    response = requests.request("GET", url2, headers=headers,params=querystring)
    time.sleep(1)
    df = pandas.DataFrame(response.json()).loc[:,["acc_trade_price","market"]]
    sorteddf = df.sort_values(by=df.columns[0],ascending=False).reset_index(drop=True)

    templist = sorteddf.loc[0:10]["market"].values.tolist()
    coinlist = Intereset_Coin
    
    for curCoin in templist :
        if not(curCoin in Intereset_Coin) :
            coinlist.append(curCoin)
    """

    coinlist = Intereset_Coin
    CoinInfo = defaultdict(dict)
    for curCoin in coinlist :
        CoinInfo[curCoin]["PriceBuy"] = 0
        CoinInfo[curCoin]["SoldTime"] = 0
        CoinInfo[curCoin]["StopLoss"] = 0
        CoinInfo[curCoin]["TakeProfit"] = 0
    return True

#매수
def buy(coin, rate, currentPrice): 
    global CoinInfo
    global left
    global NomoneyBool
    time.sleep(0.2)
    
    if left >= total * rate - 100:
        NomoneyBool = False
        upbit.buy_market_order(coin, total * rate)
        time.sleep(0.2)

        CoinInfo[coin]["PriceBuy"] = currentPrice
        set_StopLoss_Price(curCoin)
        left -= total * rate
        
        message = coin + " buy " + str(total * rate) + "won " + str(left) + "left."
        Prt_and_Slack(message)
    else :
        if NomoneyBool == False :
            message = "No Money"
            Prt_and_Slack(message)
        NomoneyBool = True
    return

#매도
def sell(coin, currentprice): 
    global CoinInfo
    global total
    global left
    amount = get_balance(coin.split("-")[1])
    time.sleep(0.2)
    upbit.sell_market_order(coin, amount) 
    time.sleep(0.2)

    #수익 Output
    tempProfit = Calculate_Profit(CoinInfo[coin]["PriceBuy"],currentprice)*100
    Profit = format(tempProfit,'f')
    message = coin + " is all Sold. Profit: " + str(Profit) + "%"
    Prt_and_Slack(message)
    ProfitList.append(tempProfit)

    tempint = currentprice*amount*0.999
    total += tempint - CoinInfo[coin]["PriceBuy"]*amount
    left += tempint

    CoinInfo[coin]["PriceBuy"] = 0
    CoinInfo[coin]["SoldTime"] = datetime.datetime.now()
    CoinInfo[coin]["StopLoss"] = 0
    CoinInfo[curCoin]["TakeProfit"] = 0
    return

#수익 계산
def Calculate_Profit(buyprice, soldprice) :
    
    output = ((soldprice-buyprice)/buyprice)
    return output

# 시작 시간 조회
def get_start_time(ticker, interval):             
    df = pyupbit.get_ohlcv(ticker, interval=interval, count=1)
    start_time = df.index[0]
    return start_time

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
    return pyupbit.get_current_price(ticker = ticker)

# 변동성 돌파 전략으로 매수 목표가 정하기 
def get_target_price(ticker, interval, k):        
    df = pyupbit.get_ohlcv(ticker, interval=interval, count=2)     
    target_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * k       
    return target_price

#15일 이동 평균선 조회
def get_ma15(ticker,interval = "day", count = 15):
    df = pyupbit.get_ohlcv(ticker, interval = interval, count = count)
    time.sleep(0.2)
    ma15 = df['close'].rolling(count).mean().iloc[-1]
    return ma15

#3015, 3030 이동 평균선 조회
def get_ma1530(ticker,interval = "minutes30", count1 = 15,count2 = 30):
    df = pyupbit.get_ohlcv(ticker, interval = interval, count = count2)
    time.sleep(0.2)
    ma15 = df['close'].rolling(count1).mean().iloc[-1]
    ma30 = df['close'].rolling(count2).mean().iloc[-1]
    temp = []
    temp.append(ma15) ; temp.append(ma30)
    return temp

#유의 종목 불러오기
def get_CAUTION_coinlist() :
    result = pandas.DataFrame(requests.request("GET",url=url,headers=headers).json())
    time.sleep(1)
    result = result.loc[result["market_warning"]=="CAUTION","market"].to_list()
    return result

#유의 종목 체크
def check_CAUTION(CAUTIONlist,curCoin):
    if curCoin in CAUTIONlist :
        return True
    else :
        return False

#손절 가격 설정
def set_StopLoss_Price(curCoin) :
    OpenPrice = pyupbit.get_ohlcv(curCoin, interval=interval_time, count=1)["open"]
    time.sleep(0.1)
    CoinInfo[curCoin]["StopLoss"] = (float(OpenPrice) + CoinInfo[curCoin]["PriceBuy"]) / 2
    return True

#익절 가격 설정
def set_TakeProfit_Price(curCoin, currentPrice) :
    global CoinInfo
    PriceBuy = CoinInfo[curCoin]["PriceBuy"]
    profit_rate = (currentPrice - PriceBuy) / PriceBuy
    if profit_rate >= 0.03 :
        if CoinInfo[curCoin]["TakeProfit"] <=  (1 + profit_rate/2) * PriceBuy :
            CoinInfo[curCoin]["TakeProfit"] = (1 + profit_rate/2) * PriceBuy
    return True

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



# access키와 secret키 입력
access = "OfAOARc0bcf71Gt1pgxExfLE7YavYTBLbU3WxuqF"
secret = "Ix4UbQvwyxOQ3Gj7WgzeMCHQ4B0J2Ae7JIiN7jzR"

#로그인 및 request 변수
upbit = pyupbit.Upbit(access, secret)

url = "https://api.upbit.com/v1/market/all?isDetails=True" #업비트 주소
url2 = "https://api.upbit.com/v1/ticker" #업비트 주소2
headers = {"Accept": "application/json"}

# 슬랙 토큰 입력
myToken = ""

#조절 변수 입력
total = 96500
left = 96500
time.sleep(0.2)
interval_time = "day"
K_value = 0.3
Intereset_Coin = KrwCoinList_InUpbit = ["KRW-BTC","KRW-ETH","KRW-XRP","KRW-ADA","KRW-POWR","KRW-SC","KRW-BCH","KRW-ENJ","KRW-MANA","KRW-ATOM","KRW-HIVE","KRW-LINK","KRW-BORA","KRW-CRO","KRW-SRM","KRW-META","KRW-SAND","KRW-MATIC","KRW-AAVE","KRW-NEAR","KRW-AVAX"]
coinlist = []
CoinInfo = defaultdict(dict)
NomoneyBool = False
initialize_Done = False

ProfitList = []

print("autotrade start")
Prt_and_Slack("Start Program")

# 자동매매 시작

while True:
    try :
        schedule.run_pending()

        CAUTION_coinlist = get_CAUTION_coinlist()

        start_time = get_start_time("KRW-BTC", interval_time)
        end_time = start_time + datetime.timedelta(days=1) - datetime.timedelta(minutes=3)
        now_time = datetime.datetime.now()

        if initialize_Done == False :
            initialize()
            initialize_Done = True

        if start_time < now_time < end_time :
            
            for curCoin in coinlist :
                curPrice = get_current_price(curCoin)

                if CoinInfo[curCoin]["PriceBuy"] == 0 :

                    if CoinInfo[curCoin]["SoldTime"] != 0 :
                        if CoinInfo[curCoin]["SoldTime"] + datetime.timedelta(days=1) > now_time :
                            message = curCoin + " Buy Lock"
                            Prt_and_Slack(message)
                            continue
                    else :
                        CoinInfo[curCoin]["SoldTime"] = 0

                    target_price = get_target_price(curCoin, interval_time, K_value)

                    Ma15 = get_ma15(curCoin)
                    Ma1530list = get_ma1530(curCoin,"minutes30",15,30)
                    Ma3015 = Ma1530list[0] ; Ma3030 = Ma1530list[1]

                    if curPrice >= target_price and curPrice > Ma15 and Ma3015 >= Ma3030:
                        if check_CAUTION(CAUTION_coinlist,curCoin) == False :
                            buy(curCoin,0.1,curPrice)
                        else :
                            message = curCoin + " is CAUTION State"
                            Prt_and_Slack(message)

                elif CoinInfo[curCoin]["PriceBuy"] > 0 :
                    set_TakeProfit_Price(curCoin,curPrice)

                    if CoinInfo[curCoin]["StopLoss"] > curPrice : 
                        sell(curCoin, curPrice)
                        print("stoploss")

                    elif CoinInfo[curCoin]["TakeProfit"] != 0 and CoinInfo[curCoin]["TakeProfit"] > curPrice:
                        sell(curCoin, curPrice)
                        print("takeProfit")

        elif end_time <= now_time :
            for curCoin in CoinInfo :
                if CoinInfo[curCoin]["PriceBuy"] > 0 :
                    curPrice = get_current_price(curCoin)
                    time.sleep(0.2)
                    sell(curCoin, curPrice)

            initialize_Done = False
    
            if len(ProfitList) != 0 :
                message = str(sum(ProfitList)/len(ProfitList)) + "% Profit Day"
                Prt_and_Slack(message)
                ProfitList = []

    except Exception as e :
        message = str(e) + " is Error Occured"
        Prt_and_Slack(message)
