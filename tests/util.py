"""Testing utilities."""

from typing import Tuple

from starkware.cairo.common.hash_state import compute_hash_on_elements
from starkware.crypto.signature.signature import private_to_stark_key, sign
from starkware.starknet.public.abi import get_selector_from_name


TRANSACTION_VERSION = 0


def str_to_felt(text: str) -> int:
    """Convert python string into equivalent Cairo short string value."""
    b_text = bytes(text, "UTF-8")
    return int.from_bytes(b_text, "big")


def uint(a: int) -> Tuple[int, int]:
    """Construct new uint tuple from a small number."""
    return (a, 0)


class Signer:
    """
    Utility for sending signed transactions to an Account on Starknet.
    Parameters
    ----------
    private_key : int
    Examples
    ---------
    Constructing a Singer object
    >>> signer = Signer(1234)
    Sending a transaction
    >>> await signer.send_transaction(account,
                                      account.contract_address,
                                      'set_public_key',
                                      [other.public_key]
                                     )
    """

    def __init__(self, private_key):
        self.private_key = private_key
        self.public_key = private_to_stark_key(private_key)

    def sign(self, message_hash):
        return sign(msg_hash=message_hash, priv_key=self.private_key)

    async def send_transaction(
        self, account, to, selector_name, calldata, nonce=None, max_fee=0
    ):
        if nonce is None:
            execution_info = await account.get_nonce().call()
            (nonce,) = execution_info.result

        calls = [(to, selector_name, calldata)]
        calls_with_selector = [(to, get_selector_from_name(selector_name), calldata)]
        (call_array, calldata) = from_call_to_call_array(calls)

        message_hash = hash_multicall(
            account.contract_address, calls_with_selector, nonce, max_fee
        )
        sig_r, sig_s = self.sign(message_hash)

        return await account.__execute__(call_array, calldata, nonce).invoke(
            signature=[sig_r, sig_s]
        )


def from_call_to_call_array(calls):
    call_array = []
    calldata = []
    for i, call in enumerate(calls):
        assert len(call) == 3, "Invalid call parameters"
        entry = (call[0], get_selector_from_name(call[1]), len(calldata), len(call[2]))
        call_array.append(entry)
        calldata.extend(call[2])
    return (call_array, calldata)


def hash_multicall(sender, calls, nonce, max_fee):
    hash_array = []
    for call in calls:
        call_elements = [call[0], call[1], compute_hash_on_elements(call[2])]
        hash_array.append(compute_hash_on_elements(call_elements))

    message = [
        str_to_felt("StarkNet Transaction"),
        sender,
        compute_hash_on_elements(hash_array),
        nonce,
        max_fee,
        TRANSACTION_VERSION,
    ]
    return compute_hash_on_elements(message)
