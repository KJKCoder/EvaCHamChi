import requests
import time
def post_message(token, channel, text):
    response = requests.post("https://slack.com/api/chat.postMessage",
        headers={"Authorization": "Bearer "+token},
        data={"channel": channel,"text": text}
    )
myToken = "xoxb-3135357024800-3124236991793-2DBjbnqB3Zbf5quyiuwUO2Vk"
 

while(True) : 
    post_message(myToken,"#cointrade","Run Program Success")
    time.sleep(600)