**TarmacSkin: Real-Time AI & Blockchain-Backed Road Structural Health Monitoring**

TarmacSkin is an end-to-end cyber-physical infrastructure monitoring system. It continuously ingests high-frequency, multi-axis accelerometer and load data streams from on-site sensor systems (using an ESP32 or serial simulator), uses a hybrid machine learning and deterministic override pipeline (XGBoost + Safety Rules) to predict structural state severity, and generates immutable, decentralized maintenance logs (workorders) on a private Ethereum blockchain.

**Key Features**

**Direct Hardware Integration:** Runs a non-blocking background thread to ingest data from an ESP32 microcontroller via a Serial COM interface.

**Hybrid AI/ML Prediction:** Predicts structural states (Healthy, Stressed, Critical) using an optimized XGBoost classifier under Z-score normalization.

**Fail-Safe Override:** Implements a deterministic safety rule ($accel\_mag > 0.6g$) that overrides machine learning predictions to prevent false negatives on extreme events.

**Class-Imbalance Compensation:** Prioritizes critical anomalies during training using balanced sample weights bolstered by a $3\times$ multiplicative factor for the Critical class.

**Decentralized Audit Trails:** Direct integration with a local private Ethereum ledger (Ganache) via Solidity smart contracts, storing tamper-proof maintenance workorders.

**Dynamic Digital Twin Dashboard:** A highly interactive React + TypeScript interface for real-time visualization and toggleable manual test-bed evaluation.

**Prerequisites**

Ensure you have the following installed on your machine:

Node.js (v18.0.0 or higher)

Python (v3.10.0 or higher)

Ganache (UI or CLI for local blockchain simulation)

Solidity Compiler (solc) (v0.8.0 or higher, or configured via deploy tools)

**Installation & Setup**

**1. Blockchain Network Setup**

Launch Ganache and start a new workspace.

Ensure it runs on http://127.0.0.1:7545 with network ID 5777.

Locate and deploy your Workorder.sol contract using Remix or your Python deployment script.

Copy the Deployed Contract Address and the Deployer Account Private Key.

**2. Backend Setup**

Navigate to the backend directory:

cd tarmac-backend


Create and activate a virtual environment:

python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate


Install required packages:

pip install -r requirements.txt


If you need to recompile and train the machine learning pipeline from your custom CSV dataset:

python train_model.py


Configure environmental parameters in app.py:

Open app.py and input your exact Ganache contract settings:

CONTRACT_ADDRESS = "0x641A92A8...."
DEPLOYER_PRIVATE_KEY = "0x73e88b883..."
SERIAL_PORT = "COM6" # Update to match your ESP32 interface


**3. Frontend Setup**

From the root directory, install npm packages:

npm install


Execution Guide

To run TarmacSkin 2.0 locally, you must run both the Flask backend server and the React frontend development server concurrently.

Run the Flask Backend

Make sure your virtual environment is active in the backend directory, then run:

python app.py


The backend will attempt to establish connection to your ESP32 over COM6 in a background thread, while simultaneously exposing REST APIs on http://localhost:5000.

Run the React Frontend

Open a new terminal window in the root directory and run:

npm run dev


The dashboard will spin up. Access the web interface at http://localhost:8080 (or the port specified by Vite).

**Blockchain Operations Deep-Dive**

TarmacSkin handles critical maintenance logging securely through Decentralized Ledger Technology (DLT). Here is the technical breakdown of how workorders are submitted to the ledger:

**1. Trigger Mechanics**

When a structural reading classifies a road status as Critical (either through the ML estimator or via the deterministic $accel\_mag > 0.6g$ override rule), the frontend triggers a "Generate Workorder" utility.

**2. Smart Contract Function (Workorder.sol)**

The deployed contract contains a struct and a mapping designed to capture and anchor operational records permanently:

// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract WorkorderContract {
    struct Workorder {
        string workorderId;
        string roadId;
        string timestamp;
        string status;
        string roadName;
    }

    mapping(string => Workorder) public workorders;

    event WorkorderCreated(
        string indexed workorderId,
        string roadId,
        string status
    );

    function createWorkorder(
        string memory _workorderId,
        string memory _roadId,
        string memory _timestamp,
        string memory _status,
        string memory _roadName
    ) public {
        workorders[_workorderId] = Workorder(
            _workorderId,
            _roadId,
            _timestamp,
            _status,
            _roadName
        );
        emit WorkorderCreated(_workorderId, _roadId, _status);
    }
}


**3. Backend Execution Steps (app.py)**

When /api/workorder/create is requested, the server performs a multi-step transaction:

JSON Local Archival: First, it writes a local backup file inside workorders/ with the initial status pending_blockchain. This provides write-ahead logging to prevent loss of critical telemetry.

Transaction Building: Web3.py accesses the contract's ABI, constructs the input arguments, and estimates the transaction's gas requirements:

tx = contract.functions.createWorkorder(
    workorder_id, road_id, timestamp_iso, "active", road_name
).build_transaction({
    'chainId': web3.eth.chain_id,
    'gas': estimated_gas + 50000,
    'gasPrice': web3.eth.gas_price,
    'nonce': web3.eth.get_transaction_count(account.address),
    'from': account.address
})


Cryptographic Signing: The transaction payload is cryptographically signed locally on the backend using the DEPLOYER_PRIVATE_KEY ensuring high-security standard practices.

Broadcast & Consensus: The signed transaction is sent to the Ganache ledger using send_raw_transaction(). The backend halts and waits for the receipt confirmation.

UI Updates: Upon block confirmation, the local JSON log updates with the absolute tx hash, and the frontend displays the transaction hash as immutable proof of workorder creation.
