import sys
import time
import os
from brownie import *

# User variables. Change these to match your wallet's public address and explorer API key
WEB3_INFURA_PROJECT_ID = "84c1242375b843589f6befc4a823dd44"

# Contract addresses
TOKEN_1_CONTRACT_ADDRESS = "0x090185f2135308bad17527004364ebcc2d37e5f6"  # SPELL
TOKEN_2_CONTRACT_ADDRESS = "0x26FA3fFFB6EfE8c1E69103aCb4044C26B9A106a9"  # sSPELL

os.environ["WEB3_INFURA_PROJECT_ID"] = WEB3_INFURA_PROJECT_ID

FILENAME = ".abra_rate"


def main():

    try:
        network.connect("mainnet")
    except:
        sys.exit(
            "Could not connect to Ethereum! Verify that brownie lists the Ethereum (Infura) Mainnet using 'brownie networks list'"
        )

    print("\nContracts loaded:")
    spell_contract = contract_load(TOKEN_1_CONTRACT_ADDRESS, "Token: SPELL")
    sspell_contract = contract_load(TOKEN_2_CONTRACT_ADDRESS, "Token: sSPELL")

    try:
        with open(FILENAME, "r") as file:
            abra_rate = float(file.read().strip())
            print(f"Last known rate: {abra_rate}")
    except Exception as e:
        print(f"{e}")

    while True:

        with open(FILENAME, "r") as file:
            abra_rate = float(file.read().strip())

        try:
            result = round(
                spell_contract.balanceOf(sspell_contract.address)
                / sspell_contract.totalSupply(),
                4,
            )
        except Exception as e:
            print(f"{e}")
            continue

        if abra_rate and result == abra_rate:
            print("Rate same")
        else:
            print(f"Updated rate found: {result}")
            abra_rate = result
            with open(FILENAME, "w") as file:
                file.write(str(abra_rate) + "\n")

        

        time.sleep(60)


def contract_load(address, alias):
    # Attempts to load the saved contract.
    # If not found, fetch from network explorer and save.
    try:
        contract = Contract(alias)
    except ValueError:
        contract = Contract.from_explorer(address)
        contract.set_alias(alias)
    finally:
        print(f"• {alias}")
        return contract


# Only executes main loop if this file is called directly
if __name__ == "__main__":
    main()