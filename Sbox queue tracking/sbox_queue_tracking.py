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
con.close()

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
    if(soup.title.text != "Login - s&box"):
        con = sqlite3.connect('terry\'s whitelist.db')
        cur = con.cursor()
        query = " INSERT INTO `history` VALUES (?, ?, ?, ?); "
        data = (-1, -1, -1, now.strftime("%Y-%m-%d %H:%M:00"))
        cur.execute(query, data)
        con.commit()
        con.close()
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
    con.close()

    #Notification
    #TODO: chage it to pure win32api
    notification.notify(
            #title of the notification,
            title = "SBox Queue Tracker [{time}]".format(
                time = now.strftime("%H:%M")
                ),
            #the body of the notification
            message = "\nPosition: {position}\\{queue} | Days: {days}".format(
                position = position[0],
                queue = position[1],
                score = score,
                days = days
                ),
            app_icon = "./sbox.ico",
            timeout = 5
        )

    generatePage()

#Pure JS doesn't support sql that's why I generate html page here.
#Todo: Add last 48h, add only today, add switch to change chart
def generatePage():
    con = sqlite3.connect('terry\'s whitelist.db')
    cur = con.cursor()
    cur.execute("""SELECT * FROM `history` WHERE `datetime` BETWEEN DATETIME('now', 'localtime', 'start of day') AND DATETIME('now', 'localtime');""")
    Today = cur.fetchall()
    cur.execute("""SELECT * FROM `history` WHERE `datetime` BETWEEN DATETIME('now', 'localtime', '-1 day') AND DATETIME('now', 'localtime')""")
    LastDay = cur.fetchall()
    cur.execute("""SELECT * FROM `history` WHERE `datetime` BETWEEN DATETIME('now', 'localtime', '-2 day') AND DATETIME('now', 'localtime')""")
    LastTwoDays = cur.fetchall()
    con.close()

    page = '''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta http-equiv="X-UA-Compatible" content="IE=edge">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="icon" type="image/ico" href="./sbox.ico">
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
            <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300&display=swap" rel="stylesheet">    <title>S&box tracking</title>
            <style>
                .background-media{
                    position:fixed;
                    left:0;
                    right:0;
                    top:0;
                    bottom:0;
                    width:110%;
                    height:110%;
                    background-position:center;
                    background-size:cover;
                    z-index:-10;
                    opacity:.1;
                    filter:blur(20px) sepia(.7) hue-rotate(160deg);
                }
                body{
                    font-family: 'Roboto', sans-serif;
                    box-sizing:border-box;
                    padding:0;
                    margin:0;
                    height:100%;
                    background-color:#0a0a0a !important;
                    color: whitesmoke;
                }
                .header{
                    width: 100%;
                    background-color: #0a0a0a;
                    display: grid;
                    grid-template-areas: 'logo position days';
                    font-size: 1.3em;
                    text-align: center;
                }
                .header > img{
                    grid-area: logo;
                }
                .header > #position{
                    grid-area: position;
                }
                .header > #days{
                    grid-area: days;
                    text-align: right;
                    padding-right: 30px;
                }
                .chart, .analyse{
                    width: 100%;
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 20px;
                    padding: 20px 20px 0px 20px;
                    box-sizing: border-box;
                    margin: 0;
                }
                .positionStats, .queueStats{
                    padding-left: 20px;
                }
                #PositionChartDiv{
                    grid-column: 1 / 2;
                    min-width: 0;
                }
                #QueueChartDiv{
                    grid-column: 2 / 3;
                    min-width: 0;
                }
                #PositionChart, #QueueChart{
                    border-radius: 5px;
                }
        ''' + '''
            </style>
        </head>
        <body>
            <div class="background-media" style="background-image: url( https://files.facepunch.com/garry/77dafb40-9a3e-4af5-9f2c-a76c2bb3c76d.jpg )"></div>
            <div class="header">
                <img src="sbox.ico" width="64" height="64">
                <p id="position">Position: {position}/{queue}</p>
                <p id="days">Days: {days}</p>\
            </div>
        </body>

            <div class="chart">
                <div id="PositionChartDiv"><canvas id="PositionChart"></canvas></div>
                <div id="QueueChartDiv"><canvas id="QueueChart"></canvas></div>
            </div>
            <div class="analyse">
                <div class="positionStats">
                    <p>[Today] Position: {pt}</p>
                    <p>[Last 24h] Position: {p24}</p>
                    <p>[Last 48h] Position: {p48}</p>
                </div>
                <div class="queueStats">
                    <p>[Today] Queue: {qt}</p>
                    <p>[Last 24h] Queue: {q24}</p>
                    <p>[Last 48h] Queue: {q48}</p>
                </div>
            </div>

        '''.format(position=Today[len(Today)-1][0], queue=Today[len(Today)-1][1], days=Today[len(Today)-1][2],
                   pt=Today[len(Today)-1][0] - Today[0][0], qt=Today[len(Today)-1][1] - Today[0][1],
                   p24=LastDay[min(len(LastDay)-1, 23)][0] - LastDay[0][0], q24=LastDay[min(len(LastDay)-1, 23)][1] - LastDay[0][1],
                   p48=LastTwoDays[min(len(LastTwoDays)-1, 47)][0] - LastTwoDays[0][0], q48=LastTwoDays[min(len(LastTwoDays)-1, 47)][1] - LastTwoDays[0][1]) + '''
        <script src="https://cdn.jsdelivr.net/npm/chart.js@3.5.0/dist/chart.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.0.0"></script>
        <script>
        Chart.register(ChartDataLabels);
        var ctx = document.getElementById('PositionChart');
        ctx.style.backgroundColor = 'rgba(245, 245, 245, 0.1)';
        var PositionChart = new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: [{hour}],
                datasets: [
                    {{
                    label: '',
                    data: [{data}],
                    borderColor: 'rgba(54, 162, 235, 1)',
                    backgroundColor: 'rgba(54, 162, 235, 1)'
                    }},
                ]
            }},
            options: {{
                plugins: {{
                    datalabels: {{
                        color: 'rgba(54, 162, 235, 1)',
                        align: 'bottom'
                    }},
                    legend: {{
                        display: false
                    }},
                    title: {{
                        display: true,
                        text: 'Your Position [Last 24h]'
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{
                            // forces step size to be 50 units
                            stepSize: 200
                        }}
                    }}
                }}
            }},
        }});
        var ctx = document.getElementById('QueueChart');
        ctx.style.backgroundColor = 'rgba(245, 245, 245, 0.1)';
        var QueueChart = new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: [{hour2}],
                datasets: [
                    {{
                    label: '',
                    data: [{data2}],
                    borderColor: 'rgba(255, 159, 64, 1)',
                    backgroundColor: 'rgba(255, 159, 64, 1)'
                    }},
                ]
            }},
            options: {{
                plugins: {{
                    datalabels: {{
                        color: 'rgba(255, 159, 64, 1)',
                        align: 'bottom'
                    }},
                    legend: {{
                        display: false
                    }},
                    title: {{
                        display: true,
                        text: 'Queue Length [Last 24h]'
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{
                            // forces step size to be 50 units
                            stepSize: 10000
                        }}
                    }}
                }}
            }},
        }});
        </script>
        </html>
    '''.format(
        hour = str('{},'.format([LastDay[x][3][11:16] for x in range(min(len(LastDay),24))]))[1:-2],
        data = str('{},'.format([LastDay[x][0] for x in range(min(len(LastDay),24))]))[1:-2],
        hour2 = str('{},'.format([LastDay[x][3][11:16] for x in range(min(len(LastDay),24))]))[1:-2],
        data2 = str('{},'.format([LastDay[x][1] for x in range(min(len(LastDay),24))]))[1:-2],
    )
    with open('tracking.html', 'w') as f:
        f.write(page)

#schedule notification every hour at x:00
schedule.every().hour.at(":00").do(getInfo)
while 1:
    schedule.run_pending()
    time.sleep(1)
