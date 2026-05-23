import joblib
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
import math
import time
import datetime
from web3 import Web3
import json # To load ABI and save workorder JSON
import os # <-- Import os for creating directory/paths
from pathlib import Path # <-- Import Path for easier path handling

# --- CONFIGURATION ---

# 1. Load ML Pipeline
try:
    # --- [Ensure this path is correct] ---
    PIPELINE_PATH = r'C:\tmc4.0\models\tarmacskin_model_thresholded_critical_emph.joblib'
    pipeline = joblib.load(PIPELINE_PATH)
    model = pipeline['model']
    scaler = pipeline['scaler']
    label_encoder = pipeline['label_encoder']
    print(f"Successfully loaded model pipeline from {PIPELINE_PATH}")
    # ... (rest of loading prints)
except Exception as e:
    print(f"ERROR loading ML pipeline: {e}")
    exit()

# 2. Map model outputs
STATUS_MAP = {'Healthy': 'Healthy', 'Warning': 'Warning', 'Critical': 'Critical'}
STATUS_MAP_LOWER = {k.lower(): v for k, v in STATUS_MAP.items()}

# --- [EDIT BLOCKCHAIN DETAILS] ---
GANACHE_URL = "http://127.0.0.1:7545"
CONTRACT_ADDRESS = "0x40e9E693306771b8e62EEFdDF923a8221E3B4EB9" # <-- PASTE ADDRESS HERE
ABI_FILE_PATH = Path("contract_abi.json")
DEPLOYER_PRIVATE_KEY = "0xe5a3c70ee970b07165167bc0dbbd850fae2c29ae3c1baf0f1786e2c2bc3f721b" # <-- PASTE KEY HERE
# --- [END EDITS] ---

# --- [NEW CONFIGURATION for Workorder Files] ---
WORKORDERS_DIR = Path("workorders") # Directory to save JSON files
WORKORDERS_DIR.mkdir(exist_ok=True) # Create the directory if it doesn't exist
# ---

# Load ABI
try:
    with open(ABI_FILE_PATH, 'r') as f:
        CONTRACT_ABI = json.load(f)
except Exception as e:
    print(f"ERROR loading ABI from {ABI_FILE_PATH}: {e}")
    CONTRACT_ABI = []

# --- INITIALIZE FLASK APP & WEB3 ---
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:8080"}})

web3 = Web3(Web3.HTTPProvider(GANACHE_URL))
account = None
contract = None

if not web3.is_connected():
    print(f"ERROR: Failed to connect to Ganache at {GANACHE_URL}")
else:
    # ... (Web3 connection, account, and contract loading logic - unchanged) ...
    print(f"Connected to Ethereum node: {GANACHE_URL}")
    try:
        account = web3.eth.account.from_key(DEPLOYER_PRIVATE_KEY)
        web3.eth.default_account = account.address
        print(f"Using account address: {account.address}")
    except ValueError as e:
         print(f"ERROR: Invalid DEPLOYER_PRIVATE_KEY: {e}")

    if CONTRACT_ABI and CONTRACT_ADDRESS != "YOUR_DEPLOYED_CONTRACT_ADDRESS_HERE":
         try:
             contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)
             print(f"Smart contract loaded at address: {CONTRACT_ADDRESS}")
         except Exception as e:
             print(f"ERROR loading smart contract: {e}")
    else:
        # Print specific reason if contract wasn't loaded
        if not CONTRACT_ABI: print("Contract not loaded: Missing/invalid ABI.")
        if CONTRACT_ADDRESS == "YOUR_DEPLOYED_CONTRACT_ADDRESS_HERE": print("Contract not loaded: CONTRACT_ADDRESS not set.")


# --- HELPER FUNCTIONS ---
def calculate_health_score_from_impact(impact_force):
    # ... (function unchanged) ...
    SAFE_IMPACT = 0.0
    CRITICAL_IMPACT = 2000.0 # Using the higher threshold
    if impact_force <= SAFE_IMPACT: return 100
    if impact_force >= CRITICAL_IMPACT: return 0
    damage_percentage = impact_force / CRITICAL_IMPACT
    score = 100.0 * (1.0 - damage_percentage)
    return int(score)

# --- API ENDPOINTS ---

@app.route('/api/road/demo/process-manual', methods=['POST'])
def process_manual_data():
    # ... (This endpoint is unchanged - uses 4 features [ax,ay,az,mag]) ...
    try:
        data = request.json
        ax = float(data.get('accel_x_g', 0))
        ay = float(data.get('accel_y_g', 0))
        az = float(data.get('accel_z_g', 0))
        rms = float(data.get('accel_rms_g', 0))
        load = float(data.get('loadcell_force_kg', 0))

        load = max(0.0, min(load, 1500.0)) # Clip load

        peak_g = max(abs(ax), abs(ay), abs(az))
        impact_force_N = load * peak_g * 9.81
        health_score = calculate_health_score_from_impact(impact_force_N)
        accel_magnitude = math.sqrt(ax**2 + ay**2 + az**2)

        features_for_model = [ax, ay, az, accel_magnitude] # 4 features
        features_input = np.array([features_for_model])
        scaled_features_input = scaler.transform(features_input)
        numeric_prediction = model.predict(scaled_features_input)[0]
        string_prediction = label_encoder.inverse_transform([numeric_prediction])[0]
        status_label = STATUS_MAP_LOWER.get(string_prediction.lower(), 'Warning')

        confidence = 0.95
        if hasattr(model, 'predict_proba'):
            probabilities = model.predict_proba(scaled_features_input)[0]
            confidence = probabilities.max()

        # Debug prints (optional)
        # ...

        new_metrics = {
            'estimated_impact_force_N': float(impact_force_N),
            'structural_health_score': int(health_score),
            'overload_alert': load > 150,
            'accel_peak_g': None,
            'accel_rms_g': float(rms),
            'loadcell_force_kg': float(load),
            'accel_x_g': float(ax),
            'accel_y_g': float(ay),
            'accel_z_g': float(az),
        }
        new_ai_verdict = { 'label': str(status_label), 'confidence': float(confidence) }

        return jsonify({'metrics': new_metrics, 'ai_verdict': new_ai_verdict})

    except Exception as e:
        print(f"Error processing manual data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Internal server error: {e}"}), 500


# --- [UPDATED WORKORDER ENDPOINT with JSON file saving] ---
@app.route('/api/workorder/create', methods=['POST'])
def create_workorder():
    """
    Generates workorder details, saves to JSON file, calls the smart contract,
    and returns details including the transaction hash.
    """
    global contract, account, web3 # Use the globally loaded objects

    # Check Web3 setup first
    if not web3 or not web3.is_connected():
        return jsonify({"error": "Backend not connected to Ethereum node"}), 503
    if account is None:
         return jsonify({"error": "Backend account not configured correctly"}), 500
    if contract is None:
         return jsonify({"error": "Smart contract not loaded correctly"}), 500

    try:
        # 1. Get data from frontend
        data = request.json
        road_id = data.get('roadId')
        road_name = data.get('roadName')
        road_location = data.get('roadLocation')
        current_status = data.get('currentStatus')

        if not all([road_id, road_name, road_location, current_status]):
            return jsonify({"error": "Missing required workorder data"}), 400

        # 2. Generate Workorder ID and Timestamp
        timestamp_dt = datetime.datetime.utcnow()
        timestamp_iso = timestamp_dt.isoformat() + 'Z'
        workorder_id = f"WO-{road_id[:4]}-{int(timestamp_dt.timestamp() * 1000) % 100000}"

        # 3. Prepare Workorder Data Object
        workorder_data = {
            'workorderId': workorder_id,
            'roadId': road_id,
            'roadName': road_name,
            'roadLocation': road_location, # Keep for file, even if not sent to contract
            'timestamp': timestamp_iso,
            'status': 'pending_blockchain', # Initial status before contract call
            'currentRoadStatus': current_status, # The status triggering the workorder
            'blockchainTransactionHash': None # Placeholder
        }

        # 4. Save Workorder Data to JSON File
        file_path = WORKORDERS_DIR / f"{workorder_id}.json"
        try:
            with open(file_path, 'w') as f:
                json.dump(workorder_data, f, indent=4)
            print(f"Workorder data saved locally to: {file_path}")
        except Exception as file_error:
            print(f"WARNING: Failed to save workorder JSON to {file_path}: {file_error}")
            # Decide if you want to proceed without saving or return an error
            # For now, we'll proceed but log the warning.

        # 5. Interact with Smart Contract
        print("-" * 50)
        print(f"Attempting to create Workorder on Blockchain:")
        print(f"  Workorder ID: {workorder_id}")
        # ... (other prints)

        # --- [Verify Function Name & Arguments match Workorder.sol] ---
        contract_function_call = contract.functions.createWorkorder(
            workorder_id,
            road_id,
            timestamp_iso,
            "active", # Send 'active' status to the contract
            road_name
        )
        # --- [End Verification] ---

        # Estimate, Build, Sign, Send Transaction (Same as before)
        try:
             estimated_gas = contract_function_call.estimate_gas({'from': account.address})
             print(f"  Estimated Gas: {estimated_gas}")
        except Exception as gas_error:
             print(f"  WARNING: Gas estimation failed: {gas_error}. Using default (300k).")
             estimated_gas = 300000

        nonce = web3.eth.get_transaction_count(account.address)
        tx = contract_function_call.build_transaction({
            'chainId': web3.eth.chain_id,
            'gas': estimated_gas + 50000,
            'gasPrice': web3.eth.gas_price,
            'nonce': nonce,
            'from': account.address
        })

        signed_tx = web3.eth.account.sign_transaction(tx, private_key=DEPLOYER_PRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"  Transaction Sent. Hash: {tx_hash.hex()}")

        # Wait for Receipt
        print("  Waiting for transaction receipt...")
        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)

        on_chain_hash = None # Initialize hash variable
        final_status = 'failed_blockchain' # Assume failure initially

        if tx_receipt.status == 1:
            print(f"  Transaction Successful! Block: {tx_receipt.blockNumber}")
            on_chain_hash = tx_hash.hex()
            final_status = 'active' # Update status on success
            # --- Optionally: Update the JSON file with the hash ---
            try:
                workorder_data['blockchainTransactionHash'] = on_chain_hash
                workorder_data['status'] = final_status
                with open(file_path, 'w') as f:
                    json.dump(workorder_data, f, indent=4)
                print(f"  Updated JSON file with transaction hash.")
            except Exception as update_error:
                print(f"  WARNING: Failed to update JSON file with hash: {update_error}")
            # --- End optional update ---
        else:
            print(f"  Transaction Failed! Status: {tx_receipt.status}")
            # Save failure status to JSON (optional)
            try:
                workorder_data['status'] = final_status
                with open(file_path, 'w') as f:
                    json.dump(workorder_data, f, indent=4)
                print(f"  Updated JSON file with failed status.")
            except Exception as update_error:
                 print(f"  WARNING: Failed to update JSON file with failed status: {update_error}")
            # ---
            raise Exception(f"Blockchain transaction failed (Status code: {tx_receipt.status}).")


        print("-" * 50)

        # 6. Return the details including the REAL hash
        return jsonify({
            'workorderId': workorder_id,
            'timestamp': timestamp_iso,
            'onChainHash': on_chain_hash, # Will be None if transaction failed
            'status': final_status # Return the final status ('active' or 'failed_blockchain')
        })

    except Exception as e:
        print(f"Error creating workorder: {e}")
        # ... (Error handling logic - unchanged) ...
        import traceback
        traceback.print_exc()
        error_message = f"Internal server error: {e}"
        # Refine error messages
        err_str = str(e).lower()
        if "insufficient funds" in err_str: error_message = "Blockchain transaction failed: Insufficient funds for gas."
        elif "reverted" in err_str: error_message = "Blockchain transaction failed: Smart contract reverted."
        elif "nonce too low" in err_str or "replacement transaction underpriced" in err_str: error_message = "Blockchain transaction failed: Nonce error. Restart backend."
        # ... other specific blockchain errors ...

        return jsonify({"error": error_message}), 500
# --- [END OF UPDATED ENDPOINT] ---


# --- RUN THE APP ---
if __name__ == '__main__':
    app.run(debug=True, port=5000)
