import os
from uagents import Agent, Context
from uagents.setup import fund_agent_if_low
from uagents.crypto import Identity
import hashlib
from common import PaymentRequest, TransactionInfo, PaymentNegotiation, PaymentAgreement, HandshakeRequest, PaymentConfirmation

AMOUNT = 100
DENOM = "atestfet"

# Initialize Bob's agent
PORT = 8001
bob = Agent(name="bob", seed="bob secret phrase", port=PORT, endpoint=f"http://localhost:{PORT}/submit")

# Ensure Bob has enough funds to send the payment
fund_agent_if_low(bob.wallet.address(), min_balance=AMOUNT)

@bob.on_event("startup")
async def introduce(ctx: Context):
    ctx.logger.info(f"Agent started with address: {ctx.agent.address}")

# Helper function to create the digest of a message
def encode(message: str) -> bytes:
    hasher = hashlib.sha256()
    hasher.update(message.encode())
    return hasher.digest()

@bob.on_message(model=PaymentRequest)
async def verify_signature_and_store_request(ctx: Context, sender: str, msg: PaymentRequest):
    """
    Verifies the signature of Alice's request and stores it for further processing.
    """
    # Create the digest of the message (PaymentRequest wallet address + amount + denom)
    digest = encode(f"{msg.wallet_address}{msg.amount}{msg.denom}")

    # Use verify_digest to verify Alice's signature
    if not Identity.verify_digest(sender, digest, msg.signature):
        ctx.logger.error("Signature verification failed.")
        return

    ctx.logger.info(f"Received valid payment request from {sender}: {msg.amount} {msg.denom}")
    
    # Serialize the payment request to a dictionary for storage
    payment_request_serialized = msg.model_dump()

    # Store the serialized payment request in agent storage for later processing after handshake
    ctx.storage.set("pending_payment_request", payment_request_serialized)

    # Initiate the handshake with Alice
    ctx.logger.info("Initiating handshake with Alice.")
    await ctx.send(sender, HandshakeRequest(confirmation=True))

@bob.on_message(model=HandshakeRequest)
async def initiate_handshake(ctx: Context, sender: str, msg: HandshakeRequest):
    """
    Initiates a handshake with Alice before proceeding with payment processing.
    """
    if msg.confirmation:
        ctx.logger.info("Handshake confirmed with Alice, ready to proceed with payment.")
        
        # Retrieve the serialized payment request from storage and deserialize it
        pending_request_serialized = ctx.storage.get("pending_payment_request")
        if pending_request_serialized:
            pending_request = PaymentRequest(**pending_request_serialized)
            ctx.logger.info(f"Proceeding with payment negotiation for request: {pending_request}")

            # Use query_bank_balance to check Bob's available balance
            available_balance = ctx.ledger.query_bank_balance(bob.wallet.address(), pending_request.denom)
            
            # Proceed with negotiation based on Bob's available balance
            offer = min(pending_request.amount, available_balance)
            
            # Send the negotiation offer to Alice
            await ctx.send(sender, PaymentNegotiation(requested_amount=pending_request.amount, offered_amount=offer, denom=pending_request.denom))
        else:
            ctx.logger.error("No pending payment request found after handshake.")
    
    else:
        ctx.logger.error("Handshake with Alice failed, aborting payment process.")
        return  # Do nothing if handshake fails

@bob.on_message(model=PaymentAgreement)
async def process_payment(ctx: Context, sender: str, msg: PaymentAgreement):
    """
    Process payment based on the agreement with Alice.
    """
    if not msg.agreed:
        ctx.logger.info(f"Payment agreement with Alice failed. No payment will be processed.")
        return
    
    try:
        # Retrieve the original payment request from storage to access wallet_address
        pending_request_serialized = ctx.storage.get("pending_payment_request")
        if not pending_request_serialized:
            ctx.logger.error("No pending payment request found for processing.")
            return
        pending_request = PaymentRequest(**pending_request_serialized)

        # Check Bob's balance before sending payment
        available_balance = ctx.ledger.query_bank_balance(bob.wallet.address(), msg.denom)
        if available_balance < msg.final_amount:
            ctx.logger.error("Insufficient balance for the agreed payment.")
            return

        # Send the payment to Alice's wallet address from the original payment request
        transaction = ctx.ledger.send_tokens(
            pending_request.wallet_address, msg.final_amount, msg.denom, bob.wallet
        )
        
        # Prevent transaction reuse (manually handle 'used_tx_hashes' presence in storage)
        if ctx.storage.has("used_tx_hashes"):
            used_transactions = set(ctx.storage.get("used_tx_hashes"))
        else:
            used_transactions = set()

        if transaction.tx_hash in used_transactions:
            ctx.logger.error(f"Transaction {transaction.tx_hash} already processed!")
            return
        
        # Send transaction info to Alice
        await ctx.send(sender, TransactionInfo(tx_hash=transaction.tx_hash))
        
        # Update the used transactions and store the list
        used_transactions.add(transaction.tx_hash)
        ctx.storage.set("used_tx_hashes", list(used_transactions))  # Convert the set to a list before storing

        ctx.logger.info(f"Transaction {transaction.tx_hash} sent to Alice.")

    except Exception as e:
        ctx.logger.error(f"Error while processing payment: {e}")

@bob.on_message(model=PaymentConfirmation)
async def handle_payment_confirmation(ctx: Context, sender: str, msg: PaymentConfirmation):
    """
    Handle payment confirmation received from Alice.
    """
    ctx.logger.info(f"Received payment confirmation from Alice: {msg.confirmation_message}")

if __name__ == "__main__":
    bob.run()
