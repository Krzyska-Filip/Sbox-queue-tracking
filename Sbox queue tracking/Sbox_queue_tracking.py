import requests
import steam.webauth as wa
import schedule
import datetime
import time
import win32gui, win32con
import os
from plyer import notification
from requests.api import request
from bs4 import BeautifulSoup
from dotenv import load_dotenv

#Env variables
load_dotenv()

#Urls
steamurl = 'https://steamcommunity.com/openid/login'
sboxurl = 'https://sbox.facepunch.com/dev/.login'

#Steam credentials
user = wa.WebAuth(os.getenv('LOGIN'))
session = user.cli_login(os.getenv('PASSWD'))

#Hide window after sucessful login
CurrentTerminal = win32gui.GetForegroundWindow()
win32gui.ShowWindow(CurrentTerminal , win32con.SW_HIDE)

#Payload for steam in order to get openid
payloadSteam = {
    "openid.ns": "http://specs.openid.net/auth/2.0",
    "openid.mode": "checkid_setup",
    "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
    "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
    "openid.return_to": "https://sbox.facepunch.com/dev/.login",
    "openid.realm": "https://sbox.facepunch.com"
    }

def getInfo():
    #Get openid
    source = user.session.get(steamurl, params=payloadSteam)
    soup = BeautifulSoup(source.text, 'html.parser')
    openidparams = soup.find('input', {'name': 'openidparams'}).get('value')
    nonce = soup.find('input', {'name': 'nonce'}).get('value')

    #Send openid to Sbox
    payloadSbox = {
    "action": "steam_openid_login", 
    "openid.mode": "checkid_setup", 
    "openidparams": openidparams, 
    "nonce": nonce
    }

    source = user.session.post(steamurl, data=payloadSbox, allow_redirects=True)

    #Retrive data from Sbox
    #TODO: add 'under construction' handling
    soup = BeautifulSoup(source.text, 'html.parser')
    errorbox = soup.find('div', {'class': 'errorbox'}).find('div').text
    data = str(errorbox).strip().split()
    position = data[2][:-1]
    position = position.split('/')
    score = data[7][:-1]
    days = data[17]

    now = datetime.datetime.now()
    
    #Save data to file
    #TODO: change to sqlite
    with open("log.txt", 'a', encoding = 'utf-8') as f:
        f.write("{datetime} | {position} | {queue} | {days}\n".format(
                datetime = now.strftime("%m/%d/%Y %H:%M:00"),
                position = position[0],
                queue = position[1],
                score = score,
                days = days
            ))

    #Notification
    #TODO: chage it to pure win32api
    notification.notify(
            #title of the notification,
            title = "SBox Queue Tracker [{time}]".format(
                time = now.strftime("%H:%M")
                ),
            #the body of the notification
            message = "\nPosition: {position}\\{queue}\nDays: {days}".format(
                position = position[0],
                queue = position[1],
                score = score,
                days = days
                ),
            app_icon = "./sbox.ico",
            timeout = 5
        )

#schedule notification every hour at x:00
schedule.every().hour.at(":00").do(getInfo)
while 1:
    schedule.run_pending()
    time.sleep(1)