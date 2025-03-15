no need to add blockchain_data folder 

Setup Instructions
On Bootstrap Node (First Computer)
bash
Copy

# 1. Create project directory
mkdir blockchain && cd blockchain

# 2. Create files
mkdir -p ui/{templates,static} blockchain_data
touch node.py requirements.txt ui/templates/index.html

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start node (replace IP with your actual LAN IP)
export PORT=5000
export BOOTSTRAP_NODE="http://$(hostname -I | awk '{print $1}'):5000"
python3 node.py

On Other Computers
bash
Copy

# 1. Copy the blockchain folder to other computers using SCP, USB, or Git

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start node with bootstrap reference
export PORT=5001  # Different port for each node
export BOOTSTRAP_NODE="http://<bootstrap-node-ip>:5000"
python3 node.py









Testing in Your Lab

    Start Bootstrap Node:
    bash
    Copy

    IS_BOOTSTRAP=true python3 node.py --port 5000

    Start Other Nodes:
    bash
    Copy

    # On PC 2
    python3 node.py --port 5001

    # On PC 3
    python3 node.py --port 5002

    Verify Participation:

        Send transactions from any node’s UI.

        Watch blocks being mined across nodes in real-time.

        Check /peers endpoint for connected nodes.


Step-by-Step Execution
On All Lab PCs:

    Clone Project:
    bash
    Copy

    mkdir blockchain-network && cd blockchain-network
    # Copy all files into this directory

    Install Dependencies:
    bash
    Copy

    pip install -r requirements.txt

On Bootstrap Node (First PC):

    Start Node:
    bash
    Copy

    export PORT=5000
    export BOOTSTRAP_NODE="http://$(hostname -I | awk '{print $1}'):5000"
    python node.py

On Other Nodes:

    Start Node (replace IP with bootstrap node's IP):
    bash
    Copy

    export PORT=5001  # Unique port for each node
    export BOOTSTRAP_NODE="http://10.240.119.24:5000"  # Bootstrap node IP
    python node.py