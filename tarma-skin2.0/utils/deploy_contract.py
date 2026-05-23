import json
from web3 import Web3
from solcx import compile_standard, install_solc
import os
from pathlib import Path

# --- [!! EDIT THESE !!] ---
GANACHE_URL = "http://127.0.0.1:7545" # Your Ganache RPC URL
# WARNING: Storing private keys directly in code is insecure for production.
DEPLOYER_PRIVATE_KEY = "YOUR_PRIVATE_KEY_HERE" # Replace with your Ganache account private key
# Path to your Solidity contract
CONTRACT_SOURCE_PATH = Path("contracts/Workorder.sol")
# Output file for the ABI
ABI_OUTPUT_PATH = Path("contract_abi.json")
# --- [!! END EDITS !!] ---

# Check if contract source exists
if not CONTRACT_SOURCE_PATH.exists():
    print(f"ERROR: Contract source file not found at {CONTRACT_SOURCE_PATH}")
    exit()

# Install and set Solidity compiler version (match the pragma in your .sol file)
SOLC_VERSION = "0.8.17"
try:
    print(f"Checking/installing solc version {SOLC_VERSION}...")
    install_solc(SOLC_VERSION)
    print(f"solc {SOLC_VERSION} installed/verified.")
except Exception as e:
    print(f"ERROR installing solc {SOLC_VERSION}: {e}")
    exit()


# Compile the Solidity contract
print(f"Compiling {CONTRACT_SOURCE_PATH}...")
with open(CONTRACT_SOURCE_PATH, "r") as file:
    contract_source_code = file.read()

compiled_sol = compile_standard(
    {
        "language": "Solidity",
        "sources": {CONTRACT_SOURCE_PATH.name: {"content": contract_source_code}},
        "settings": {
            "outputSelection": {
                "*": {
                    "*": ["abi", "metadata", "evm.bytecode", "evm.bytecode.sourceMap"]
                }
            }
        },
    },
    solc_version=SOLC_VERSION,
)

# Extract ABI and Bytecode
try:
    # Adjust key based on your contract file and contract name
    contract_name = "WorkorderManager"
    contract_interface = compiled_sol["contracts"][CONTRACT_SOURCE_PATH.name][contract_name]
    abi = contract_interface["abi"]
    bytecode = contract_interface["evm"]["bytecode"]["object"]
    print("Compilation successful.")
except KeyError as e:
    print(f"ERROR: Could not find contract '{contract_name}' in compiled output.")
    print("Please check the contract name and file path.")
    print(f"Details: {e}")
    exit()

# Save ABI to file
print(f"Saving ABI to {ABI_OUTPUT_PATH}...")
with open(ABI_OUTPUT_PATH, "w") as f:
    json.dump(abi, f, indent=4)
print("ABI saved.")

# Connect to Ganache
web3 = Web3(Web3.HTTPProvider(GANACHE_URL))
if not web3.is_connected():
    print(f"ERROR: Failed to connect to Ganache at {GANACHE_URL}")
    exit()
print(f"Connected to Ethereum node: {GANACHE_URL}")

# Set up account
try:
    account = web3.eth.account.from_key(DEPLOYER_PRIVATE_KEY)
    web3.eth.default_account = account.address
    print(f"Using deployer account: {account.address}")
    # Check balance (optional)
    balance = web3.eth.get_balance(account.address)
    print(f"Account balance: {web3.from_wei(balance, 'ether')} ETH")
    if balance == 0:
         print("WARNING: Deployer account has zero balance. Deployment will likely fail.")
except ValueError as e:
    print(f"ERROR: Invalid DEPLOYER_PRIVATE_KEY: {e}")
    exit()

# Create Contract Instance
Contract = web3.eth.contract(abi=abi, bytecode=bytecode)

# Estimate gas for deployment
try:
    estimated_gas = Contract.constructor().estimate_gas({'from': account.address})
    print(f"Estimated gas for deployment: {estimated_gas}")
except Exception as e:
    print(f"WARNING: Gas estimation failed: {e}. Using default.")
    estimated_gas = 1500000 # Fallback gas limit

# Build Transaction
nonce = web3.eth.get_transaction_count(account.address)
tx = Contract.constructor().build_transaction(
    {
        "chainId": web3.eth.chain_id,
        "gas": estimated_gas + 100000, # Add buffer
        "gasPrice": web3.eth.gas_price,
        "nonce": nonce,
    }
)

# Sign Transaction
signed_tx = web3.eth.account.sign_transaction(tx, private_key=DEPLOYER_PRIVATE_KEY)

# Send Transaction
print("Deploying contract...")
tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
print(f"Transaction sent. Hash: {tx_hash.hex()}")

# Wait for Transaction Receipt
print("Waiting for transaction receipt...")
try:
    tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180) # Wait up to 3 mins
except Exception as e:
     print(f"ERROR waiting for receipt: {e}")
     print("Check Ganache for transaction status.")
     exit()


if tx_receipt.status == 1:
    contract_address = tx_receipt.contractAddress
    print("-" * 50)
    print("CONTRACT DEPLOYED SUCCESSFULLY!")
    print(f"  Contract Address: {contract_address}")
    print(f"  Transaction Hash: {tx_hash.hex()}")
    print(f"  Block Number: {tx_receipt.blockNumber}")
    print("-" * 50)
    print("\nACTION REQUIRED:")
    print("1. Copy the Contract Address above.")
    print("2. Paste it into the 'CONTRACT_ADDRESS' variable in your app.py file.")
    print("-" * 50)
else:
    print("-" * 50)
    print("CONTRACT DEPLOYMENT FAILED!")
    print(f"  Transaction Hash: {tx_hash.hex()}")
    print(f"  Status Code: {tx_receipt.status}")
    print("  Check Ganache logs for more details (e.g., out of gas, revert reason).")
    print("-" * 50)
