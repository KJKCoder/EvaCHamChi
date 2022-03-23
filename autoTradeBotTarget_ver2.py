import time
import pyupbit
import datetime
import pandas
import requests
import schedule
from collections import defaultdict

def initialize() :
    global coinlist
    krw_tickers = pyupbit.get_tickers("KRW")
    querystring = {"markets":krw_tickers}

    response = requests.request("GET", url2, headers=headers,params=querystring)
    time.sleep(1)
    df = pandas.DataFrame(response.json()).loc[:,["acc_trade_price_24h","market"]]
    sorteddf = df.sort_values(by=df.columns[0],ascending=False).reset_index(drop=True)

    coinlist = sorteddf.loc[0:20]["market"].values.tolist()
    return True

#매수
def buy(coin, rate): 
    global CoinInfo
    global total
    global NomoneyBool
    krw = get_balance("KRW")
    time.sleep(0.2)
    
    if krw >= total * rate - 100:
        NomoneyBool = False
        upbit.buy_market_order(coin, total * rate)
        time.sleep(0.2)
        CoinInfo[coin]["PriceBuy"] = total * rate
        message = coin + " buy " + str(CoinInfo[coin]["PriceBuy"]) + "won " + str(krw - CoinInfo[coin]["PriceBuy"]) + "left."
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
    amount = get_balance(coin.split("-")[1])
    time.sleep(0.2)
    upbit.sell_market_order(coin, amount) 
    time.sleep(0.2)

    #수익 Output
    message = coin + " is all Sold. Profit: " + str(Calculate_Profit(coin,currentprice*amount)*100) + "%"
    Prt_and_Slack(message)

    total += currentprice*amount*0.995 - CoinInfo[coin]["PriceBuy"]
    CoinInfo[coin]["PriceBuy"] = 0
    return

#수익 계산
def Calculate_Profit(coin, soldprice) :
    return round(soldprice - CoinInfo[coin]["PriceBuy"],4) / CoinInfo[coin]["PriceBuy"]

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
def get_ma15(ticker):
    df = pyupbit.get_ohlcv(ticker, interval="day", count=15)
    time.sleep(0.2)
    ma15 = df['close'].rolling(15).mean().iloc[-1]
    return ma15

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
total = get_balance("KRW") - 5000
time.sleep(0.2)
interval_time = "day"
K_value = 0.5
coinlist = []
CoinInfo = defaultdict(dict)
NomoneyBool = False

print("autotrade start")
Prt_and_Slack("Start Program")

# 자동매매 시작
while True:
    try :
        initialize()
        schedule.run_pending()
        CAUTION_coinlist = get_CAUTION_coinlist()

        start_time = get_start_time("KRW-BTC", interval_time)
        end_time = start_time + datetime.timedelta(days=1) - datetime.timedelta(minutes=3)
        now_time = datetime.datetime.now()

        if start_time < now_time < end_time :
            for curCoin in coinlist :
                target_price = get_target_price(curCoin, interval_time, K_value)
                curPrice = get_current_price(curCoin)
                Mal15 = get_ma15(curCoin)

                if curPrice >= target_price and curPrice > Mal15 and (curCoin in CoinInfo) == False:
                    if check_CAUTION(CAUTION_coinlist,curCoin) == False :
                        buy(curCoin,0.1)
                    else :
                        message = curCoin + " is CAUTION State"
                        Prt_and_Slack(message)

        elif end_time <= now_time :
            for curCoin in CoinInfo :
                curPrice = get_current_price(curCoin)
                CoinInfo["CurPrice"] = curPrice
                time.sleep(0.2)
                sell(curCoin, CoinInfo["CurPrice"])
            
            total = get_balance("KRW") - 5000
            CoinInfo = defaultdict(dict)
            time.sleep(0.2)

    except Exception as e :
        message = str(e) + " is Error Occured"
        Prt_and_Slack(message)