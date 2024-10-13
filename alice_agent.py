import os
import hashlib
import asyncio
from uagents import Agent, Context
from uagents.setup import fund_agent_if_low
from uagents.network import wait_for_tx_to_complete
from common import PaymentRequest, TransactionInfo, PaymentConfirmation, PaymentNegotiation, PaymentAgreement, HandshakeRequest

AMOUNT = 100
DENOM = "atestfet"

# Initialize Alice's agent
PORT = 8000
alice = Agent(name="alice", seed="alice secret phrase", port=PORT, endpoint=f"http://localhost:{PORT}/submit")

# Ensure Alice has enough balance for any fees
fund_agent_if_low(alice.wallet.address(), min_balance=AMOUNT)

# Helper function to create the digest of a message
def encode(message: str) -> bytes:
    hasher = hashlib.sha256()
    hasher.update(message.encode())
    return hasher.digest()

# @alice.on_event("startup")
# async def introduce(ctx: Context):
#     ctx.logger.info(f"Agent started with address: {ctx.agent.address}")

# @alice.on_interval(period=10.0)
@alice.on_event("startup")
async def request_payment(ctx: Context):
    """
    Alice periodically requests payment from Bob.
    """
    try:
        # Create the digest to be signed
        digest = encode(f"{alice.wallet.address()}{AMOUNT}{DENOM}")

        # Sign the digest with Alice's private key
        signature = alice.sign_digest(digest)

        # Create the payment request with the signature
        payment_request = PaymentRequest(
            wallet_address=str(alice.wallet.address()),
            amount=AMOUNT,
            denom=DENOM,
            signature=signature
        )
        ctx.logger.info(f"Requesting payment from Bob: {payment_request}")
        
        # Send the payment request to Bob
        await ctx.send(os.getenv("BOB_AGENT_ADDRESS", "agent1q2kxet3vh0scsf0sm7y2erzz33cve6tv5uk63x64upw5g68kr0chkv7hw50"), payment_request)
    except Exception as e:
        ctx.logger.error(f"Error while requesting payment: {e}")

@alice.on_message(model=HandshakeRequest)
async def confirm_handshake(ctx: Context, sender: str, msg: HandshakeRequest):
    """
    Confirms Bob's handshake request and proceeds to negotiation.
    """
    if msg.confirmation:
        ctx.logger.info("Handshake request from Bob received, confirming handshake.")
        await ctx.send(sender, HandshakeRequest(confirmation=True))
    else:
        ctx.logger.error("Handshake request from Bob failed.")

@alice.on_message(model=PaymentNegotiation)
async def handle_negotiation(ctx: Context, sender: str, msg: PaymentNegotiation):
    """
    Handle negotiation from Bob by either accepting or rejecting the offer.
    """
    if msg.offered_amount >= msg.requested_amount // 2:  # Accept offers >= 50%
        ctx.logger.info(f"Accepted payment offer from Bob: {msg.offered_amount}{msg.denom}")
        await ctx.send(sender, PaymentAgreement(agreed=True, final_amount=msg.offered_amount, denom=msg.denom))
    else:
        ctx.logger.info(f"Rejected offer from Bob: {msg.offered_amount}{msg.denom}")
        await ctx.send(sender, PaymentAgreement(agreed=False, final_amount=0, denom=msg.denom))

@alice.on_message(model=TransactionInfo)
async def verify_transaction(ctx: Context, sender: str, msg: TransactionInfo):
    """
    Alice receives transaction info from Bob and verifies it on the ledger.
    """
    try:
        ctx.logger.info(f"Received transaction info from Bob: {msg.tx_hash}")

        # Check if the transaction has already been verified (using agent storage)
        if ctx.storage.has("used_tx_hashes"):
            used_transactions = set(ctx.storage.get("used_tx_hashes"))
        else:
            used_transactions = set()

        if msg.tx_hash in used_transactions:
            ctx.logger.error(f"Transaction {msg.tx_hash} already used!")
            return

        # Verify transaction with a timeout
        timeout = 30  # seconds
        tx_resp = await asyncio.wait_for(wait_for_tx_to_complete(msg.tx_hash, ctx.ledger), timeout=timeout)
        coin_received = tx_resp.events["coin_received"]

        # Verify that Alice is the recipient and the correct amount was received
        if (
            coin_received["receiver"] == str(alice.wallet.address())
            and coin_received["amount"] == f"{AMOUNT}{DENOM}"
        ):
            ctx.logger.info(f"Transaction {msg.tx_hash} was successful!")

            # Store the transaction hash to prevent double-spending
            used_transactions.add(msg.tx_hash)
            ctx.storage.set("used_tx_hashes", list(used_transactions))  # Convert the set to a list before storing

            # Send a confirmation to Bob using the PaymentConfirmation model
            confirmation_message = f"Payment of {AMOUNT}{DENOM} verified successfully."
            await ctx.send(sender, PaymentConfirmation(confirmation_message=confirmation_message))
        else:
            ctx.logger.error(f"Transaction verification failed for {msg.tx_hash}")

    except asyncio.TimeoutError:
        ctx.logger.error(f"Transaction {msg.tx_hash} verification timed out.")
    
    except Exception as e:
        ctx.logger.error(f"Error while verifying transaction: {e}")

if __name__ == "__main__":
    alice.run()