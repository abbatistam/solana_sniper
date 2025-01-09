import requests
import argparse
import time
import json
import pandas as pd
from datetime import datetime, timedelta
from solders.transaction import VersionedTransaction
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from flask import Flask

# Flask app for health check
app = Flask(__name__)

@app.route('/ping', methods=['GET'])
def ping():
    return "Pong!", 200

# Mantener las configuraciones originales
RAYDIUM_API_URL = "https://api.raydium.io"
rpc_endpoint = "https://api.mainnet-beta.solana.com"

class SimulatedWallet:
    def __init__(self, initial_balance_usd=100):
        self.usd_balance = initial_balance_usd
        self.holdings = {}  # {token_name: {'amount': float, 'entry_price': float}}
        self.transactions = []
        
    def record_transaction(self, token_name, tx_type, amount, price, usd_value):
        timestamp = datetime.now()
        transaction = {
            'timestamp': timestamp,
            'token': token_name,
            'type': tx_type,
            'amount': amount,
            'price': price,
            'usd_value': usd_value,
            'wallet_balance': self.usd_balance
        }
        self.transactions.append(transaction)
        print(f"\nTransaction recorded: {tx_type} {token_name}")
        print(f"Amount: {amount:.6f} @ ${price:.6f}")
        print(f"USD Value: ${usd_value:.2f}")
        print(f"Wallet Balance: ${self.usd_balance:.2f}")
        
    def can_buy(self, usd_amount):
        return self.usd_balance >= usd_amount

def get_token_price(token_name):
    """Fetch the current price of a token."""
    try:
        response = requests.get(f"{RAYDIUM_API_URL}/v2/main/pairs")
        response.raise_for_status()
        pairs = response.json()
        for pair in pairs:
            if pair["name"].upper() == token_name.upper():
                return pair["price"]
        return None
    except Exception as e:
        print(f"Error fetching price: {e}")
        return None

def fetch_new_tokens():
    """Fetch tokens added to Raydium in the last 10 minutes."""
    try:
        response = requests.get(f"{RAYDIUM_API_URL}/v2/main/pairs")
        response.raise_for_status()
        pairs = response.json()

        ten_minutes_ago = datetime.now() - timedelta(minutes=10)
        new_pairs = []
        
        for pair in pairs:
            if "createdAt" in pair and isinstance(pair["createdAt"], (int, float)):
                created_at = datetime.fromtimestamp(pair["createdAt"])
                if created_at > ten_minutes_ago and "SOL" in pair["name"]:
                    new_pairs.append(pair)

        if new_pairs:
            print(f"Found {len(new_pairs)} new tokens: {[pair['name'] for pair in new_pairs]}")
        else:
            print("No new tokens found in the last 10 minutes.")

        return new_pairs

    except Exception as e:
        print(f"Error fetching new tokens: {e}")
        return []

def save_results(transactions):
    """Save transactions to CSV file"""
    try:
        df = pd.DataFrame(transactions)
        df.to_csv('trading_simulation_results.csv', index=False)
        print("Results saved to trading_simulation_results.csv")
    except Exception as e:
        print(f"Error saving results: {e}")

def parse_arguments():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Raydium DEX Trading Bot Simulator")
    parser.add_argument("--profit", type=float, default=60.0, help="Profit percentage to sell (default: 60%)")
    parser.add_argument("--loss", type=float, default=60.0, help="Loss percentage to sell (default: 60%)")
    return parser.parse_args()

def main_bot():
    """Main entry point for the simulator"""
    args = parse_arguments()
    wallet = SimulatedWallet(100)  # Start with $100 USD
    
    print("Starting bot in simulation mode with $100 USD")
    print("Monitoring for new tokens...")
    
    try:
        while True:
            new_tokens = fetch_new_tokens()
            
            for token in new_tokens:
                token_name = token['name']
                token_price = token['price']
                
                # Simulate buying with $10 USD per trade
                usd_amount = 10
                if wallet.can_buy(usd_amount):
                    token_amount = usd_amount / token_price
                    wallet.usd_balance -= usd_amount
                    wallet.holdings[token_name] = {
                        'amount': token_amount,
                        'entry_price': token_price
                    }
                    wallet.record_transaction(token_name, 'BUY', token_amount, token_price, usd_amount)
                
            # Monitor existing holdings
            for token_name in list(wallet.holdings.keys()):
                current_price = get_token_price(token_name)
                if current_price is None:
                    continue
                    
                entry_price = wallet.holdings[token_name]['entry_price']
                token_amount = wallet.holdings[token_name]['amount']
                price_change = ((current_price - entry_price) / entry_price) * 100
                
                print(f"Monitoring {token_name}: Entry: ${entry_price:.6f} Current: ${current_price:.6f} Change: {price_change:.2f}%")
                
                # Check sell conditions
                if price_change >= args.profit or price_change <= -args.loss:
                    usd_value = token_amount * current_price
                    wallet.usd_balance += usd_value
                    wallet.record_transaction(token_name, 'SELL', token_amount, current_price, usd_value)
                    del wallet.holdings[token_name]
            
            # Save results periodically
            save_results(wallet.transactions)
            time.sleep(60)  # Wait 1 minute before next iteration
            
    except KeyboardInterrupt:
        print("\nBot stopped by user")
        print("\nFinal Results:")
        print(f"Final Balance: ${wallet.usd_balance:.2f}")
        print(f"Total Trades: {len(wallet.transactions)}")
        save_results(wallet.transactions)
    except Exception as e:
        print(f"Error in main loop: {e}")
        save_results(wallet.transactions)

if __name__ == "__main__":
    import threading
    # Run bot and Flask server in parallel
    bot_thread = threading.Thread(target=main_bot, daemon=True)
    bot_thread.start()
    app.run(host="0.0.0.0", port=5000)
