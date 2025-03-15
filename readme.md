no need to add blockchain_data folder 
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