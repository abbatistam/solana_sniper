# Raydium Sniper Trading Bot

## About

Raydium Sniper Trading Bot is a Python-based automated trading bot designed to monitor, buy, and sell newly listed tokens on the Raydium DEX. The bot uses the Solana blockchain and Raydium API to identify tokens added within the last 10 minutes, purchase them with SOL, and manage trades based on profit and loss thresholds.

## Features

- **Token Monitoring**: Fetches newly listed tokens on Raydium within a specified timeframe (last 10 minutes).
- **Automated Trading**: Buys and sells tokens directly on the Solana blockchain using specified criteria.
- **Profit and Loss Management**: Monitors price changes of purchased tokens and sells based on customizable profit and loss percentages.
- **Real-Time Price Fetching**: Retrieves the latest token prices from Raydium's API.
- **Secure Transactions**: Uses Solana's keypair-based signing for secure transactions.
- **Customizable Settings**: Configure minimum purchase amount, profit and loss thresholds, and monitoring intervals via CLI arguments.

---

## Prerequisites

1. **Python 3.8 or higher**  
   Install Python from [python.org](https://www.python.org/).

2. **Dependencies**  
   Install required libraries:

   ```bash
   pip install requests solders solana
   ```

3. **Private Key**  
   A valid Solana wallet private key in base58 format is required for signing transactions.

4. **Sufficient SOL Balance**  
   Ensure the wallet has enough SOL to cover token purchases and transaction fees.

---

## Installation

Ensure the wallet has enough SOL to cover token purchases and transaction fees.

```bash
git clone https://gitlab.com/solana-development/raydium-sniper-trading-bot.git
cd raydium-sniper-bot
```

## Install Dependencies

Ensure the wallet has enough SOL to cover token purchases and transaction fees.

```bash
pip install -r requirements.txt
```

## Usage

Run the bot using the following command:

```bash
python raydium.py --private-key <YOUR_PRIVATE_KEY> [OPTIONS]
```

## Options

--min Minimum SOL to use for buying tokens 0.1 SOL
--private-key Private key of the wallet (required) None
--profit Profit percentage to sell tokens 60.0%
--loss Loss percentage to sell tokens 60.0%

## Example

Run the bot using the following command:

```bash
python raydium.py --private-key <YOUR_PRIVATE_KEY> --min 0.2 --profit 50 --loss 30
```

## How It Works

1. **Fetch New Tokens**  
   The bot retrieves the latest token pairs from the Raydium API and filters tokens listed within the last 10 minutes.

2. **Buy Tokens**  
   For each eligible token, the bot initiates a purchase using a specified amount of SOL. The purchase is adjusted for slippage to ensure successful swaps.

3. **Monitor Prices**  
   The bot continuously tracks the price changes of purchased tokens.

4. **Sell Tokens**  
   Based on the profit or loss thresholds, the bot triggers sell transactions to optimize returns.

## Important Notes

**Use Caution**  
 Automated trading involves financial risks. Ensure you understand the risks and test with small amounts before scaling.

**Private Key Security**  
Keep your private key secure and do not share it. Avoid hardcoding sensitive information.

**Network Latency**  
 Real-time trading may be affected by network delays or API response times.
