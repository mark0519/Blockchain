"""
Author: 孙嘉骏 2020211896
Date : 2021/6/6
Version : 1.3.0
Github : https://github.com/mark0519/Blockchain
"""


"""

运行:  python blockchain.py

cURL方式操作{

    挖矿（创建新的Block）:  [GET] localhost:5000/mine

    查看链上全部区块 : [GET] localhost:5000/chain

    创建一笔交易: [POST] localhost:5000/new/transaction
        [POST] JSON文件
        {
            "sender": "sender_address" ,
            "recipient": "recipient_address" ,
            "amount": num #交易数量
        }
        例如 : { "sender": "faf5c2ad054640499a18688a55d30499" ,
                "recipient": "any_other_address" ,
                "amount": 8.8 }
            
    注册新节点: [POST] localhost:5000/nodes/register
        [POST] JSON文件
        {   
            ”nodes“: ["new_nodes_ip:port"]  
        }
        例如 : { "nodes":["127.0.0.1:5001"] }
    
    更新区块链(解决节点冲突): [GET] localhost:5000/nodes/resolve
}
"""

"""
GUI方式操作{

    chrome 内核浏览器访问 localhost:5000
    
    按页面提示操作
    
}

"""

import hashlib
import json

from time import time
from urllib.parse import urlparse
from uuid import uuid4
from argparse import ArgumentParser

import requests

from flask import Flask, jsonify, request, render_template


class Blockchain(object):
    # 初始化
    def __init__(self):
        self.chain = []  # 此列表表示区块链对象本身。
        self.currentTransaction = []  # 此列表用于记录目前在区块链网络中已经经矿工确认合法的交易信息，等待写入新区块中的交易信息。
        self.nodes = set()  # 建立一个无序元素集合。此集合用于存储区块链网络中已发现的所有节点信息
        # 创建创世区块
        self.new_block(proof=100, previous_hash=1)

    # 注册节点
    def register_node(self, address):
        """
        注册一个新节点
        :param address: 节点地址 示例：'http://127.0.0.1：5001'
        """
        # 检查节点的格式，通过urlparse方法将这个节点的url分割成六个部分
        parsed_url = urlparse(address)

        # 如果网络地址不为空，那么就添加没有http://之类修饰的纯的地址，如：www.baidu.com
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)

        # 如果网络地址为空，那么就添加相对Url的路径
        elif parsed_url.path:
            # Accepts an URL without scheme like '192.168.0.5:5000'.
            self.nodes.add(parsed_url.path)

        # 其他情况
        else:
            raise ValueError('Invalid URL')  # 说明这是一个非标准的Url

    # 验证区块链有效性,根据正确的区块链修正钱包余额
    def valid_chain(self, chain):
        """
        验证区块链有效性，根据正确的区块链修正钱包余额
        :param chain: blockchain
        :return: 是否合法
        """
        # 这里取得的是创世区块，意味着必须从头检查整个区块链上从创世区块到链上最后一个区块为止的所有区块的链接关系
        last_block = chain[0]

        # 引入全局变量钱包余额和钱包地址
        global wallet
        global node_identifier

        # 如果区块链检查全部正确且原链被替换的情况下才更新钱包余额
        new_wallet = 0

        # 下面的while循环就是为了检查链上每一个区块与其连接的前一个区块是否合法相关，通过检查 previous_hash 来判断
        current_index = 1
        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            last_block_hash = self.hash(last_block)

            # 检查块的哈希是否正确
            if block['previous_hash'] != last_block_hash:
                return False  # 如果发现当前在检查的区块的previous_hash值与它实际连接的前一区块的hash值不同，则证明此链条有问题，终止检查

            # 检查工作量证明是否正确
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            # 如果区块中存在交易消息
            if len(block['transactions']) != 0:
                for i in range(len(block['transactions'])):
                    # 存在以自己钱包地址为发送者的交易
                    if block['transactions'][i]['sender'] == node_identifier:
                        new_wallet = new_wallet - int(block['transactions'][i]['amount'])
                    # 存在以自己钱包地址为接收者的交易
                    if block['transactions'][i]['recipient'] == node_identifier:
                        new_wallet = new_wallet + int(block['transactions'][i]['amount'])

            last_block = block  # 让当前区块变成前一个区块，以迭代到一下次循环
            current_index += 1  # 让下一个区块区区块号+1

        # 更新钱包余额
        wallet = new_wallet
        return True

    # 解决冲突
    def resolve_conflicts(self):
        """
        解决区块链节点之间的冲突，用网络中最长的链替换我们的链。
        :return: 被替换返回True。否则返回False
        """
        neighbours = self.nodes
        new_chain = None

        # 本节点的存储的区块链条的长度（即有多少个区块）
        max_length = len(self.chain)

        # 获取所有已知区块链网络中的节点中存储的区块链条，并分析其是否比本节点的链条长度要长
        for node in neighbours:
            # 到每个节点的chain页面去获取此节点的区块链条信息，返回结果包含了一个chain对象本身和它的长度信息
            response = requests.get(f'http://{node}/chain')

            # HTTP状态码等于200表示请求成功
            if response.status_code == 200:
                length = response.json()['length']  # 通过json类把返回的对象取出来
                chain = response.json()['chain']

                # 如果此节点的区块链长度比本节点区块链长度长，且链条合法，则证明是值得覆盖本节点链条的合法链条
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # 用找到的比本节点区块链链条长的链条覆盖本节点的旧链条，返回True
        if new_chain:
            self.chain = new_chain
            return True

        # 如果没有发现别的节点上的链条比本节点的链条更长，那么就返回False
        return False

    # 创建一个新的区块，并将其加入到链中
    def new_block(self, proof, previous_hash=None):
        """
        生成新块
        :param proof: <int> 工作量证明算法给出的证明
        :param previous_hash: (Optional) <str> 上一个区块的哈希值
        :return: <dict> 新区快
         """
        block = {
            'index': len(self.chain) + 1,  # 区块编号
            'timestamp': time(),  # 时间戳字符串
            'transactions': self.currentTransaction,  # 交易信息
            'proof': proof,  # 矿工通过算力证明（工作量证明）成功得到的Number Once值，证明其合法创建了一个区块（当前区块）
            'previous_hash': previous_hash or self.hash(self.chain[-1])  # 前一个区块的哈希值
        }

        # 重置当前事务列表
        '''
        因为已经将待处理（等待写入下一下新创建的区块中）交易信息列表（变量是：transactions）
        中的所有交易信息写入了区块并添加到区块链末尾，则此处清除此列表中的内容'
        '''
        self.currentTransaction = []
        # 将当前区块添加到区块链末端
        self.chain.append(block)
        return block

    # 创建新交易
    def new_transaction(self, sender, recipient, amount):
        # 向交易列表中添加一个新的交易
        """
        生成新交易信息，此交易信息将加入到下一个待挖的区块中
        :param sender: 发送方地址
        :param recipient:  接收方地址
        :param amount: 数量
        :return: 需要将交易记录在下一个区块中
        """
        self.currentTransaction.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })

        # 下一个待挖的区块中
        return self.last_block['index'] + 1

    # 计算hash
    @staticmethod
    def hash(block):
        # 根据一个区块 来生成这个区块的哈希值
        """
        :param block: <dict> Block
        :return: <str> 转化为json编码格式之后hash，最后以16进制的形式输出
        """

        # 我们必须确保字典是有序的，否则我们会有不一致的哈希值
        # sort_keys=True
        '''
        首先通过json.dumps方法将一个区块打散，并进行排序（保证每一次对于同一个区块都是同样的排序）
        这个时候区块被转换成了一个json字符串
        然后，通过json字符串的encode()方法进行编码处理。
        其中encode方法有两个可选形参，第一个是编码描述字符串，另一个是预定义错误信息
        默认情况下，编码描述字符串参数就是：默认编码为 'utf-8'。此处就是默认编码为'utf-8'
        '''
        block_string = json.dumps(block, sort_keys=True).encode()

        return hashlib.sha256(block_string).hexdigest()  # 以16进制的形式输出

    # 区块链的最后一个区块
    @property
    def last_block(self):
        return self.chain[-1]  # 区块链的最后一个区块

    # 工作量证明
    def proof_of_work(self, lastProof):
        """
        简单的工作量证明:
         - 查找一个 p' 使得 hash(pp') 以4个0开头
         - p 是上一个块的证明,  p' 是当前的证明
        :param lastProof: <int> 上一个块的证明
        :return: <int> 当前的证明
        """

        # #下面通过循环来使proof的值从0开始每次增加1来进行尝试，直到得到一个符合算法要求的proof值为止
        proof = 0
        while self.valid_proof(lastProof, proof) is False:
            proof += 1  # 如果得到的proof值不符合要求，那么就继续寻找。
        # 返回这个符合算法要求的proof值
        return proof

    # 此函数是工作量证明的附属部分，用于检查哈希值是否满足挖矿条件
    @staticmethod
    def valid_proof(lastProof, proof):
        """
        验证证明: 是否hash(last_proof, proof)以4个0开头?
        :param lastProof: <int> 上一个块的证明 lastProof
        :param proof: <int> 是当前的证明
        :return: <bool> 是否匹配
        """
        # 根据传入的参数proof来进行尝试运算，得到一个转码为utf-8格式的字符串
        guess = f'{lastProof}{proof}'.encode()
        # 将此字符串（guess）进行sha256方式加密，并转换为十六进制的字符串
        guessHash = hashlib.sha256(guess).hexdigest()
        # 验证该字符前4位是否为0，如果符合要求，就返回True，否则 就返回False
        return guessHash[:4] == '0000'


# 实例化节点，加载 Flask 框架
app = Flask(__name__)


# 为我们的节点创建一个随机名称
node_identifier = str(uuid4()).replace('-', '')


# 钱包余额
wallet = 0


# 实例化 Blockchain 类
blockchain = Blockchain()


# index界面
@app.route('/')
def index():
    return render_template('index.html')


# 创建 new 端点,填写POST内容
@app.route('/new', methods=['GET'])
def new_for_post():
    return render_template('new_for_post.html')


# 创建 new/transaction 端点，创建交易，这是一个 POST 请求，用它来发送数据
@app.route('/new/transaction', methods=['POST'])
# 新的交易
def new_transaction():
    # 将请求参数做了处理，得到的是字典格式的，因此排序会打乱依据字典排序规则
    values = request.get_json()

    # 检查所需字段是否在过账数据中
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400  # HTTP状态码等于400表示请求错误

    # 计算钱包余额
    global node_identifier
    global wallet
    if values['sender'] == node_identifier:  # 此账户是交易的发出者
        if (wallet - int(values['amount'])) < 0:  # 余额不足
            return 'Insufficient balance', 400
        wallet = wallet - int(values['amount'])

    if values['recipient'] == node_identifier:  # 此账户是交易的接受者
        wallet = wallet + int(values['amount'])

    # 创建新交易
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])
    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201


# 创建 /mine 端点，这是一个GET请求
@app.route('/mine', methods=['GET'])
# 挖矿
def mine():
    # 我们运行工作证明算法来获得下一个证明
    last_block = blockchain.last_block  # 取出区块链现在的最后一个区块
    last_proof = last_block['proof']  # 取出这最后 一个区块的哈希值（散列值）
    proof = blockchain.proof_of_work(last_proof)  # 获得了一个可以实现优先创建（挖出）下一个区块的工作量证明的proof值。

    # 由于找到了证据，我们会收到一份奖励
    # sender为“0”，表示此节点已挖掘了一个新货币
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
    )

    # 钱包余额增加
    global wallet
    wallet = wallet + 1

    # 将新块添加到链中打造新的区块
    previous_hash = blockchain.hash(last_block)  # 取出当前区块链中最长链的最后一个区块的Hash值，用作要新加入区块的前导HASH（用于连接）
    block = blockchain.new_block(proof, previous_hash)  # 将新区快添加到区块链最后

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'account': node_identifier,
        'wallet': wallet,
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200


# 创建 /chain 端点，它是用来返回整个 Blockchain类
@app.route('/chain', methods=['GET'])
# 将返回本节点存储的区块链条的完整信息和长度信息。
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


# 创建 nodes 端点,填写POST内容
@app.route('/nodes', methods=['GET'])
# 用于加载 register 和 resolve 端点
def nodes():
    return render_template('nodes.html')


# 创建 /nodes/register 端点，这是一个POST请求
@app.route('/nodes/register', methods=['POST'])
# 注册节点，应POST一个JSON，需要至少一个包含“nodes”作为新节点
def register_nodes():
    values = request.get_json()
    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201


# 创建 /nodes/resolve 端点，这是一个GET请求
@app.route('/nodes/resolve', methods=['GET'])
# 添加节点解决冲突的路由
def consensus():
    # 解决多个区块链网络节点间的节点冲突，更新为区块链网络中最长的那条链条-
    replaced = blockchain.resolve_conflicts()
    # 如果使用的本节点的链条，那么返回如下
    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'chain': blockchain.chain
        }
    # 如果更新别的节点的链条，那么返回如下：
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return jsonify(response), 200  # jsonify()序列化把返回信息变成字符


if __name__ == '__main__':
    parser = ArgumentParser()  # 创建一个参数接收的解释器，由此对象（这里是：parser)来负责解释参数信息
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()  # 通过parse_args()方法尝试对收到的参数关键字进行解释
    port = args.port  # 从args对象中取出其中的参数关键字--port 参数的内容，也可能是获取到预设的默认值
    app.run(host='0.0.0.0', port=port)
