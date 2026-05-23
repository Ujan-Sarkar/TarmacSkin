import joblib
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
import math
import time
import datetime
from web3 import Web3
import json
import os
from pathlib import Path
import threading # For thread safety of latest_data AND serial reading
import re # For error parsing
import serial # <-- Import PySerial
import sys # <-- Import sys for exit on serial error

# --- CONFIGURATION ---

# 1. Load ML Pipeline
try:
    MODEL_BUNDLE_PATH = r'C:\tmc5.0\models\tarmacskin_model_thresholded_critical_emph.joblib' # Using path from your code
    pipeline = joblib.load(MODEL_BUNDLE_PATH)
    model = pipeline['model']
    scaler = pipeline['scaler']
    label_encoder = pipeline['label_encoder']
    critical_threshold = pipeline.get('critical_threshold')
    le_classes = list(label_encoder.classes_) # Store classes for mapping
    print(f"Successfully loaded model pipeline from {MODEL_BUNDLE_PATH}")
    print(f"-> Model: {model.__class__.__name__}")
    print(f"-> Scaler: {scaler.__class__.__name__}")
    print(f"-> LabelEncoder classes: {le_classes}")
    if hasattr(scaler, 'n_features_in_'):
        print(f"-> Scaler expects {scaler.n_features_in_} features.")
    if critical_threshold is not None:
        print(f"-> Critical Threshold Rule Loaded: {critical_threshold}")
    else:
        print("-> No Critical Threshold Rule found in bundle.")
except FileNotFoundError:
    print("*" * 50); print(f"ERROR: Model file not found at: {MODEL_BUNDLE_PATH}"); print("*" * 50); exit()
except KeyError as e:
    print("*" * 50); print(f"ERROR: Model pipeline missing key: {e}"); print("*" * 50); exit()
except Exception as e:
    print(f"ERROR loading ML pipeline: {e}"); exit()

# 2. Status Map (Dynamically created based on loaded encoder)
STATUS_MAP_TO_FRONTEND = {}
critical_label_found = None
for cls in le_classes:
    cls_lower = cls.lower()
    if 'healthy' in cls_lower: STATUS_MAP_TO_FRONTEND[cls] = 'Healthy'
    elif 'stressed' in cls_lower: STATUS_MAP_TO_FRONTEND[cls] = 'Warning'
    elif 'damaged' in cls_lower or 'critical' in cls_lower:
        STATUS_MAP_TO_FRONTEND[cls] = 'Critical'
        critical_label_found = cls # Store the actual name ('Damaged' or 'Critical')
    else: STATUS_MAP_TO_FRONTEND[cls] = 'Warning'
print(f"-> Status Map (Model -> Frontend): {STATUS_MAP_TO_FRONTEND}")


# 3. Blockchain Config (Using values from your code)
GANACHE_URL = "http://127.0.0.1:7545"
CONTRACT_ADDRESS = "YOUR_DEPLOYED_CONTRACT_ADDRESS_HERE" # From your code
ABI_FILE_PATH = Path("contract_abi.json")
DEPLOYER_PRIVATE_KEY = "YOUR_DEPLOYER_PRIVATE_KEY_HERE" # From your code
WORKORDERS_DIR = Path("workorders")
WORKORDERS_DIR.mkdir(exist_ok=True)

# --- [ADDED Serial Port Configuration] ---
SERIAL_PORT = "COM6"  # <-- !! EDIT THIS if needed !!
BAUD_RATE = 115200
# ---

# --- [ADDED In-Memory Store for ESP32 Data] ---
latest_esp32_data = {
    "ax": 0.0, "ay": 0.0, "az": 0.0, "rms": 0.0, "load": 70.0, # Includes load read from serial
    "timestamp": None,
}
data_lock = threading.Lock() # To prevent race conditions
serial_running = True # Flag to control the serial thread
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

# Web3 connection, account, and contract loading logic
if not web3.is_connected():
    print(f"ERROR: Failed to connect to Ganache at {GANACHE_URL}")
else:
    print(f"Connected to Ethereum node: {GANACHE_URL}")
    # Validate Private Key and setup account
    if not DEPLOYER_PRIVATE_KEY or DEPLOYER_PRIVATE_KEY == "YOUR_GANACHE_ACCOUNT_PRIVATE_KEY_HERE":
         print("ERROR: DEPLOYER_PRIVATE_KEY is not set in the configuration.")
    else:
        try:
            account = web3.eth.account.from_key(DEPLOYER_PRIVATE_KEY)
            web3.eth.default_account = account.address
            print(f"Using account address: {account.address}")
            # Check balance (optional but good sanity check)
            balance = web3.eth.get_balance(account.address)
            print(f"Account Balance: {web3.from_wei(balance, 'ether')} ETH")
            if balance == 0:
                 print("WARNING: Account has zero balance. Transactions will likely fail.")
        except ValueError as e:
             print(f"ERROR: Invalid DEPLOYER_PRIVATE_KEY: {e}")
             account = None # Ensure account is None if key is bad

    # Validate Contract Address and ABI before loading contract
    if not CONTRACT_ABI:
        print("Contract not loaded: Missing or invalid ABI.")
    elif not CONTRACT_ADDRESS or CONTRACT_ADDRESS == "YOUR_DEPLOYED_CONTRACT_ADDRESS_HERE":
        print("Contract not loaded: CONTRACT_ADDRESS is not set.")
    elif not web3.is_address(CONTRACT_ADDRESS):
         print(f"ERROR: Invalid CONTRACT_ADDRESS format: {CONTRACT_ADDRESS}")
    else:
         try:
             # Check if contract code exists at the address
             code = web3.eth.get_code(CONTRACT_ADDRESS)
             if code == b'\x00' or code == b'0x' or code == b'':
                  print(f"ERROR: No contract code found at address {CONTRACT_ADDRESS}. Was it deployed correctly?")
             else:
                 contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)
                 print(f"Smart contract interface loaded for address: {CONTRACT_ADDRESS}")
                 # You could optionally try calling a view/pure function here to test interaction
                 # e.g., if contract has `owner()`: contract.functions.owner().call()
         except Exception as e:
             print(f"ERROR loading smart contract: {e}")
             contract = None


# --- [ADDED Serial Reading Thread Function] ---
def serial_reader_thread():
    """Continuously reads data from the serial port in a background thread."""
    global latest_esp32_data, serial_running
    ser = None
    while serial_running:
        try:
            if ser is None or not ser.is_open:
                print(f"Attempting to connect to serial port {SERIAL_PORT}...")
                ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
                time.sleep(2) # Give connection time
                if ser.is_open:
                    print(f"Successfully connected to {SERIAL_PORT}.")
                else:
                    print(f"Failed to open {SERIAL_PORT} on creation. Retrying...")
                    time.sleep(5)
                    continue

            line = ser.readline().decode('utf-8', errors='ignore').strip()

            if line:
                parts = line.split(',')
                if len(parts) >= 6:
                    try:
                        # Assuming order: ts,ax,ay,az,rms,load
                        _, ax_str, ay_str, az_str, rms_str, load_str = parts[:6]
                        ax = float(ax_str)
                        ay = float(ay_str)
                        az = float(az_str)
                        rms = float(rms_str)
                        load = float(load_str) # Read the load value from serial
                        timestamp = datetime.datetime.utcnow().isoformat() + 'Z'

                        # Update shared data structure safely
                        with data_lock:
                            latest_esp32_data["ax"] = ax
                            latest_esp32_data["ay"] = ay
                            latest_esp32_data["az"] = az
                            latest_esp32_data["rms"] = rms
                            latest_esp32_data["load"] = load # Store the actual load read
                            latest_esp32_data["timestamp"] = timestamp

                    except ValueError:
                        pass # Ignore lines that can't be fully parsed as numbers
                    except Exception as parse_e:
                        print(f"Serial Read Error: Unexpected issue parsing line '{line}': {parse_e}")

        except serial.SerialException as se:
            print(f"Serial Error: {se}. Will attempt to reconnect...")
            if ser and ser.is_open:
                ser.close()
            ser = None
            time.sleep(5)
        except Exception as e:
            print(f"Unexpected error in serial thread: {e}")
            time.sleep(5)

    if ser and ser.is_open:
        ser.close()
    print("Serial reader thread finished.")
# --- [END Serial Thread] ---


# --- REUSABLE PROCESSING FUNCTION ---
# (Unchanged - Takes load as argument)
def process_sensor_data(ax, ay, az, rms, load):
    """
    Takes sensor inputs, runs calculations and ML model,
    returns metrics dict and ai_verdict dict.
    Uses 4 features for model: [ax, ay, az, magnitude]
    Uses load for impact force calculation.
    """
    global model, scaler, label_encoder, critical_threshold, STATUS_MAP_TO_FRONTEND, critical_label_found, le_classes

    load_clipped = max(0.0, min(load, 1500.0))
    peak_g = max(abs(ax), abs(ay), abs(az))
    impact_force_N = load_clipped * peak_g * 9.81
    health_score = calculate_health_score_from_impact(impact_force_N)
    accel_magnitude = math.sqrt(ax**2 + ay**2 + az**2)

    features_for_model = [ax, ay, az, accel_magnitude]
    features_input = np.array([features_for_model])
    scaled_features_input = scaler.transform(features_input)
    numeric_prediction = model.predict(scaled_features_input)[0]
    raw_string_prediction = label_encoder.inverse_transform([numeric_prediction])[0]

    corrected_string_prediction = raw_string_prediction
    forced_by_rule = False
    if critical_threshold is not None:
        threshold = float(critical_threshold)
        if accel_magnitude > threshold and critical_label_found:
            corrected_string_prediction = critical_label_found
            forced_by_rule = True

    status_label = STATUS_MAP_TO_FRONTEND.get(corrected_string_prediction, 'Warning')

    confidence = 0.95
    probabilities_dict = {}
    if hasattr(model, 'predict_proba'):
        probabilities = model.predict_proba(scaled_features_input)[0]
        confidence = probabilities.max()
        probabilities_dict = dict(zip(le_classes, probabilities.tolist()))

    metrics = {
        'estimated_impact_force_N': float(impact_force_N),
        'structural_health_score': int(health_score),
        'overload_alert': load > 150, # Use original load for alert check
        'accel_peak_g': None,
        'accel_rms_g': float(rms),
        'loadcell_force_kg': float(load), # Return original load used in processing
        'accel_x_g': float(ax),
        'accel_y_g': float(ay),
        'accel_z_g': float(az),
    }
    ai_verdict = { 'label': str(status_label), 'confidence': float(confidence) }

    # Return extra info for debugging prints in calling functions
    return metrics, ai_verdict, probabilities_dict, forced_by_rule, raw_string_prediction, corrected_string_prediction

# --- HELPER for Health Score ---
# (Unchanged)
def calculate_health_score_from_impact(impact_force):
    SAFE_IMPACT = 0.0
    CRITICAL_IMPACT = 2000.0
    if impact_force <= SAFE_IMPACT: return 100
    if impact_force >= CRITICAL_IMPACT: return 0
    damage_percentage = impact_force / CRITICAL_IMPACT
    score = 100.0 * (1.0 - damage_percentage)
    return int(score)


# --- API ENDPOINTS ---

# (Manual input endpoint - unchanged)
@app.route('/api/road/demo/process-manual', methods=['POST'])
def process_manual_data_endpoint():
    """Endpoint for processing manual inputs."""
    try:
        data = request.json
        ax = float(data.get('accel_x_g', 0))
        ay = float(data.get('accel_y_g', 0))
        az = float(data.get('accel_z_g', 0))
        rms = float(data.get('accel_rms_g', 0))
        load = float(data.get('loadcell_force_kg', 0)) # Uses load from form

        # Call the reusable processing function with manual load
        metrics, ai_verdict, probs, forced, raw_pred, corr_pred = process_sensor_data(ax, ay, az, rms, load)

        # Debug prints (unchanged)
        print("-" * 30); print("MANUAL INPUT PROCESSED:")
        print(f"  Inputs: ax={ax:.3f}, ay={ay:.3f}, az={az:.3f}, rms={rms:.3f}, load={load:.1f}")
        if probs: print(f"  Probabilities: { {k: f'{v:.3f}' for k,v in probs.items()} }")
        if forced: print(f"  HARD RULE APPLIED -> {corr_pred}")
        print(f"  Prediction Sent: {ai_verdict['label']} (Conf: {ai_verdict['confidence']:.2f})")
        print(f"  Metrics Sent: Impact={metrics['estimated_impact_force_N']:.1f}N, Score={metrics['structural_health_score']}%")
        print("-" * 30)

        return jsonify({'metrics': metrics, 'ai_verdict': ai_verdict})

    except Exception as e:
        print(f"Error processing manual data: {e}"); return jsonify({"error": f"Internal server error: {e}"}), 500


# --- [LATEST DATA ENDPOINT - MODIFIED] ---
@app.route('/api/road/demo/latest', methods=['GET'])
def get_latest_demo_data():
    """Endpoint for frontend to fetch the latest processed data read from serial."""
    global latest_esp32_data
    try:
        with data_lock:
            # Get the latest data read by the serial thread
            ax = latest_esp32_data["ax"]
            ay = latest_esp32_data["ay"]
            az = latest_esp32_data["az"]
            rms = latest_esp32_data["rms"]
            # load = latest_esp32_data["load"] # We ignore the load read from serial here
            timestamp = latest_esp32_data["timestamp"]

        if timestamp is None:
             # No data received yet from serial
             print("GET /latest: No serial data available yet.")
             # Return default state (unchanged)
             default_metrics = { 'estimated_impact_force_N': 0, 'structural_health_score': 100,
                                 'overload_alert': False, 'accel_peak_g': None, 'accel_rms_g': 0,
                                 'loadcell_force_kg': 70.0, 'accel_x_g': 0, 'accel_y_g': 0, 'accel_z_g': 0 } # Default load to 70
             default_verdict = { 'label': 'Healthy', 'confidence': 1.0 }
             return jsonify({'metrics': default_metrics, 'ai_verdict': default_verdict, 'timestamp': None})

        # Process the latest stored data using the reusable function,
        # ALWAYS pass load=70.0 for real-time mode processing.
        fixed_load_for_realtime = 70.0
        metrics, ai_verdict, probs, forced, raw_pred, corr_pred = process_sensor_data(ax, ay, az, rms, fixed_load_for_realtime)

        # Debug prints (unchanged, will show load=70.0 being used)
        print("-" * 30); print("GET /LATEST PROCESSED:")
        print(f"  Using Stored: ax={ax:.3f}, ay={ay:.3f}, az={az:.3f}, rms={rms:.3f}, FIXED load={fixed_load_for_realtime:.1f}")
        if probs: print(f"  Probabilities: { {k: f'{v:.3f}' for k,v in probs.items()} }")
        if forced: print(f"  HARD RULE APPLIED -> {corr_pred}")
        print(f"  Prediction Sent: {ai_verdict['label']} (Conf: {ai_verdict['confidence']:.2f})")
        print(f"  Metrics Sent: Impact={metrics['estimated_impact_force_N']:.1f}N, Score={metrics['structural_health_score']}%")
        print("-" * 30)

        # Add the timestamp to the response
        return jsonify({'metrics': metrics, 'ai_verdict': ai_verdict, 'timestamp': timestamp})

    except Exception as e:
        print(f"Error fetching latest data: {e}"); return jsonify({"error": f"Internal server error: {e}"}), 500


# --- [REFINED WORKORDER ENDPOINT] ---
@app.route('/api/workorder/create', methods=['POST'])
def create_workorder():
    """
    Generates workorder details, saves to JSON file, calls the smart contract,
    and returns details including the transaction hash.
    """
    global contract, account, web3 # Use the globally loaded objects

    # Check Web3 setup first for better error messages
    if not web3 or not web3.is_connected():
        return jsonify({"error": "Backend not connected to Ethereum node. Is Ganache running?"}), 503
    if account is None:
         return jsonify({"error": "Backend Ethereum account not configured correctly. Check DEPLOYER_PRIVATE_KEY."}), 500
    if contract is None:
         return jsonify({"error": "Smart contract not loaded correctly. Check CONTRACT_ADDRESS and contract_abi.json."}), 500

    try:
        # 1. Get data from frontend
        data = request.json
        road_id = data.get('roadId')
        road_name = data.get('roadName')
        road_location = data.get('roadLocation')
        current_status = data.get('currentStatus') # Status from frontend badge ('Healthy', 'Warning', 'Critical')

        if not all([road_id, road_name, road_location, current_status]):
            return jsonify({"error": "Missing required workorder data (roadId, roadName, roadLocation, currentStatus)"}), 400

        # 2. Generate Workorder ID and Timestamp
        timestamp_dt = datetime.datetime.utcnow()
        timestamp_iso = timestamp_dt.isoformat() + 'Z'
        # Slightly more robust ID generation
        workorder_id = f"WO-{road_id.replace('_','-').split('-')[0][-4:]}-{int(timestamp_dt.timestamp() * 1000) % 100000}"

        # 3. Prepare Workorder Data Object for JSON file
        workorder_data = {
            'workorderId': workorder_id,
            'roadId': road_id,
            'roadName': road_name,
            'roadLocation': road_location,
            'timestamp': timestamp_iso,
            'status': 'pending_blockchain', # Initial file status
            'currentRoadStatus': current_status, # Status that triggered the workorder
            'blockchainTransactionHash': None
        }
        file_path = WORKORDERS_DIR / f"{workorder_id}.json"

        # 4. Save Workorder Data to JSON File (before blockchain interaction)
        try:
            with open(file_path, 'w') as f:
                json.dump(workorder_data, f, indent=4)
            print(f"Workorder data saved locally to: {file_path}")
        except Exception as file_error:
            # Log warning but proceed with blockchain attempt
            print(f"WARNING: Failed to save workorder JSON to {file_path}: {file_error}")


        # 5. Interact with Smart Contract
        print("-" * 50)
        print(f"Attempting Blockchain Transaction for Workorder: {workorder_id}")
        print(f"  Data: RoadID='{road_id}', Timestamp='{timestamp_iso}', Status='active', Name='{road_name}'")


        # --- [Verify Function Name & Arguments match Workorder.sol] ---
        # function createWorkorder(string memory _workorderId, string memory _roadId, string memory _timestamp, string memory _status, string memory _roadName)
        # We send "active" as the initial status *to the blockchain*
        contract_function_call = contract.functions.createWorkorder(
            workorder_id,
            road_id,
            timestamp_iso,
            "active", # Contract stores initial status as 'active'
            road_name
        )
        # --- [End Verification] ---

        # Estimate gas
        estimated_gas = 300000 # Default fallback gas limit
        try:
             # Add 'from' address for estimation
             estimated_gas = contract_function_call.estimate_gas({'from': account.address})
             print(f"  Estimated Gas: {estimated_gas}")
        except Exception as gas_error:
             # Provide more context if estimation fails (e.g., contract likely to revert)
             err_str_gas = str(gas_error).lower()
             if "revert" in err_str_gas:
                 print(f"  ERROR: Gas estimation failed - Contract likely to revert: {gas_error}")
                 reason = "Unknown revert reason"
                 try: # Attempt to parse revert reason (fragile)
                     reason_match = re.search(r"revert reason string '(.*?)'", err_str_gas)
                     if reason_match: reason = reason_match.group(1)
                 except: pass
                 # Return error to frontend immediately if gas estimation reverts
                 return jsonify({"error": f"Smart contract reverted during gas estimation: {reason}"}), 400
             else:
                  print(f"  WARNING: Gas estimation failed: {gas_error}. Using fallback gas limit ({estimated_gas}).")


        # Build Transaction
        nonce = web3.eth.get_transaction_count(account.address)
        tx_params = {
            'chainId': web3.eth.chain_id,
            'gas': estimated_gas + 50000, # Add buffer
            'gasPrice': web3.eth.gas_price,
            'nonce': nonce,
            'from': account.address # Explicitly include sender
        }
        print(f"  Building Tx with Nonce: {nonce}, GasLimit: {tx_params['gas']}, GasPrice: {tx_params['gasPrice']}")
        tx = contract_function_call.build_transaction(tx_params)

        # Sign Transaction
        signed_tx = web3.eth.account.sign_transaction(tx, private_key=DEPLOYER_PRIVATE_KEY)

        # Send Transaction
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"  Transaction Sent. Hash: {tx_hash.hex()}")

        # Wait for Transaction Receipt (Blocking)
        print("  Waiting for transaction receipt...")
        # Increased timeout for potentially slower operations or nodes
        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)

        on_chain_hash = None # Initialize hash variable
        final_status_for_frontend = 'failed_blockchain' # Assume failure initially for frontend status

        if tx_receipt and tx_receipt.status == 1:
            print(f"  Transaction Successful! Block: {tx_receipt.blockNumber}, Gas Used: {tx_receipt.gasUsed}")
            on_chain_hash = tx_hash.hex()
            final_status_for_frontend = 'active' # Update status for frontend on success

            # --- Optionally: Update the JSON file with the hash and final status ---
            try:
                workorder_data['blockchainTransactionHash'] = on_chain_hash
                workorder_data['status'] = 'active_on_chain' # More specific status in file
                with open(file_path, 'w') as f:
                    json.dump(workorder_data, f, indent=4)
                print(f"  Updated JSON file with transaction hash and status.")
            except Exception as update_error:
                print(f"  WARNING: Failed to update JSON file with hash: {update_error}")
            # --- End optional update ---
        else:
            # Transaction failed on the blockchain
            failure_status = tx_receipt.status if tx_receipt else "Receipt Unavailable"
            print(f"  Transaction Failed! Status: {failure_status}")
            # --- Optionally: Update the JSON file with failure status ---
            try:
                workorder_data['status'] = 'failed_blockchain'
                with open(file_path, 'w') as f:
                    json.dump(workorder_data, f, indent=4)
                print(f"  Updated JSON file with failed status.")
            except Exception as update_error:
                 print(f"  WARNING: Failed to update JSON file with failed status: {update_error}")
            # ---
            # Raise exception to trigger the main error handling block below
            raise Exception(f"Blockchain transaction failed (Receipt Status: {failure_status}). Check Ganache logs for details (e.g., revert reason).")


        print("-" * 50)

        # 6. Return the details including the REAL hash and final status
        return jsonify({
            'workorderId': workorder_id,
            'timestamp': timestamp_iso,
            'onChainHash': on_chain_hash, # Will be None if transaction failed before sending or receipt status was 0
            'status': final_status_for_frontend # Return 'active' or 'failed_blockchain'
        })

    except Exception as e:
        # Catch specific Web3/Blockchain errors and provide clearer messages
        print(f"Error creating workorder: {e}")
        import traceback
        traceback.print_exc() # Print full traceback to console for debugging
        error_message = f"Internal server error: {e}"
        err_str = str(e).lower()
        # Add more specific error checks
        if "insufficient funds" in err_str:
             error_message = "Blockchain transaction failed: Insufficient funds for gas."
        elif "reverted" in err_str:
             # Try to extract revert reason if available in the exception message
             reason = "Check contract logic/inputs"
             match = re.search(r"(?:revert reason:|execution reverted:)\s*\'?([^\'}]+)\'?", err_str)
             if match: reason = match.group(1)
             error_message = f"Blockchain transaction failed: Smart contract reverted ({reason})."
        elif "nonce too low" in err_str or "replacement transaction underpriced" in err_str:
             error_message = "Blockchain transaction failed: Nonce error. Please restart the backend server."
        elif "unknown account" in err_str or "invalid sender" in err_str:
             error_message = "Blockchain transaction failed: Sending account configuration error (check Private Key)."
        elif "header not found" in err_str or "connection error" in err_str:
             error_message = "Blockchain connection error. Is Ganache running and accessible?"
        elif "could not transact" in err_str: # Catch-all for tx sending issues
              error_message = f"Blockchain transaction failed during sending: {e}"

        return jsonify({"error": error_message}), 500
# --- [END WORKORDER ENDPOINT] ---


# --- RUN THE APP ---
if __name__ == '__main__':
    # --- [START Serial Thread] ---
    print("Starting serial reader thread...")
    serial_thread = threading.Thread(target=serial_reader_thread, daemon=True)
    serial_thread.start()
    # ---
    print("Starting Flask application...")
    # Use use_reloader=False to prevent issues with the serial thread and Flask's auto-reloader
    app.run(debug=True, port=5000, use_reloader=False)

