import asyncio
import datetime
import ssl

import aiohttp
import eth_account
from mnemonic import Mnemonic
from termcolor import colored


eth_account.Account.enable_unaudited_hdwallet_features()

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

semaphore = asyncio.Semaphore(5)


def logger(message, type='info'):
    timestamp = datetime.datetime.now().strftime('%H:%M:%S')
    if type == 'info':
        print(f"[{timestamp}] {message}")
    elif type == 'success':
        print(colored(f"[{timestamp}] {message}", 'green'))
    elif type == 'error':
        print(colored(f"[{timestamp}] {message}", 'red'))
    elif type == 'warning':
        print(colored(f"[{timestamp}] {message}", 'yellow'))


def generate_seed_phrase():
    length = 12
    mnemo = Mnemonic('english')
    return mnemo.generate(strength=(length // 3) * 32)


async def scrape_blockscan(session, address):
    url = f'https://eth.tokenview.io/api/search/{address}'

    try:
        async with semaphore:
            async with session.get(url, ssl=ssl_context) as response:
                if response.status == 200:
                    wallet_info = await response.json()
                    wallet_code = wallet_info.get('code')
                    if wallet_code == 1:
                        currencies = wallet_info.get('data')
                        balances = []
                        for currency in currencies:
                            balances.append({currency.get('network'): currency.get('balance')})
                        return balances
                    else:
                        return '$0.00'
                else:
                    logger(f"API error: {response.status}", 'error')
                    return '$0.00'
    except Exception as ex:
        logger(f"Exception occurred: {ex}", 'error')
        return '$0.00'


async def check_wallets(session):
    while True:
        try:
            seed_phrase = generate_seed_phrase()
            account = eth_account.Account.from_mnemonic(seed_phrase)

            logger(f"👾 Address: {account.address}", 'info')
            logger(f"💬 Mnemonic: {seed_phrase}", 'info')
            logger(f"🔑 Private key: {account.key.hex()}", 'info')

            balances = await scrape_blockscan(session, account.address)

            logger(f"🤑 Balance: {balances}", 'info')
            if balances != '$0.00':
                logger("🎉 Found a wallet with a non-zero balance!", 'success')
                with open('wallets_eth.txt', 'a') as file:
                    file.write(f"👾 Address: {account.address}\n💬 Mnemonic: {seed_phrase}\n🔑 "
                               f"Private key: {account.key.hex()}\n🤑 Balances: {balances}\n🤑\n\n")
            else:
                logger("👎 No luck this time.", 'warning')

        except Exception as e:
            logger(f"An error occurred: {e}", 'error')


async def run_bruteforce():
    async with aiohttp.ClientSession() as session:
        tasks = [check_wallets(session) for _ in range(5)]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(run_bruteforce())
