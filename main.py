
import os
import time
from dotenv import load_dotenv
from opinion_clob_sdk import Client
from opinion_clob_sdk.chain.py_order_utils.model.order import PlaceOrderDataInput
from opinion_clob_sdk.chain.py_order_utils.model.order_type import LIMIT_ORDER
from opinion_clob_sdk.chain.py_order_utils.model.sides import OrderSide
from opinion_clob_sdk.model import TopicStatusFilter
import base64
from decimal import Decimal
import urllib3
import opinion_api.rest
from opinion_clob_sdk.model import TopicType, TopicStatusFilter
from datetime import datetime
import traceback
import time
import logging


global des
global client
global markets
global markets_ids


load_dotenv()
MIN_BUY_VOL = float(os.getenv('MIN_BUY_VOL'))
MAX_BUY_VOL = float(os.getenv('MAX_BUY_VOL'))
BUY_PRICE_MAX = float(os.getenv('BUY_PRICE_MAX'))
BUY_PRICE_MIN = float(os.getenv('BUY_PRICE_MIN'))
BUY_ITEM_AMOUNT = float(os.getenv('BUY_ITEM_AMOUNT'))



def init():
    global client
    global des
    des = []
    proxy = os.getenv('proxy')  # ← 改成你的代理地址
    proxy_manager = urllib3.ProxyManager(proxy)

    # 修改 RESTClientObject，使其所有实例都使用这个代理池
    def _patched_init(self, configuration):
        self.pool_manager = proxy_manager

    opinion_api.rest.RESTClientObject.__init__ = _patched_init
    # Initialize client
    client = Client(
        host='https://proxy.opinion.trade:8443',
        apikey=os.getenv('apikey'),
        chain_id=56,  # BNB Chain mainnet
        rpc_url="https://bsc-dataseed.binance.org",
        private_key=os.getenv('private_key'),
        multi_sig_addr=os.getenv('multi_sig_addr'),
        conditional_tokens_addr=os.getenv('conditional_tokens_addr'),
    )
    getMarket()


def getMarket():
    # Get all active markets
    global markets
    global markets_ids
    markets = {}
    markets_ids = []
    page = 1

    while True:
        markets_response = client.get_markets(
            topic_type=TopicType.BINARY,
            status=TopicStatusFilter.ACTIVATED,
            page=page,
            limit=20
        )

        # Parse the response
        page = page + 1
        items = []
        if markets_response.errno == 0:
            items = markets_response.result.list
        else:
            print(f"Error: {markets_response.errmsg}")
        if len(items) == 0:
            break
        for item in items:
            markets_ids.append(item.market_id)
            markets[item.market_id] = item
    page = 1
    while True:
        markets_response = client.get_markets(
            topic_type=TopicType.CATEGORICAL,
            status=TopicStatusFilter.ACTIVATED,
            page=page,
            limit=20
        )

        # Parse the response
        page = page + 1
        items = []
        if markets_response.errno == 0:
            items = markets_response.result.list
        else:
            print(f"Error: {markets_response.errmsg}")
        if len(items) == 0:
            break
        for item in items:
            markets_ids.append(item.market_id)
            markets[item.market_id] = item






def getDetail(market_id):
    market_detail = client.get_market(market_id)
    market = None
    if market_detail.errno == 0:
        market = market_detail.result.data
    return market


def getOrderBook(tokenId):
    try:
        orderbook = client.get_orderbook(tokenId)
        if orderbook.errno == 0:
            bids = orderbook.result.bids
            asks = orderbook.result.asks
            bids = sorted(bids, key=lambda x: x.price, reverse=True)
            asks = sorted(asks, key=lambda x: x.price)

            if len(bids) == 0 or len(asks) == 0:
                return {'ok': False}
            ask_price = float(asks[0].price)
            bid_price = (float(bids[0].price))
            ask_len = len(asks)
            i = 0
            js = 0
            while i < ask_len - 1:
                js2 = False
                if float(asks[i + 1].price) - float(asks[i].price) > 0.05:
                    ask_price = float(asks[i + 1].price)
                    js2 = True
                    if js == 0:
                        js = 1
                if float(asks[i].price) * float(asks[i].size) < 100:
                    ask_price = float(asks[i + 1].price)
                    js2 = True
                    if js == 0:
                        js = 1
                if not js2:
                    break
                i = i+1
            return { 'bid': bid_price, 'ask': ask_price, 'amount': float(bids[0].size) * float(bids[0].price),'ok':True}
    except Exception as e:
        print(f"  (Skip if token_id not set: {e})")


def getMyOrder():
    # Get all open orders
    time.sleep(3)
    page = 1
    rs = {}
    left = 1
    while left > 0:
        response = client.get_my_orders(status="1", limit=20, page=page)
        left = response.result.total - (page * 20)
        page = page + 1
        if response.errno == 0:
            orders = response.result.list
            if orders != None:
                for order in orders:
                    if True:
                        add = True
                        market = getDetail(order.market_id)
                        tokenId = ''
                        if order.outcome_side == 1:
                            tokenId = market.yes_token_id
                        if order.outcome_side == 2:
                            tokenId = market.no_token_id
                        price =getOrderBook(tokenId)
                        if not price['ok']:
                            continue
                        if order.side == 1 and (abs(float(order.price) - price['bid']) >= 0.001):
                            #买入的订单
                            print(f"取消{order.market_title}订单重新下单:报价更新")
                            cancel(order.order_id)
                            add = False
                        if order.side == 2 and (float(order.price) > price['ask']):
                            print(f"取消{order.market_title}订单重新下单:报价更新")
                            cancel(order.order_id)
                            add = False
                        if add:
                            rs[str(order.market_id)] = order
    return rs



def placeOrder(marketId, tokenId, side, price, amount, title, cb):
    if side == OrderSide.BUY:
        ye = getBalances(1)
        amount = BUY_ITEM_AMOUNT
        if ye < amount:
            #print(f'{title}余额不足,当前余额{ye}')
            return 0
    order = PlaceOrderDataInput(
        marketId=marketId,
        tokenId=tokenId,
        side=side,
        orderType=LIMIT_ORDER,
        price=str(round(float(price), 3)),  # Buy at $0.55 or better
        makerAmountInQuoteToken= amount
    )
    result = client.place_order(order, check_approval=True)
    if result.errno == 0:
        if side == OrderSide.SELL:
            RED = "\033[31m"
            GREEN = "\033[32m"
            RESET = "\033[0m"
            cj = (float(amount) / float(price)) * (float(price) - float(cb))
            if cj > 0:
                print(f"下单成功:卖出{title}:{amount}u:均价：{price}:盈利{GREEN}{cj}{RESET}")
            else:
                print(f"下单成功:卖出{title}:{amount}u:均价：{price}:亏损{RED}{cj}{RESET}")
        if side == OrderSide.BUY:
            print(f"下单成功:买入{title}:{amount}u:均价：{price}")
    else:
        if result.errno == 10604:
            return
        print(result.errmsg)
        time.sleep(3)
        placeOrder(marketId, tokenId, side, price, Decimal(amount - 1), title, 0)
    return 1


def cancel(id):
    result = client.cancel_order(order_id=id)

def getMyPosition():
    page = 1
    left = 1
    rs = {}
    while left > 0:
        response = client.get_my_positions(page=page, limit=20)
        left = response.result.total - (page * 20)
        page = page + 1
        if response.errno == 0:
            for item in response.result.list:
                if float(item.shares_owned) > 10:
                    rs[str(item.market_id)] = item
    return rs





def bot():
    global markets_ids
    RED = "\033[31m"
    GREEN = "\033[32m"
    BLUE = "\033[33m"
    RESET = "\033[0m"
    myPosition = getMyPosition()
    orders = getMyOrder()
    for id in markets_ids:
        market = markets[id]
        #筛选一下
        if abs(market.cutoff_at - time.time()) < 15 * 24 * 60 * 60:
            # 马上快结束的风险大跳过
            continue
        if name_check(market.market_title):
            continue
        if market.child_markets is None:
            #无分类市场
            # 判断订单是否已经存在
            if str(id) in orders.keys():
                if str(id) in myPosition.keys() and orders[str(id)].side_enum == 'Sell':
                    cj = (float(orders[str(id)].price) - float(myPosition[str(id)].avg_entry_price)) * (float(orders[str(id)].order_shares))
                    if cj > 0:
                        print(f'{market.market_title}已经存在订单,{GREEN}盈利{cj}{RESET}')
                    else:
                        print(f'{market.market_title}已经存在订单,{RED}亏损{cj}{RESET}')
                    continue
                else:
                    print(f'{market.market_title}已经存在订单,买入价格:{BLUE}{orders[str(id)].price}{RESET}')
                    continue
            else:
                if str(id) in myPosition.keys() and float(myPosition[str(id)].shares_owned) > 10:
                    # 卖出订单
                    sell(myPosition[str(id)], myPosition[str(id)], market.market_title)
                    continue
            market = getDetail(id)
            if MIN_BUY_VOL < float(market.volume) < MAX_BUY_VOL:
                #买入
                ob = get_token(market)
                if not ob['ok']:  # 报价不可用  不进行交易
                    continue
                placeOrder(market.market_id, ob['token_id'], OrderSide.BUY, str(ob['price']), Decimal('50'), market.market_title,0)
        else:
            go = True
            #判断订单是否已经存在
            for item in market.child_markets:
                if str(item.market_id) in orders.keys():
                    if str(item.market_id) in myPosition.keys() and orders[str(item.market_id)].side_enum == 'Sell':
                        cj = (float(orders[str(item.market_id)].price) - float(myPosition[str(item.market_id)].avg_entry_price) ) * (float(orders[str(item.market_id)].order_shares))
                        if cj > 0:
                            print(f'{market.market_title}{item.market_title}已经存在订单,{GREEN}盈利{cj}{RESET}')
                        else:
                            print(f'{market.market_title}{item.market_title}已经存在订单,{RED}亏损{cj}{RESET}')
                    else:
                        print(f'{market.market_title}{item.market_title}已经存在订单,买入价格:{BLUE}{orders[str(item.market_id)].price}{RESET}')
                    go = False
                else:
                    if str(item.market_id) in myPosition.keys() and float(myPosition[str(item.market_id)].shares_owned) > 10:
                        # 卖出订单
                        go = False
                        sell(myPosition[str(item.market_id)], item, market.market_title + ":" + item.market_title)
            #有分类市场
            if go:
                for item in market.child_markets:
                    itemDetail = getDetail(item.market_id)
                    if MAX_BUY_VOL > float(itemDetail.volume) > MIN_BUY_VOL:
                        ob = get_token(itemDetail)
                        if not ob['ok']:  #报价不可用  不进行交易
                            continue
                        placeOrder(item.market_id, ob['token_id'], OrderSide.BUY, str(ob['price']),Decimal('50'), market.market_title, 0)
                        break


def sell(position, market, title):
    if float(position.shares_owned) > 10:
        ob = getOrderBook(position.token_id)
        if not ob['ok']:
            return
        price = ob['ask']
        cb = Decimal(position.avg_entry_price) * Decimal(float(position.shares_owned))
        amount = Decimal(price) * Decimal(float(position.shares_owned))  #卖出价格
        return placeOrder(market.market_id, position.token_id, OrderSide.SELL,
                    str(price), Decimal(amount - 1), title, position.avg_entry_price)


def name_check(name):
    if 'Bitcoin' in name:
        return True
    return False

def get_token(market):
    rs = {'ok': True}
    ob = getOrderBook(market.yes_token_id)
    ob2 = getOrderBook(market.no_token_id)
    if ob['ok'] == False or ob2['ok'] == False:
        return {'ok': False}

    if ob['bid'] > ob2['bid']:
        rs['price'] = ob['bid']
        rs['token_id'] = market.yes_token_id
        rs['amount'] = ob['amount']
        if abs(ob['bid'] - ob['ask']) > 0.2:
            return {'ok': False}
    else:
        rs['price'] = ob2['bid']
        rs['token_id'] = market.no_token_id
        rs['amount'] = ob2['amount']
        if abs(ob2['bid'] - ob2['ask']) > 0.2:
            return {'ok': False}
    if rs['price'] > BUY_PRICE_MAX or rs['price'] < BUY_PRICE_MIN:
        return {'ok': False}
    if rs['amount'] > 1000:
        return {'ok': False}
    return rs







def getBalances(type):
    response = client.get_my_balances()
    if response.errno == 0:
        balance_data = response.result
        balances = balance_data.balances[0]  # List of quote token balances
        return float(balances.available_balance)

logging.getLogger().setLevel(logging.ERROR)

if __name__ == '__main__':
    init()
    while True:
        try:
            bot()
            now = datetime.now()
            print(f'--------------------{now}-------------------------')
            time.sleep(150)
        except Exception as e:
            traceback.print_exc()

