import joblib
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
import math
import time
import datetime
from web3 import Web3
import json # To load ABI and save workorder JSON
import os
from pathlib import Path

# --- CONFIGURATION ---

# 1. Load ML Pipeline using the exact path
try:
    # --- [Using the specific model path you provided] ---
    MODEL_BUNDLE_PATH = r'C:\tmc4.0\models\tarmacskin_model_thresholded_critical_emph.joblib'
    pipeline = joblib.load(MODEL_BUNDLE_PATH)

    # Check for expected keys
    if not isinstance(pipeline, dict) or not all(k in pipeline for k in ("model", "scaler", "label_encoder")):
         raise KeyError("Model bundle must contain keys: 'model', 'scaler', 'label_encoder'")

    # Extract components
    model = pipeline['model']
    scaler = pipeline['scaler']
    label_encoder = pipeline['label_encoder']
    critical_threshold = pipeline.get('critical_threshold') # Get threshold if it exists

    print(f"Successfully loaded model pipeline from {MODEL_BUNDLE_PATH}")
    print(f"-> Model: {model.__class__.__name__}")
    print(f"-> Scaler: {scaler.__class__.__name__}")
    print(f"-> LabelEncoder classes: {list(label_encoder.classes_)}")
    if hasattr(scaler, 'n_features_in_'):
        print(f"-> Scaler expects {scaler.n_features_in_} features.")
    if critical_threshold is not None:
        print(f"-> Critical Threshold Rule Loaded: {critical_threshold}")
    else:
        print("-> No Critical Threshold Rule found in bundle.")


except FileNotFoundError:
    print("*" * 50)
    print(f"ERROR: Model file not found at: {MODEL_BUNDLE_PATH}")
    print("*" * 50)
    exit()
except KeyError as e:
    print("*" * 50)
    print(f"ERROR: Your model pipeline is missing a key: {e}")
    print("Expected keys: 'model', 'scaler', 'label_encoder'")
    print("*" * 50)
    exit()
except Exception as e:
    print(f"ERROR loading ML pipeline: {e}")
    exit()

# 2. Map model outputs (using Capitalized keys to match encoder output)
#    Maps the string from label_encoder.inverse_transform to frontend display label
STATUS_MAP = {
    'Healthy': 'Healthy',
    'Warning': 'Warning',
    'Critical': 'Critical'
    # Add 'Critical': 'Critical' if your encoder uses that instead of 'Damaged'
}
if 'Critical' in label_encoder.classes_ and 'Critical' not in STATUS_MAP:
     STATUS_MAP['Critical'] = 'Critical'


# --- [EDIT BLOCKCHAIN DETAILS] ---
GANACHE_URL = "http://127.0.0.1:7545"
CONTRACT_ADDRESS = "0x641A92A8b56EDD6d18b8a7d43f36070F2dD0A14B" # <-- PASTE ADDRESS HERE
ABI_FILE_PATH = Path("contract_abi.json")
DEPLOYER_PRIVATE_KEY = "0x73e88b88384b8b5e91ecd6f2cc302251732fcea937324186bbb5e876e25223fd" # <-- PASTE KEY HERE
WORKORDERS_DIR = Path("workorders")
WORKORDERS_DIR.mkdir(exist_ok=True)
# --- [END EDITS] ---

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

# ... (Web3 connection, account, and contract loading logic - unchanged) ...
if not web3.is_connected():
    print(f"ERROR: Failed to connect to Ganache at {GANACHE_URL}")
else:
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
    # ... (rest of contract loading checks) ...


# --- HELPER FUNCTIONS ---
def calculate_health_score_from_impact(impact_force):
    # ... (function unchanged, uses 2000N threshold) ...
    SAFE_IMPACT = 0.0
    CRITICAL_IMPACT = 2000.0
    if impact_force <= SAFE_IMPACT: return 100
    if impact_force >= CRITICAL_IMPACT: return 0
    damage_percentage = impact_force / CRITICAL_IMPACT
    score = 100.0 * (1.0 - damage_percentage)
    return int(score)

# --- API ENDPOINTS ---

@app.route('/api/road/demo/process-manual', methods=['POST'])
def process_manual_data():
    """
    Processes manual inputs using the 4-feature model [ax, ay, az, magnitude]
    AND applies the critical threshold rule if present.
    """
    global model, scaler, label_encoder, critical_threshold, STATUS_MAP # Use global artifacts

    try:
        # 1. Get inputs
        data = request.json
        ax = float(data.get('accel_x_g', 0))
        ay = float(data.get('accel_y_g', 0))
        az = float(data.get('accel_z_g', 0))
        rms = float(data.get('accel_rms_g', 0))
        load = float(data.get('loadcell_force_kg', 0))

        # Clip load (from predict_tarmacskin.py logic)
        load = max(0.0, min(load, 1500.0))

        # 2. Calculations
        peak_g = max(abs(ax), abs(ay), abs(az))
        impact_force_N = load * peak_g * 9.81
        health_score = calculate_health_score_from_impact(impact_force_N)
        accel_magnitude = math.sqrt(ax**2 + ay**2 + az**2)

        # 3. Prediction (Using 4 features)
        features_for_model = [ax, ay, az, accel_magnitude] # 4 features
        features_input = np.array([features_for_model])
        scaled_features_input = scaler.transform(features_input)
        numeric_prediction = model.predict(scaled_features_input)[0]

        # Get raw prediction label from encoder
        raw_string_prediction = label_encoder.inverse_transform([numeric_prediction])[0]

        # --- [APPLY HARD RULE CORRECTION] ---
        corrected_string_prediction = raw_string_prediction
        forced_by_rule = False
        if critical_threshold is not None:
            threshold = float(critical_threshold)
            # Find the critical class name ('Critical' or 'Damaged')
            critical_class_name = None
            if 'Critical' in label_encoder.classes_:
                critical_class_name = 'Critical'
            elif 'Damaged' in label_encoder.classes_:
                critical_class_name = 'Damaged'
            else: # Fallback to the last class if names don't match
                 critical_class_name = label_encoder.classes_[-1]
                 print(f"Warning: Neither 'Critical' nor 'Damaged' found in label encoder classes. Using '{critical_class_name}' as critical class for threshold rule.")


            if accel_magnitude > threshold and critical_class_name:
                corrected_string_prediction = critical_class_name
                forced_by_rule = True
        # --- [END HARD RULE] ---

        # Map the *corrected* prediction string to the frontend label
        # Use .get() with a default to handle potential mismatches
        status_label = STATUS_MAP.get(corrected_string_prediction, 'Warning')

        # Get confidence score (based on the RAW model probabilities)
        confidence = 0.95
        probabilities_dict = {}
        if hasattr(model, 'predict_proba'):
            probabilities = model.predict_proba(scaled_features_input)[0]
            confidence = probabilities.max()
            # Create dict for debugging prints
            probabilities_dict = dict(zip(label_encoder.classes_, probabilities.tolist()))


        # Debug prints
        print("-" * 50)
        print(f"MANUAL INPUT PROCESSING:")
        print(f"  Inputs (Model): {features_for_model}")
        print(f"  Inputs (Other): RMS={rms:.4f}, Load={load:.2f}")
        print(f"  Scaled: {scaled_features_input}")
        print(f"  Raw Prediction: {raw_string_prediction} ({numeric_prediction})")
        if probabilities_dict:
             print(f"  Probabilities: { {k: f'{v:.4f}' for k, v in probabilities_dict.items()} }")
        if forced_by_rule:
             print(f"  HARD RULE APPLIED: accel_mag ({accel_magnitude:.4f}) > threshold ({critical_threshold})")
             print(f"  Corrected Prediction: {corrected_string_prediction}")
        print(f"  Final Status (to frontend): {status_label} (Confidence: {confidence:.2f})")
        print(f"  Calculations: Impact={impact_force_N:.2f}N, Health Score={health_score}%")
        print("-" * 50)

        # 4. Assemble response
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
        # Send the *final*, potentially rule-corrected status label
        new_ai_verdict = { 'label': str(status_label), 'confidence': float(confidence) }

        return jsonify({'metrics': new_metrics, 'ai_verdict': new_ai_verdict})

    except Exception as e:
        print(f"Error processing manual data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Internal server error: {e}"}), 500


# --- WORKORDER ENDPOINT (Using Web3) ---
@app.route('/api/workorder/create', methods=['POST'])
def create_workorder():
    # ... (This endpoint remains unchanged from the previous version) ...
    global contract, account, web3

    if not web3 or not web3.is_connected(): return jsonify({"error": "Backend not connected to Ethereum node"}), 503
    if account is None: return jsonify({"error": "Backend account not configured correctly"}), 500
    if contract is None: return jsonify({"error": "Smart contract not loaded correctly"}), 500

    try:
        data = request.json
        road_id = data.get('roadId')
        road_name = data.get('roadName')
        road_location = data.get('roadLocation')
        current_status = data.get('currentStatus') # Status from frontend badge

        if not all([road_id, road_name, road_location, current_status]):
            return jsonify({"error": "Missing required workorder data"}), 400

        timestamp_dt = datetime.datetime.utcnow()
        timestamp_iso = timestamp_dt.isoformat() + 'Z'
        workorder_id = f"WO-{road_id[:4]}-{int(timestamp_dt.timestamp() * 1000) % 100000}"

        # --- Prepare data for JSON file ---
        workorder_data = {
            'workorderId': workorder_id, 'roadId': road_id, 'roadName': road_name,
            'roadLocation': road_location, 'timestamp': timestamp_iso,
            'status': 'pending_blockchain', 'currentRoadStatus': current_status,
            'blockchainTransactionHash': None
        }
        file_path = WORKORDERS_DIR / f"{workorder_id}.json"
        try:
            with open(file_path, 'w') as f: json.dump(workorder_data, f, indent=4)
            print(f"Workorder data saved locally to: {file_path}")
        except Exception as file_error:
            print(f"WARNING: Failed to save workorder JSON: {file_error}")
        # --- End file save ---


        print("-" * 50)
        print(f"Attempting Blockchain Transaction for Workorder: {workorder_id}")
        # ... (rest of prints)

        contract_function_call = contract.functions.createWorkorder(
            workorder_id, road_id, timestamp_iso,
            "active", # Send 'active' to contract
            road_name
        )

        # Estimate, Build, Sign, Send, Wait for Receipt (unchanged)
        estimated_gas = 300000 # Default
        try:
             estimated_gas = contract_function_call.estimate_gas({'from': account.address})
             print(f"  Estimated Gas: {estimated_gas}")
        except Exception as gas_error:
             print(f"  WARNING: Gas estimation failed: {gas_error}.")

        nonce = web3.eth.get_transaction_count(account.address)
        tx = contract_function_call.build_transaction({
            'chainId': web3.eth.chain_id, 'gas': estimated_gas + 50000,
            'gasPrice': web3.eth.gas_price, 'nonce': nonce, 'from': account.address
        })
        signed_tx = web3.eth.account.sign_transaction(tx, private_key=DEPLOYER_PRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"  Transaction Sent. Hash: {tx_hash.hex()}")
        print("  Waiting for receipt...")
        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)

        on_chain_hash = None
        final_status = 'failed_blockchain'

        if tx_receipt.status == 1:
            print(f"  Transaction Successful! Block: {tx_receipt.blockNumber}")
            on_chain_hash = tx_hash.hex()
            final_status = 'active'
            # Update JSON file
            try:
                workorder_data['blockchainTransactionHash'] = on_chain_hash
                workorder_data['status'] = final_status
                with open(file_path, 'w') as f: json.dump(workorder_data, f, indent=4)
                print(f"  Updated JSON with tx hash.")
            except Exception as update_error:
                print(f"  WARNING: Failed to update JSON with hash: {update_error}")
        else:
            print(f"  Transaction Failed! Status: {tx_receipt.status}")
            # Update JSON file
            try:
                workorder_data['status'] = final_status
                with open(file_path, 'w') as f: json.dump(workorder_data, f, indent=4)
                print(f"  Updated JSON with failed status.")
            except Exception as update_error:
                 print(f"  WARNING: Failed to update JSON failed status: {update_error}")
            raise Exception(f"Blockchain tx failed (Status: {tx_receipt.status})")

        print("-" * 50)

        # Return details
        return jsonify({
            'workorderId': workorder_id, 'timestamp': timestamp_iso,
            'onChainHash': on_chain_hash, 'status': final_status
        })

    except Exception as e:
        # ... (Error handling unchanged) ...
        print(f"Error creating workorder: {e}")
        import traceback
        traceback.print_exc()
        error_message = f"Internal server error: {e}"
        err_str = str(e).lower()
        if "insufficient funds" in err_str: error_message = "Blockchain transaction failed: Insufficient funds for gas."
        elif "reverted" in err_str: error_message = "Blockchain transaction failed: Smart contract reverted."
        elif "nonce too low" in err_str or "replacement transaction underpriced" in err_str: error_message = "Blockchain transaction failed: Nonce error. Restart backend."
        # ... other specific blockchain errors ...
        return jsonify({"error": error_message}), 500

# --- RUN THE APP ---
if __name__ == '__main__':
    app.run(debug=True, port=5000)

