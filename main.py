import os
import time
import json
from dotenv import load_dotenv
from web3 import Web3
from telegram_utils import send_deposit_notification, send_error_notification, send_log

# Load environment variables
load_dotenv()

TARGET_WALLET_ADDRESS = os.environ.get("TARGET_WALLET_ADDRESS")
ETH_RPC_URL = os.environ.get("ETH_RPC_URL")
BASE_RPC_URL = os.environ.get("BASE_RPC_URL")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", 15))

if not TARGET_WALLET_ADDRESS or "your_" in TARGET_WALLET_ADDRESS:
    print("Please set TARGET_WALLET_ADDRESS in your .env file.")
    exit(1)

# Initialize Web3 providers
eth_w3 = Web3(Web3.HTTPProvider(ETH_RPC_URL))
base_w3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))

target_wallet = Web3.to_checksum_address(TARGET_WALLET_ADDRESS)

# USDC Contract Addresses (Mainnet)
ETH_USDC_ADDRESS = Web3.to_checksum_address("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")
BASE_USDC_ADDRESS = Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")

# Minimal ERC20 ABI for Transfer events
ERC20_ABI = json.loads('[{"anonymous":false,"inputs":[{"indexed":true,"name":"from","type":"address"},{"indexed":true,"name":"to","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Transfer","type":"event"}]')

eth_usdc_contract = eth_w3.eth.contract(address=ETH_USDC_ADDRESS, abi=ERC20_ABI)
base_usdc_contract = base_w3.eth.contract(address=BASE_USDC_ADDRESS, abi=ERC20_ABI)

def poll_once(last_eth_block, last_base_block):
    new_eth_block = last_eth_block
    new_base_block = last_base_block

    # --- Check Ethereum ---
    try:
        latest_eth_block = eth_w3.eth.block_number
        if latest_eth_block > last_eth_block:
            send_log(f"Scanning ETH blocks {last_eth_block + 1} to {latest_eth_block}...")
            events = eth_usdc_contract.events.Transfer.get_logs(from_block=last_eth_block + 1, to_block=latest_eth_block)
            for event in events:
                if event.args.to == target_wallet:
                    amount = event.args.value / 1e6
                    
                    # Pretty message for Bot 1
                    pretty_msg = f"🟢 <b>USDC Deposit Detected!</b>\n\n💰 <b>Amount:</b> {amount:,.2f} USDC\n🌐 <b>Network:</b> Ethereum\n🏦 <b>Address:</b> <code>{target_wallet}</code>"
                    
                    # Raw message for Bot 2
                    raw_msg = f"USDC DEPOSIT DETECTED: {amount} USDC on Ethereum."
                    
                    send_deposit_notification(pretty_msg, raw_msg)
            
            # Update block ONLY if get_logs was successful (guarantees no skipped blocks on error)
            new_eth_block = latest_eth_block
    except Exception as e:
        send_error_notification(f"Error fetching ETH events: {e}")
    
    # --- Check Base ---
    try:
        latest_base_block = base_w3.eth.block_number
        if latest_base_block > last_base_block:
            send_log(f"Scanning BASE blocks {last_base_block + 1} to {latest_base_block}...")
            events = base_usdc_contract.events.Transfer.get_logs(from_block=last_base_block + 1, to_block=latest_base_block)
            for event in events:
                if event.args.to == target_wallet:
                    amount = event.args.value / 1e6
                    
                    # Pretty message for Bot 1
                    pretty_msg = f"🔵 <b>USDC Deposit Detected!</b>\n\n💰 <b>Amount:</b> {amount:,.2f} USDC\n🌐 <b>Network:</b> Base\n🏦 <b>Address:</b> <code>{target_wallet}</code>"
                    
                    # Raw message for Bot 2
                    raw_msg = f"USDC DEPOSIT DETECTED: {amount} USDC on Base."
                    
                    send_deposit_notification(pretty_msg, raw_msg)
            
            # Update block ONLY if get_logs was successful
            new_base_block = latest_base_block
    except Exception as e:
        send_error_notification(f"Error fetching BASE events: {e}")

    return new_eth_block, new_base_block

def check_deposits():
    send_log(f"Started USDC Deposit Bot.\nMonitoring: {target_wallet}\nInterval: {POLL_INTERVAL} seconds")
    
    try:
        last_eth_block = eth_w3.eth.block_number
        last_base_block = base_w3.eth.block_number
        send_log(f"Initial blocks - ETH: {last_eth_block}, BASE: {last_base_block}")
    except Exception as e:
        send_error_notification(f"Failed to initialize block numbers. Is RPC up? Error: {e}")
        return
    
    while True:
        try:
            last_eth_block, last_base_block = poll_once(last_eth_block, last_base_block)
        except Exception as e:
            send_error_notification(f"Main loop critical error: {e}")

        time.sleep(POLL_INTERVAL)

from keep_alive import keep_alive

if __name__ == "__main__":
    # Start the Flask keep-alive server in a background thread
    keep_alive()
    
    check_deposits()
