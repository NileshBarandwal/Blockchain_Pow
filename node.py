import os
import json
import time
import hashlib
import requests
import socket
from flask import Flask, jsonify, request, render_template
from threading import Thread, Lock
from uuid import uuid4

app = Flask(__name__, template_folder='ui/templates', static_folder='ui/static')
app.config['BLOCKCHAIN_DATA_DIR'] = 'blockchain_data'
app.config['CHAIN_FILE'] = os.path.join(app.config['BLOCKCHAIN_DATA_DIR'], 'chain.json')
app.config['MINERS_FILE'] = os.path.join(app.config['BLOCKCHAIN_DATA_DIR'], 'miners.json')

def get_lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

NODE_ID = str(uuid4())
NODE_ADDRESS = f"http://{get_lan_ip()}:{os.environ.get('PORT', 5000)}"

class Block:
    def __init__(self, index, transactions, previous_hash):
        self.index = index
        self.timestamp = time.time()
        self.transactions = transactions.copy()
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = ""
        self.block_size = 0
        self.tx_count = len(transactions)
        self.block_header = {
            "version": 1,
            "prevBlockHash": previous_hash,
            "merkleRoot": self.calculate_merkle_root(),
            "timestamp": self.timestamp,
            "bits": "1d00ffff",
            "nonce": 0,
            "blockHash": ""
        }
        self.mine_block()

    def calculate_merkle_root(self):
        tx_hashes = [str(tx) for tx in self.transactions]
        return hashlib.sha256(''.join(tx_hashes).encode()).hexdigest()

    def calculate_hash(self):
        block_string = f"{self.index}{self.block_header['prevBlockHash']}{self.block_header['merkleRoot']}{self.block_header['timestamp']}{self.nonce}".encode()
        return hashlib.sha256(block_string).hexdigest()

    def mine_block(self):
        while not self.hash.startswith("0000"):
            self.nonce += 1
            self.hash = self.calculate_hash()
        self.block_size = len(str(self.__dict__))
        self.block_header['blockHash'] = self.hash
        self.block_header['nonce'] = self.nonce

class Blockchain:
    def __init__(self):
        self.chain = []
        self.transactions = []
        self.miners = {}
        self.lock = Lock()
        self.load_data()
        
        if not self.chain:
            self.create_genesis_block()

    def load_data(self):
        os.makedirs(app.config['BLOCKCHAIN_DATA_DIR'], exist_ok=True)
        try:
            with open(app.config['CHAIN_FILE'], 'r') as f:
                self.chain = [Block(**block) for block in json.load(f)]
        except (FileNotFoundError, json.JSONDecodeError):
            self.chain = []
        try:
            with open(app.config['MINERS_FILE'], 'r') as f:
                self.miners = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.miners = {}

    def save_data(self):
        with open(app.config['CHAIN_FILE'], 'w') as f:
            json.dump([b.__dict__ for b in self.chain], f)
        with open(app.config['MINERS_FILE'], 'w') as f:
            json.dump(self.miners, f)

    def create_genesis_block(self):
        genesis = Block(0, [], "0")
        self.chain.append(genesis)
        self.save_data()

    def add_transaction(self, sender, receiver, amount):
        with self.lock:
            self.transactions.append({
                "sender": sender,
                "receiver": receiver,
                "amount": amount,
                "timestamp": time.time()
            })
        self.broadcast_transaction(sender, receiver, amount)

    def broadcast_transaction(self, sender, receiver, amount):
        for miner in list(self.miners.keys()):
            try:
                requests.post(
                    f"{miner}/receive_transaction",
                    json={"sender": sender, "receiver": receiver, "amount": amount},
                    timeout=2
                )
            except:
                self.remove_miner(miner)

    def register_miner(self, address):
        if address != NODE_ADDRESS and address not in self.miners:
            self.miners[address] = time.time()
            self.save_data()

    def remove_miner(self, address):
        if address in self.miners:
            del self.miners[address]
            self.save_data()

    def mine_new_block(self):
        if self.transactions:
            last_block = self.chain[-1]
            new_block = Block(
                index=len(self.chain),
                transactions=self.transactions,
                previous_hash=last_block.hash
            )
            with self.lock:
                self.chain.append(new_block)
                self.transactions.clear()
                self.save_data()
                self.broadcast_block(new_block)

    def broadcast_block(self, block):
        for miner in list(self.miners.keys()):
            try:
                requests.post(f"{miner}/receive_block", json=block.__dict__, timeout=2)
            except:
                self.remove_miner(miner)

blockchain = Blockchain()

@app.template_filter('datetime')
def format_datetime(value):
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(value))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    data = request.json
    blockchain.add_transaction(data['sender'], data['receiver'], data['amount'])
    return jsonify({"message": "Transaction added to pool"}), 201

@app.route('/chain', methods=['GET'])
def full_chain():
    return jsonify([b.__dict__ for b in blockchain.chain]), 200

@app.route('/miners', methods=['GET'])
def list_miners():
    active_miners = [m for m, t in blockchain.miners.items() if time.time() - t < 30]
    return jsonify({"active_miners": active_miners}), 200

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    blockchain.register_miner(data['address'])
    return jsonify({"peers": list(blockchain.miners.keys())}), 201

@app.route('/receive_block', methods=['POST'])
def receive_block():
    block_data = request.json
    new_block = Block(
        block_data['index'],
        block_data['transactions'],
        block_data['previous_hash']
    )
    new_block.__dict__.update(block_data)
    
    with blockchain.lock:
        if new_block.index == len(blockchain.chain):
            blockchain.chain.append(new_block)
            blockchain.save_data()
    return jsonify({"message": "Block added"}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "active", "address": NODE_ADDRESS}), 200

def mining_process():
    while True:
        blockchain.mine_new_block()
        time.sleep(5)

def peer_sync():
    while True:
        for miner in list(blockchain.miners.keys()):
            try:
                requests.get(f"{miner}/health", timeout=2)
                blockchain.miners[miner] = time.time()
            except:
                blockchain.remove_miner(miner)
        time.sleep(15)

if __name__ == '__main__':
    # Auto-register with bootstrap node
    if 'BOOTSTRAP_NODE' in os.environ and os.environ['BOOTSTRAP_NODE'] != NODE_ADDRESS:
        try:
            requests.post(
                f"{os.environ['BOOTSTRAP_NODE']}/register",
                json={"address": NODE_ADDRESS},
                timeout=5
            )
            print(f"Registered with bootstrap node: {os.environ['BOOTSTRAP_NODE']}")
        except Exception as e:
            print(f"Bootstrap registration failed: {str(e)}")

    # Start services
    Thread(target=mining_process, daemon=True).start()
    Thread(target=peer_sync, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))