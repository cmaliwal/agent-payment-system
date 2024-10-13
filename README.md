# Agent Payment System

This repository demonstrates a decentralized payment system between two autonomous agents, Alice and Bob, built using the `uAgents` framework. The system allows Alice to request payments, Bob to negotiate, process, and send payments, and Alice to confirm and verify the transaction. This implementation includes features such as payment negotiation, signature verification, transaction validation, and preventing transaction reuse.

## Features

- **Payment Requests:** Alice can request payments from Bob, signing the request with her wallet.
- **Payment Negotiation:** Bob checks his balance and offers an amount for payment.
- **Payment Processing:** Once both parties agree, Bob sends the payment and transaction info to Alice.
- **Transaction Verification:** Alice verifies the transaction on the ledger and confirms its success.
- **Transaction Integrity:** Reuse of transaction hashes is prevented by tracking used transactions.
- **Signature Verification:** All communication between agents is verified using cryptographic signatures.

## Requirements

- Python 3.8+
- `uAgents` framework
- Fetch.ai testnet tokens (for payments)

## Setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/yourusername/agent-payment-system.git
   cd agent-payment-system
   ```

2. **Create a virtual environment and activate it:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install the required dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up Fetch.ai testnet tokens for agents:**

   - Ensure both agents (Alice and Bob) have enough test tokens for sending payments on the Fetch.ai network. You can request tokens via the [Fetch.ai faucet](https://faucet.fetch.ai/).

## Running the Agents

### 1. Start Bob's Agent:

Bob's agent will wait for a payment request from Alice, negotiate the payment, and then send it.

```bash
python bob_agent.py
```

### 2. Start Alice's Agent:

Alice's agent will periodically request payments, verify the transactions received, and send confirmation messages.

```bash
python alice_agent.py
```

## Key Components

- **alice_agent.py**: Handles payment requests, verifies incoming payments, and confirms successful transactions.
- **bob_agent.py**: Negotiates payments, processes them, and sends transaction information to Alice.
- **common.py**: Defines the models used for communication between agents, such as `PaymentRequest`, `TransactionInfo`, and `PaymentConfirmation`.

## How it Works

1. **Payment Request**: Alice sends a signed payment request to Bob.
2. **Negotiation**: Bob checks his balance and negotiates the amount to be sent back to Alice.
3. **Payment Processing**: Bob sends the payment, and transaction information is shared with Alice.
4. **Verification**: Alice verifies the transaction on the ledger and sends a confirmation message to Bob.

