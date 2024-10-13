from uagents import Model

# Payment-related models
class PaymentRequest(Model):
    wallet_address: str
    amount: int
    denom: str
    signature: str  # Add signature field to the PaymentRequest model

class TransactionInfo(Model):
    tx_hash: str

class PaymentConfirmation(Model):
    confirmation_message: str

# Negotiation models
class PaymentNegotiation(Model):
    requested_amount: int
    offered_amount: int
    denom: str

class PaymentAgreement(Model):
    agreed: bool
    final_amount: int
    denom: str

# Handshake protocol model
class HandshakeRequest(Model):
    confirmation: bool
