import sys
import time
import datetime
import requests
import os
from brownie import *
from pynput.keyboard import Key, Controller
from twilio.rest import Client
client = Client("ACd58c2ff9e3c0739d8b41aa2021027b23", "24fa93d06bfeaedda72b099eac0706b7")

# Contract addresses (verify on Snowtrace)
TRADERJOE_ROUTER_CONTRACT_ADDRESS = "0x60aE616a2155Ee3d9A68541Ba4544862310933d4"
SPELL_CONTRACT_ADDRESS = "0xce1bffbd5374dac86a2893119683f4911a2f7814"
SSPELL_CONTRACT_ADDRESS = "0x3ee97d514bbef95a2f110e6b9b73824719030f7a" 

# API key from Snowtrace
SNOWTRACE_API_KEY = "XDH98VUEGSRKE3PF3SNXZJVY226HEYSIQK"
os.environ["SNOWTRACE_TOKEN"] = SNOWTRACE_API_KEY

# Create helper values
SECOND = 1
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
DAY = 24 * HOUR
PERCENT = 0.01

# [BOT OPTIONS]
# Simulate swaps and approvals
DRY_RUN = False

# Quit after the first successful trade
ONE_SHOT = False

# How often to run the main loop (in seconds)
LOOP_TIME = 1.0

# [SWAP THRESHOLDS AND SLIPPAGE]
# SPELL -> sSPELL swap targets
# a zero value will trigger a swap when the ratio matches base_staking_rate exactly
# a negative value will trigger a swap when the rate is below base_staking_rate
# a positive value will trigger a swap when the rate is above base_staking_rate
THRESHOLD_SPELL_TO_SSPELL = 0.15 * PERCENT

# sSPELL -> SPELL swap targets
# a positive value will trigger a (sSPELL -> SPELL) swap when the ratio is above base_staking_rate
THRESHOLD_SSPELL_TO_SPELL = 0.15 * PERCENT

# tolerated slippage in swap price (used to calculate amountOutMin)
SLIPPAGE = 0.1 * PERCENT


# [FUNCTION DEFINITIONS]
def account_get_balance(account):
    try:
        return account.balance()
    except Exception as e:
        print(f"Exception in account_get_balance: {e}")


def contract_load(address, alias):
    # Attempts to load the saved contract by alias.
    # If not found, fetch from network explorer and set alias.
    try:
        contract = Contract(alias)
    except ValueError:
        contract = Contract.from_explorer(address)
        contract.set_alias(alias)
    finally:
        print(f"• {alias}")
        return contract


def get_approval(token, router, user):
    try:
        return token.allowance.call(user, router.address)
    except Exception as e:
        print(f"Exception in get_approval: {e}")
        return False


def get_token_name(token):
    try:
        return token.name.call()
    except Exception as e:
        print(f"Exception in get_token_name: {e}")
        raise


def get_token_symbol(token):
    try:
        return token.symbol.call()
    except Exception as e:
        print(f"Exception in get_token_symbol: {e}")
        raise


def get_token_balance(token, user):
    try:
        return token.balanceOf.call(user)
    except Exception as e:
        print(f"Exception in get_token_balance: {e}")
        raise


def get_token_decimals(token):
    try:
        return token.decimals.call()
    except Exception as e:
        print(f"Exception in get_token_decimals: {e}")
        raise


def token_approve(token, router, value="unlimited"):
    if DRY_RUN:
        return True

    if value == "unlimited":
        try:
            token.approve(
                router,
                2 ** 256 - 1,
                {"from": user},
            )
            return True
        except Exception as e:
            print(f"Exception in approve_swap: {e}")
            raise
    else:
        try:
            token.approve(
                router,
                value,
                {"from": user},
            )
            return True
        except Exception as e:
            print(f"Exception in approve_swap: {e}")
            raise


def get_swap_rate(token_in_quantity, token_in_address, token_out_address, router):
    try:
        return router.getAmountsOut(
            token_in_quantity, [token_in_address, token_out_address]
        )
    except Exception as e:
        print(f"Exception in get_swap_rate: {e}")
        return False


def token_swap(
    token_in_quantity,
    token_in_address,
    token_out_quantity,
    token_out_address,
    router,
):
    if DRY_RUN:
        return True

    try:
        router.swapExactTokensForTokens(
            token_in_quantity,
            int(token_out_quantity * (1 - SLIPPAGE)),
            [token_in_address, token_out_address],
            user.address,
            int(1000 * (time.time()) + 30 * SECOND),
            {"from": user},
        )
        return True
    except Exception as e:
        print(f"Exception: {e}")
        return False

# SETUP BLOCK
# Connect to the network
network.connect('avax-main')
network.priority_fee('5 gwei')
network.max_fee('200 gwei')


# Load the user account
keyboard = Controller()
keyboard.press(Key.enter)
keyboard.release(Key.enter)
user = accounts.load('megacap')

print("Loading Contracts:")
# Load the router contract
router_contract = contract_load(TRADERJOE_ROUTER_CONTRACT_ADDRESS, "TraderJoe AVAX Router")

# Load the token contracts
spell_contract = contract_load(SPELL_CONTRACT_ADDRESS, "Token: SPELL")
sspell_contract = contract_load(SSPELL_CONTRACT_ADDRESS, "Token: sSPELL")

# MAIN PROGRAM
# Get allowance and set approvals as needed
if get_approval(spell_contract, router_contract, user):
    print("SPELL OK")
else:
    token_approve(spell_contract, router_contract, value="unlimited")

if get_approval(sspell_contract, router_contract, user):
    print("sSPELL OK")
else:
    token_approve(sspell_contract, router_contract, value="unlimited")

try:
     with open(".abra_rate", "r") as file:
            abra_rate = float(file.read().strip())
            print(f"Last known rate: {abra_rate}")
except Exception as e:
        print(f"{e}")

print(f"SPELL Balance: {get_token_balance(spell_contract, user) / (10 ** get_token_decimals(spell_contract))}")
print(f"sSPELL Balance: {get_token_balance(sspell_contract, user) / (10 ** get_token_decimals(sspell_contract))}")
# Set up loop

balance_refresh = True

while True:
    if balance_refresh:
        time.sleep(10)
        spell_balance = get_token_balance(spell_contract, user)
        sspell_balance = get_token_balance(sspell_contract, user)
        print("\nAccount Balance:")
        print(
            f"• Token #1: {int(spell_balance/(10**get_token_decimals(spell_contract)))} {spell_contract.symbol()}"
        )
        print(
            f"• Token #2: {int(sspell_balance/(10**get_token_decimals(sspell_contract)))} {sspell_contract.symbol()}"
        )
        print()
        balance_refresh = False
        last_ratio_spell_to_sspell = 0
        last_ratio_sspell_to_spell = 0

    # If we have SPELL, then we need to figure out the SPELL -> sSPELL ratio
    if get_token_balance(spell_contract, user) != 0:

        # Open and read text file with ETH abra rate for SPELL -> sSPELL
        with open(".abra_rate", "r") as file:
            abra_rate = float(file.read().strip())

        # Fetch, and store swap results
        if qty_out := get_swap_rate(
            token_in_quantity=get_token_balance(spell_contract, user), 
            token_in_address=spell_contract.address, 
            token_out_address=sspell_contract.address, 
            router=router_contract,
            ):
            
            spell_in, sspell_out = qty_out
            ratio_spell_to_sspell = round(sspell_out / spell_in, 4)

            if ratio_spell_to_sspell != last_ratio_spell_to_sspell:
                print(
                f"{datetime.datetime.now().strftime('[%I:%M:%S %p]')} {get_token_symbol(spell_contract)} → {get_token_symbol(sspell_contract)}: ({ratio_spell_to_sspell:.4f}/{1 / (abra_rate * (1 + THRESHOLD_SPELL_TO_SSPELL)):.4f})"
            )
            last_ratio_spell_to_sspell = ratio_spell_to_sspell
        else:
            break

        with open(".sspellout", "r") as file:
            last_sspell_out = float(file.read().strip())

        if ratio_spell_to_sspell >= 1 / (abra_rate * (1 + THRESHOLD_SPELL_TO_SSPELL)) and sspell_out > last_sspell_out:
            print("*** EXECUTING SWAP ***")
            if token_swap(
                token_in_quantity=spell_in,
                token_in_address=spell_contract.address, 
                token_out_quantity=sspell_out, 
                token_out_address=sspell_contract.address, 
                router=router_contract
                ):
                balance_refresh = True
                with open(".sspellout", "w") as file:
                    file.write(str(sspell_out) + "\n")
                

                with open(".swaps_executed", "a") as file:

                    # Write info regarding swap into a text file
                    file.write(
                    f"{datetime.datetime.now().strftime('[%I:%M:%S %p]')} {spell_contract.symbol()} -> {sspell_contract.symbol()}: ({ratio_spell_to_sspell:.3f})"
                    f" ETH Rate: ({abra_rate: .3f})"
                    f" Amount In: {int(spell_in / (10**get_token_decimals(spell_contract)))}%"
                    f" Amount Out: {int(sspell_out / (10**get_token_decimals(sspell_contract)))}%"
                    + "\n"
                    )

                # Send a notification to yourself and clients
                numbers_to_message = ["+16198629563"]
                for number in numbers_to_message:
                    client.messages.create(to=number, from_="+13165319116",
                    body="Your bot just executed a trade. See details below:"
                    + "\n" + "\n"
                    f"{datetime.datetime.now().strftime('[%I:%M:%S %p]')} {spell_contract.symbol()} → {sspell_contract.symbol()}:" + "\n" f"AVAX Rate: ({ratio_spell_to_sspell:.3f})"
                    + "\n" f"Amount In: {int(spell_in / (10**get_token_decimals(spell_contract)))} SPELL"
                    + "\n" f"Amount Out: {int(sspell_out / (10**get_token_decimals(sspell_contract)))} sSPELL"
                    )

    # If we don't have SPELL, then we have sSPELL, and need to figure out the
    # sSPELL -> SPELL ratio
    if get_token_balance(sspell_contract, user) != 0:
        # Open and read text file with ETH abra rate for sSPELL -> SPELL
        with open(".abra_rate", "r") as file:
            abra_rate = float(file.read().strip())

        if qty_out := get_swap_rate(
            token_in_quantity=get_token_balance(sspell_contract, user), 
            token_in_address=sspell_contract.address, 
            token_out_address=spell_contract.address, 
            router=router_contract,
            ):

            sspell_in, spell_out = qty_out
            ratio_sspell_to_spell = round(spell_out / sspell_in, 4)

            if ratio_sspell_to_spell != last_ratio_sspell_to_spell:
                print(
                        f"{datetime.datetime.now().strftime('[%I:%M:%S %p]')} {sspell_contract.symbol()} → {spell_contract.symbol()}: ({ratio_sspell_to_spell:.4f}/{abra_rate * (1 + THRESHOLD_SSPELL_TO_SPELL):.4f})"
                    )

                last_ratio_sspell_to_spell = ratio_sspell_to_spell

        else:
            break

        with open(".spellout", "r") as file:
            last_spell_out = float(file.read().strip())

        if ratio_sspell_to_spell >= abra_rate * (1 + THRESHOLD_SSPELL_TO_SPELL) and spell_out >= last_spell_out:
            print("*** EXECUTING SWAP ***")
            if token_swap(
                token_in_quantity=sspell_in, 
                token_in_address=sspell_contract.address, 
                token_out_quantity=spell_out, 
                token_out_address=spell_contract.address, 
                router=router_contract
                ):
                balance_refresh = True
                with open(".spellout", "w") as file:
                    file.write(str(spell_out) + "\n")

                # Write info regarding swap into a text file
                with open(".swaps_executed", "a") as file:
                    file.write(
                        f"{datetime.datetime.now().strftime('[%I:%M:%S %p]')} {spell_contract.symbol()} -> {spell_contract.symbol()}: ({ratio_sspell_to_spell:.3f})"
                        f" Amount In: {int(sspell_in / (10**get_token_decimals(sspell_contract)))} sSPELL"
                        f" Amount Out: {int(spell_out / (10**get_token_decimals(spell_contract)))}SPELL"
                        + "\n")

                # Send a message to yourself and clients
                numbers_to_message = ["+16198629563"]
                for number in numbers_to_message:
                    client.messages.create(to=number, from_="+13165319116",
                    body="Your bot just executed a trade. See details below:"
                    + "\n" + "\n"
                    f"{datetime.datetime.now().strftime('[%I:%M:%S %p]')} {sspell_contract.symbol()} → {spell_contract.symbol()}:" + "\n" f"AVAX Rate: ({ratio_sspell_to_spell:.3f})"
                    + "\n" f"Amount In: {int(sspell_in / (10**get_token_decimals(sspell_contract)))} sSPELL"
                    + "\n" f"Amount Out: {int(spell_out / (10**get_token_decimals(spell_contract)))} SPELL"
                    )
        
        time.sleep(LOOP_TIME)
            
