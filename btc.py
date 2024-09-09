import asyncio
import datetime
import ssl
import uuid

import aiohttp
from bitcoinlib.wallets import Wallet, wallet_delete
from bitcoinlib.mnemonic import Mnemonic
from termcolor import colored


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
    mnemo = Mnemonic('english')
    return mnemo.generate()


async def scrape_blockchain_info(session, address):
    url = f'https://btc.tokenview.io/api/search/{address}'

    try:
        async with semaphore:
            async with session.get(url, ssl=ssl_context) as response:
                if response.status == 200:
                    wallet_info = await response.json()
                    wallet_code = wallet_info.get('code')
                    if wallet_code == 1:
                        wallet_data = wallet_info.get('data')[0]
                        if float(wallet_data.get('spend')) == 0 and float(wallet_data.get('receive')) > 0:
                            balance = wallet_data.get('receive')
                        else:
                            balance = '0.00'
                        return balance
                    else:
                        return '0.00'
                else:
                    logger(f"API error: {response.status}", 'error')
                    return '0.00'
    except Exception as ex:
        logger(f"Exception occurred: {ex}", 'error')
        return '0.00'


async def check_wallets(session):
    while True:
        try:
            seed_phrase = generate_seed_phrase()
            wallet_name = f'temp_wallet_{uuid.uuid4()}'
            wallet = Wallet.create(name=wallet_name, keys=seed_phrase, network='bitcoin')
            address = wallet.get_key().address
            private_key = wallet.get_key().key_private.hex()

            logger(f"👾 Address: {address}", 'info')
            logger(f"💬 Mnemonic: {seed_phrase}", 'info')
            logger(f"🔑 Private key: {private_key}", 'info')

            balance = await scrape_blockchain_info(session, address)

            logger(f"🤑 BTC Balance: {balance}", 'info')

            if float(balance) > 0.0:
                logger("🎉 Found a wallet with a non-zero balance!", 'success')
                with open('wallets_btc.txt', 'a') as file:
                    file.write(f"👾 Address: {address}\n💬 Mnemonic: {seed_phrase}\n🔑 Private key: "
                               f"{private_key}\n🤑 BTC Balance: {balance}\n\n")
            else:
                logger("👎 No luck this time.", 'warning')
            wallet_delete(wallet_name)

        except Exception as e:
            logger(f"An error occurred: {e}", 'error')


async def run_bruteforce():
    async with aiohttp.ClientSession() as session:
        tasks = [check_wallets(session) for _ in range(5)]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(run_bruteforce())
