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

# Get LAN IP automatically
def get_lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

NODE_ID = str(uuid4())
NODE_ADDRESS = f"http://{get_lan_ip()}:{os.environ.get('PORT', 5000)}"

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
        if os.path.exists(app.config['CHAIN_FILE']):
            with open(app.config['CHAIN_FILE'], 'r') as f:
                self.chain = json.load(f)
        if os.path.exists(app.config['MINERS_FILE']):
            with open(app.config['MINERS_FILE'], 'r') as f:
                self.miners = json.load(f)

    def save_data(self):
        with open(app.config['CHAIN_FILE'], 'w') as f:
            json.dump(self.chain, f)
        with open(app.config['MINERS_FILE'], 'w') as f:
            json.dump(self.miners, f)

    def create_genesis_block(self):
        genesis = {
            'index': 0,
            'miner': 'genesis',
            'transactions': [],
            'timestamp': time.time(),
            'previous_hash': '0',
            'nonce': 0,
            'hash': '0000genesis'
        }
        self.chain.append(genesis)
        self.save_data()

    def proof_of_work(self, index, previous_hash, transactions, nonce):
        block_string = f"{index}{previous_hash}{transactions}{nonce}".encode()
        return hashlib.sha256(block_string).hexdigest()

    def mine_block(self):
        while True:
            if self.transactions:
                last_block = self.chain[-1]
                new_nonce = 0
                
                while True:
                    new_hash = self.proof_of_work(
                        len(self.chain),
                        last_block['hash'],
                        self.transactions,
                        new_nonce
                    )
                    
                    if new_hash.startswith("0000"):
                        new_block = {
                            'index': len(self.chain),
                            'miner': NODE_ID,
                            'transactions': self.transactions.copy(),
                            'timestamp': time.time(),
                            'previous_hash': last_block['hash'],
                            'nonce': new_nonce,
                            'hash': new_hash
                        }
                        
                        with self.lock:
                            self.chain.append(new_block)
                            self.transactions.clear()
                            self.save_data()
                            self.broadcast_block(new_block)
                            
                        print(f"\nMined block {new_block['index']}")
                        break
                        
                    new_nonce += 1
            else:
                time.sleep(5)

    def add_transaction(self, sender, receiver, amount):
        with self.lock:
            self.transactions.append({
                'sender': sender,
                'receiver': receiver,
                'amount': amount,
                'timestamp': time.time()
            })
        self.broadcast_transaction(sender, receiver, amount)

    def broadcast_transaction(self, sender, receiver, amount):
        for miner in list(self.miners.keys()):
            try:
                requests.post(
                    f"{miner}/receive_transaction",
                    json={'sender': sender, 'receiver': receiver, 'amount': amount},
                    timeout=2
                )
            except:
                self.remove_miner(miner)

    def broadcast_block(self, block):
        for miner in list(self.miners.keys()):
            try:
                requests.post(f"{miner}/receive_block", json=block, timeout=2)
            except:
                self.remove_miner(miner)

    def register_miner(self, address):
        if address != NODE_ADDRESS:
            self.miners[address] = time.time()
            self.save_data()

    def remove_miner(self, address):
        if address in self.miners:
            del self.miners[address]
            self.save_data()

blockchain = Blockchain()

# Flask Endpoints
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    data = request.json
    blockchain.add_transaction(data['sender'], data['receiver'], data['amount'])
    return jsonify({"message": "Transaction added"}), 201

@app.route('/chain', methods=['GET'])
def full_chain():
    return jsonify(blockchain.chain), 200

@app.route('/miners', methods=['GET'])
def list_miners():
    active_miners = []
    for miner, last_seen in blockchain.miners.items():
        if time.time() - last_seen < 30:
            active_miners.append(miner)
    return jsonify({"active_miners": active_miners}), 200

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    blockchain.register_miner(data['address'])
    
    # Return existing peers
    return jsonify({"peers": list(blockchain.miners.keys())}), 201

@app.route('/receive_block', methods=['POST'])
def receive_block():
    block = request.json
    last_block = blockchain.chain[-1]

    if block['previous_hash'] != last_block['hash']:
        return jsonify({"error": "Invalid chain"}), 400

    if not block['hash'].startswith("0000"):
        return jsonify({"error": "Invalid PoW"}), 400

    with blockchain.lock:
        if block['index'] == len(blockchain.chain):
            blockchain.chain.append(block)
            blockchain.save_data()
    return jsonify({"message": "Block added"}), 200

@app.route('/receive_transaction', methods=['POST'])
def receive_transaction():
    data = request.json
    with blockchain.lock:
        blockchain.transactions.append({
            'sender': data['sender'],
            'receiver': data['receiver'],
            'amount': data['amount'],
            'timestamp': time.time()
        })
    return jsonify({"message": "Transaction received"}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "active", "node_id": NODE_ID}), 200

if __name__ == '__main__':
    # Auto-register with bootstrap node
    if os.environ.get('BOOTSTRAP_NODE'):
        try:
            requests.post(
                os.environ['BOOTSTRAP_NODE'] + "/register",
                json={"address": NODE_ADDRESS},
                timeout=5
            )
            print(f"Registered with bootstrap node: {os.environ['BOOTSTRAP_NODE']}")
        except Exception as e:
            print(f"Bootstrap registration failed: {str(e)}")

    # Start mining thread
    Thread(target=blockchain.mine_block, daemon=True).start()

    # Health check thread
    def health_check():
        while True:
            for miner in list(blockchain.miners.keys()):
                try:
                    requests.get(f"{miner}/health", timeout=2)
                    blockchain.miners[miner] = time.time()
                except:
                    blockchain.remove_miner(miner)
            time.sleep(15)
    Thread(target=health_check, daemon=True).start()

    # Start Flask
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)