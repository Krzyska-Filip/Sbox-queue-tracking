import requests
import steam.webauth as wa
import schedule
import datetime
import time
import win32gui, win32con
import os
import sqlite3
from plyer import notification
from requests.api import request
from bs4 import BeautifulSoup
from dotenv import load_dotenv

#Create sqlite
con = sqlite3.connect('terry\'s whitelist.db')
cur = con.cursor()
cur.execute('''
    CREATE TABLE IF NOT EXISTS `history`(
        `curPosition` INT,
        `queueLength` INT,
        `daysRemaining` INT,
        `datetime` TEXT
    ); ''')
con.commit()

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
    now = datetime.datetime.now()
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
    soup = BeautifulSoup(source.text, 'html.parser')

    #If site doesn't work insert -1 into table
    #Don't know if it works [It should]
    if(soup.title != "Login - s&box"):
        con = sqlite3.connect('terry\'s whitelist.db')
        cur = con.cursor()
        query = " INSERT INTO `history` VALUES (?, ?, ?, ?); "
        data = (-1, -1, -1, now.strftime("%Y-%m-%d %H:%M:00"))
        cur.execute(query, data)
        con.commit()
        return

    errorbox = soup.find('div', {'class': 'errorbox'}).find('div').text
    data = str(errorbox).strip().split()
    position = data[2][:-1].replace(',', '')
    position = position.split('/')
    score = data[7][:-1]
    days = data[17]
    
    #Save to db
    con = sqlite3.connect('terry\'s whitelist.db')
    cur = con.cursor()
    query = " INSERT INTO `history` VALUES (?, ?, ?, ?); "
    data = (position[0], position[1], days, now.strftime("%Y-%m-%d %H:%M:00"))
    cur.execute(query, data)
    con.commit()

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