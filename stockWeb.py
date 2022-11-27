import ta
import requests
from datetime import timedelta
import certifi
import pymongo
import twstock as t
import yfinance as yf
from plotly.subplots import make_subplots
import plotly.graph_objs as go
import plotly
import json
import numpy as np
import pandas as pd
from flask import Flask, redirect, render_template, request, session
from bson.objectid import ObjectId
import matplotlib.pyplot as plt
import mplfinance as mpf
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from backtesting.test import SMA


client = pymongo.MongoClient(
    "mongodb+srv://root:databasepassword@cluster0.yqjcy.mongodb.net/myFirstDatabase?retryWrites=true&w=majority", tlsCAFile=certifi.where())
db = client.test
db = client.member_system
print("資料庫建立成功")

app = Flask(
    __name__,
    static_folder="static",
    static_url_path="/"
)

# seesion
app.secret_key = "key for secert"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=5)

# 路由:首頁


@app.route('/')
def index():
    return render_template('/signin.html')

# 路由:member_page


@app.route('/member')
def member():
    if 'email' in session:
        return render_template('member.html', nickname=nickname)
    else:
        return redirect("/")

# 路由:signup_page


@app.route('/signuppage')
def signuppage():
    return render_template('signup.html')

# 路由:signup 註冊處理


@app.route('/signup', methods=['POST'])
def signup():
    # 獲取資料
    nickname = request.form['nickname']
    email = request.form['email']
    password = request.form['password']
    birthday = request.form['birthday']
    identity = request.form['identity']
    print(nickname, email, password, identity, birthday)
    collection = db.user  # 連接db.user
    result = collection.find_one({
        "email": email
    })
    if result != None:
        return redirect("/errorpage?msg=信箱已經被註冊")

    collection.insert_one({
        "nickname": nickname,
        "email": email,
        "password": password,
        "identity": identity,
        "birthday": birthday
    })
    return redirect('/')

# 路由:signin_page


@app.route('/signin', methods=['POST'])
def signin():
    global email
    global nickname
    email = request.form['email']
    password = request.form['password']

    # 與資料庫user連線
    collection = db.user

    # 檢查帳密是否相同
    result = collection.find_one({
        "$and": [
            {'email': email},
            {'password': password}
        ]
    })

    # 登入失敗導向失敗頁面
    if result == None:
        return redirect("/errorpage?msg=帳號或密碼錯誤")

    memberdata = collection.find_one({
        "email": email
    })

    print(memberdata['nickname'])
    nickname = memberdata['nickname']
    session['email'] = result['email']
    return render_template('member.html', nickname=nickname)
    # 登入成功導向會員頁面

# 路由:signout_page


@app.route('/shpw')
def shpw():
    return render_template('searchpw.html')


@app.route('/searchpw', methods=['POST'])
def searchpw():
    global email
    email = request.form['email']
    birthday = request.form['birthday']

    # 與資料庫user連線
    collection = db.user

    # 檢查帳密是否相同
    result = collection.find({
        'email': email,
        'birthday': birthday
    })
    for i in result:
        print(i)
    return render_template('searchpw.html', data=i)


@ app.route('/signout')
def signout():
    del session['email']
    return redirect('/')

# 路由:error_page


@ app.route('/errorpage')
def errorpage():
    message = request.args.get("msg", "發生錯誤，請聯繫客服")
    return render_template('errorpage.html', message=message)

# 路由:stockinfo_page


@ app.route('/member/stockinfopage')
def stockInfopage():
    return render_template('stockInfo.html')

# 路由:公司資訊抓取&回傳


@ app.route('/member/stockinfo')
def stockInfo():
    stockid = request.args.get('stockid')
    info = yf.Ticker(stockid).info
    print(info)
    return render_template('stockInfo.html', info=info)

# 股價圖路由 & 處理及回應


@ app.route('/member/stockdraw')
def stockDraw():
    return render_template('stockDraw.html')


@ app.route('/callback/<endpoint>')
def cb(endpoint):
    if endpoint == "getStock":
        return gm(request.args.get('data'), request.args.get('period'), request.args.get('interval'))
    elif endpoint == "getInfo":
        stock = request.args.get('data')
        st = yf.Ticker(stock)
        return json.dumps(st.info)
    else:
        return "Bad endpoint", 400

# 抓取資料&回傳 JSON 資料給 Plotly


def gm(stock, period, interval):
    st = yf.Ticker(stock)

    # 繪製股價圖
    df = st.history(period=(period), interval=interval)
    df = df.reset_index()
    df.columns = ['Date-Time']+list(df.columns[1:])
    df['MA5'] = df['Close'].rolling(5).mean()
    df['MA10'] = df['Close'].rolling(10).mean()
    df['MA20'] = df['Close'].rolling(20).mean()
    df['MA60'] = df['Close'].rolling(60).mean()
    candlestick = go.Candlestick(x=df['Date-Time'],
                                 open=df['Open'],
                                 high=df['High'],
                                 low=df['Low'],
                                 close=df['Close'],
                                 increasing_line_color='red',
                                 decreasing_line_color='green')
    ma5_scatter = go.Scatter(x=df['Date-Time'],
                             y=df['MA5'],
                             line=dict(color='red', width=1),
                             mode='lines',
                             name='MA5')
    ma10_scatter = go.Scatter(x=df['Date-Time'],
                              y=df['MA10'],
                              line=dict(color='orange', width=1),
                              mode='lines',
                              name='MA10')
    ma20_scatter = go.Scatter(x=df['Date-Time'],
                              y=df['MA20'],
                              line=dict(color='blue', width=1),
                              mode='lines',
                              name='MA20')
    ma60_scatter = go.Scatter(x=df['Date-Time'],
                              y=df['MA60'],
                              line=dict(color='green', width=1),
                              mode='lines',
                              name='MA60')
    fig = go.Figure(data=[candlestick, ma5_scatter,
                    ma10_scatter, ma20_scatter, ma60_scatter])

    # 輸出JSON資料圖
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graphJSON


# 路由:order_page
@app.route('/member/orderpage')
def orderpage():
    return render_template('order.html')


@app.route('/member/order', methods=['POST'])
def order():
    buy_day = request.form['buy_day']
    buyorsell = request.form['buyorsell']
    stock_id = request.form['stock_id']
    stockname = request.form['stockname']
    buy_price = request.form['buy_price']
    volume = request.form['volume']

    collection = db.record
    record = collection.insert_one({
        "email": email,
        "record": [{
            'buy_day': buy_day,
            'buyorsell': buyorsell,
            'stock_id': stock_id,
            'stockname': stockname,
            'buy_price': buy_price,
            'volume': volume
        }]
    })
    print(record)
    print(buy_day, buyorsell, stock_id, stockname, buy_price, volume)

    cursor = collection.find({
        "email": email
    })

    return render_template('order.html', list=cursor)


@app.route('/member/search', methods=["POST"])
def search():
    collection = db.record

    cursor = collection.find({
        "email": email
    })
    return render_template('order.html', list=cursor)


# 路由:about_page


@app.route('/member/about')
def about():
    return render_template('about.html')


@app.route('/member/tcone')
def bbandspage():
    return render_template('tcone.html')


@app.route('/member/tconeplt')
def tcone():

    stockid = request.args.get('stockid')
    id = yf.Ticker(stockid)
    df = id.history(period="max", start="2020-01-01")
    print(df)

    # mpf.plot(df)
    # fig = go.Figure(data=[go.Candlestick(
    #     open=df['Open'],
    #     high=df['High'],
    #     low=df['Low'],
    #     close=df['Close'],
    #     increasing_line_color='red',
    #     decreasing_line_color='green'
    # )])

    # fig.show()

    plt.subplot(3, 1, 1)
    period = 20
    df['SMA'] = df['Close'].rolling(window=period).mean()
    df['STD'] = df['Close'].rolling(window=period).std()
    df['Upper'] = df['SMA'] + (df['STD']*2)
    df['Lower'] = df['SMA'] - (df['STD']*2)
    # df['Buy_Signal'] = np.where(df.Lower > df.Close, True, False)
    # df['Sell_Signal'] = np.where(df.Upper < df.Close, True, False)

    # buys = []
    # sells = []
    # open_pos = False

    # for i in range(len(value)):
    #     if value.Lower[i] > value.Close[i]:
    #         if open_pos == False:
    #             buys.append(i)
    #             open_pos = True
    #     elif value.Upper[i] < value.Close[i]:
    #         if open_pos:
    #             sells.append(i)
    #             open_pos = False

    plt.plot(df.Upper, label='Upper', color='green')
    plt.plot(df.Lower, label='Lower', color='green')
    plt.plot(df.SMA, label='SMA', color='yellow')
    plt.plot(df.Close, label='Close', color='blue')
    plt.legend()
    plt.fill_between(df.index, df.Upper,
                     df.Lower, color='grey', alpha=0.2)

    # plt.scatter(value.iloc[buys].index,
    #             value.iloc[buys].Close, marker='^', color='red')
    # plt.scatter(value.iloc[sells].index,
    #             value.iloc[sells].Close, marker='v', color='green')

    plt.subplot(3, 1, 2)
    df['rsi'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()
    plt.plot(df['rsi'])

    plt.subplot(3, 1, 3)
    df['EMA12'] = df.Close.ewm(span=12).mean()
    df['EMA26'] = df.Close.ewm(span=26).mean()
    df['MACD'] = df.EMA12 - df.EMA26
    df['signal'] = df.MACD.ewm(span=9).mean()

    plt.plot(df.signal, label='signal', color='red')
    plt.plot(df.MACD, label='MACD', color='green')
    plt.legend()

    plt.show()
    plt.close()
    return render_template('tcone.html')


@app.route('/member/bt')
def bt():
    return render_template('bt.html')


@app.route('/member/btpage')
def btpage():
    class SmaCrossCons(Strategy):
        fast_days = 5
        slow_days = 15

        def init(self):
            super().init()
            self.fast_line = self.I(SMA, self.data.Close, self.fast_days)
            self.slow_line = self.I(SMA, self.data.Close, self.slow_days)
            self.conservative = True

        def next(self):
            if crossover(self.fast_line, self.slow_line):
                print(
                    f"{self.data.index[-1]} Buy: Price: {self.data.Close[-1]}, Slow: {self.slow_line[-5:]}, Fast: {self.fast_line[-5:]}"
                )
                self.buy()
            elif crossover(self.slow_line, self.fast_line):
                print(
                    f"{self.data.index[-1]} Sell: Price: {self.data.Close[-1]}, Slow: {self.slow_line[-5:]}, Fast: {self.fast_line[-5:]}"
                )
                self.sell()

        @property
        def params(self):
            return self._params

    stockid = request.args.get('stockid')
    id = yf.Ticker(stockid)
    df = id.history(period="max", start="2020-01-01")
    print(df)

    test = Backtest(df, SmaCrossCons, cash=10000000,
                    commission=0.004, exclusive_orders=True)

    result = test.optimize(fast_days=[5, 10, 15], slow_days=[10, 15, 20],
                           constraint=lambda p: p.fast_days < p.slow_days)
    test.plot()

    return render_template('bt.html')


@app.route('/member/news')
def news():
    url = "https://newsapi.org/v2/top-headlines?country=tw&category=business&apiKey=1532527f0e4745ebaabb4627fea2c7c7"
    r = requests.get(url).json()
    case = {
        'articles': r['articles']
    }
    return render_template('news.html', cases=case)


if __name__ == '__main__':
    app.run()
