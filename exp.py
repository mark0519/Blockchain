"""
Author: 孙嘉骏 2020211896
Date : 2021/6/6
Version : 1.3.0
Github : https://github.com/mark0519/Blockchain
"""

''' Double Spending Attacks '''

import requests
import json


url_1 = "http://localhost:5000/"  # 卖家
url_2 = "http://localhost:5001/"  # 买家(Hacker)


'''发送post请求，卖家与买家相互注册'''
url_1_register = url_1+'nodes/register'
url_2_register = url_2+'nodes/register'

data1 = {"nodes": [url_2]}
data2 = {"nodes": [url_1]}

req_1 = requests.post(url_1_register, json = data1)
req_2 = requests.post(url_2_register, json = data2)
print(json.loads(req_1.text))
print(json.loads(req_2.text))


'''发送get请求,卖家买家分别进行一些挖矿以获得初始货币'''
url_1_mine = url_1+'mine'
url_1_resolve = url_1+'nodes/resolve'
url_2_mine = url_2+'mine'
url_2_resolve = url_2+'nodes/resolve'
url_1_chain = url_2+'chain'
url_2_chain = url_2+'chain'

'''解决冲突'''
req = requests.get(url_1_resolve)
req = requests.get(url_2_resolve)

recipient_address = ""

for i in range(10):
    req_1 = requests.get(url_1_mine)  # 发送mine请求
    recipient_address = req_1.json()['account']
    if i == 9:
        print("After mine by Seller:")
        print("   Seller account:" + str(req_1.json()['account']))
        print("   Seller wallet :" + str(req_1.json()['wallet']))

req_1 = requests.get(url_1_resolve)
req_2 = requests.get(url_2_resolve)

sender_address = ""

for i in range(15):
    req_2 = requests.get(url_2_mine)  # 发送mine请求
    sender_address = req_2.json()['account']
    if i == 14:
        print("After mine by Buyer:")
        print("   Buyer account: " + str(req_2.json()['account']))
        print("   Buyer wallet : " + str(req_2.json()['wallet']))

'''解决冲突'''
req_1 = requests.get(url_1_resolve)
req_2 = requests.get(url_2_resolve)

'''获取全部区块'''
req_1 = requests.get(url_1_chain)
req_2 = requests.get(url_2_chain)

print("For Seller`s Blockchain:")
print("   "+req_1.text)
print("   Length: " + str(req_1.json()['length'])) # 检查长度
print("\n=============\n")
print("For Buyer`s Blockchain:")
print("   "+req_2.text)
print("   Length: " + str(req_2.json()['length'])) # 检查长度


'''卖家向买家发起交易'''
data3 = {"sender": sender_address, "recipient": recipient_address, "amount": "8"}
url_1_new = url_1 + "new/transaction"
req = requests.post(url_1_new, json = data3)
print("\nCreate transaction:")
print(data3)
print(req.text)

'''刷新Blockchain，同时进行Double Spending Attacks'''
req_1 = requests.get(url_1_mine)
req = requests.get(url_1_resolve)

req_1 = requests.get(url_1_mine) # Double Spending Attacks前检查卖家的账户余额
print("After mine by Seller:")
print("   Seller account:" + str(req_1.json()['account']))
print("   Seller wallet :" + str(req_1.json()['wallet']))

'''启动攻击'''
for i in range(30):
    req = requests.get(url_2_mine) # 利用大量算力延长自己的区块超过卖家区块长度，在超过之前不广播
'''Double Spending Attacks'''
req = requests.get(url_2_resolve) # 广播结果
req = requests.get(url_1_resolve) # 广播结果

'''结果：'''
print("==== Double Spending Attacks ====")
print("=========")
print("After mine by Seller:")
req_1 = requests.get(url_1_mine)
print("   Seller account:" + str(req_1.json()['account']))
print("   Seller wallet :" + str(req_1.json()['wallet'])) # 卖家的账户余额
print("=========")
print("After mine by Buyer(Hacker):")
req_2 = requests.get(url_2_mine)
print("   Buyer account:" + str(req_2.json()['account']))
print("   Buyer wallet :" + str(req_2.json()['wallet'])) # 买家（黑客）的账户余额
print("=========")

