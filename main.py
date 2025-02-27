import asyncio
import time
import random
from web3 import Web3
import requests
from colorama import init, Fore, Style
import os
from eth_account import Account
from datetime import datetime, timedelta
from web3.providers.rpc import HTTPProvider
import pytz  # 引入 pytz 库处理时区

# 初始化 colorama 以支持彩色输出
init()

# 设置 UTC+8 时区
UTC8 = pytz.timezone('Asia/Shanghai')

# 全局变量，用于保存是否使用代理的选择
USE_PROXY = None

# 读取代理文件
def read_proxies():
    try:
        with open('proxy.txt', 'r') as f:
            proxies = [proxy.strip() for proxy in f.readlines() if proxy.strip()]
        return proxies
    except Exception as e:
        print(f"{Fore.RED}读取 proxy.txt 时出错: {str(e)}{Style.RESET_ALL}")
        os._exit(1)

# Web3 配置函数，支持代理
def create_web3_with_proxy(proxy=None):
    if proxy:
        return Web3(HTTPProvider('https://sepolia.base.org', request_kwargs={'proxies': {'http': proxy, 'https': proxy}}))
    return Web3(HTTPProvider('https://sepolia.base.org'))

# 使用校验和地址
wstETHAddress = Web3.to_checksum_address('0x13e5fb0b6534bb22cbc59fae339dbbe0dc906871')
contractAddress = Web3.to_checksum_address('0xF39635F2adF40608255779ff742Afe13dE31f577')

erc20Abi = [
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"name": "remaining", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "success", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    }
]

contractAbi = [
    {
        "inputs": [
            {"internalType": "uint8", "name": "tokenType", "type": "uint8"},
            {"internalType": "uint256", "name": "depositAmount", "type": "uint256"},
            {"internalType": "uint256", "name": "minAmount", "type": "uint256"}
        ],
        "name": "create",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint8", "name": "tokenType", "type": "uint8"},
            {"internalType": "uint256", "name": "depositAmount", "type": "uint256"},
            {"internalType": "uint256", "name": "minAmount", "type": "uint256"}
        ],
        "name": "redeem",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

# 确保 wstETH 的无限授权
async def ensure_unlimited_spending(web3, private_key, spender_address):
    account = Account.from_key(private_key)
    owner_address = account.address
    wstETH_contract = web3.eth.contract(address=wstETHAddress, abi=erc20Abi)

    try:
        allowance = wstETH_contract.functions.allowance(owner_address, spender_address).call()
        max_uint = int('0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff', 16)

        if allowance < max_uint:
            print(f"{Fore.RED}wstETH 的授权额度不是无限的，正在设置为无限...{Style.RESET_ALL}")
            approve_method = wstETH_contract.functions.approve(spender_address, max_uint)
            gas_estimate = approve_method.estimate_gas({'from': owner_address})
            nonce = web3.eth.get_transaction_count(owner_address)

            tx = approve_method.build_transaction({
                'from': owner_address,
                'gas': gas_estimate,
                'nonce': nonce
            })

            signed_tx = web3.eth.account.sign_transaction(tx, private_key)
            tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

            print(f"{Fore.BLUE}已为 wstETH 设置无限授权额度，交易哈希: {receipt.transactionHash.hex()}{Style.RESET_ALL}")
        else:
            print(f"{Fore.BLUE}wstETH 的授权额度已是无限的{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}设置 wstETH 无限授权额度时出错: {str(e)}{Style.RESET_ALL}")

# 申请水龙头，使用代理（可选）
async def claim_faucet(address, proxy=None):
    try:
        proxies = {'http': proxy, 'https': proxy} if proxy else None
        response = requests.post(
            'https://api.plaza.finance/faucet/queue',
            json={"address": address},
            headers={
                'User-Agent': 'Mozilla/5.0',
                'Content-Type': 'application/json',
                'x-plaza-api-key': 'bfc7b70e-66ad-4524-9bb6-733716c4da94'
            },
            proxies=proxies,
            timeout=10  # 添加超时
        )
        response.raise_for_status()
        print(f"{Fore.BLUE}已成功为 {address} 申请水龙头{'（使用代理: ' + proxy + '）' if proxy else ''}{Style.RESET_ALL}")
        print(f"{Fore.RED}申请响应: {response.json()}{Style.RESET_ALL}")
    except requests.exceptions.ProxyError as e:
        print(f"{Fore.RED}代理连接失败: {str(e)}{'（代理: ' + proxy + '），' if proxy else ''}跳过水龙头申请{Style.RESET_ALL}")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            print(f"{Fore.RED}水龙头每天只能使用一次{'（代理: ' + proxy + '）' if proxy else ''}{Style.RESET_ALL}")
        elif e.response.status_code == 403:
            print(f"{Fore.RED}403 禁止访问：可能已达到速率限制或被阻止{'（代理: ' + proxy + '）' if proxy else ''}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}申请水龙头时出错: {str(e)}{'（代理: ' + proxy + '）' if proxy else ''}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}申请水龙头时出错: {str(e)}{'（代理: ' + proxy + '）' if proxy else ''}{Style.RESET_ALL}")

# 获取随机存款金额
def get_random_deposit_amount():
    min_amount = 0.009
    max_amount = 0.01
    random_eth_amount = random.uniform(min_amount, max_amount)
    return Web3.to_wei(random_eth_amount, 'ether')

# 获取代币合约地址
def get_token_contract_address(token_type):
    if token_type == 0:  # bondETH
        return Web3.to_checksum_address("0x5Bd36745f6199CF32d2465Ef1F8D6c51dCA9BdEE")
    elif token_type == 1:  # levETH
        return Web3.to_checksum_address("0x98f665D98a046fB81147879eCBE9A6fF68BC276C")

# 获取代币余额的 50%
async def get_fifty_percent_balance(web3, token_type, user_address):
    token_address = get_token_contract_address(token_type)
    token_contract = web3.eth.contract(address=token_address, abi=erc20Abi)
    balance = token_contract.functions.balanceOf(user_address).call()
    return balance // 2

# 执行创建或赎回操作
async def perform_action(web3, action, token_type, deposit_amount, min_amount, private_key):
    max_retries = 5
    retry_delay_in_seconds = 30
    attempt = 0
    account = Account.from_key(private_key)
    sender_address = account.address
    contract = web3.eth.contract(address=contractAddress, abi=contractAbi)

    while attempt < max_retries:
        try:
            if action == 'create':
                action_method = contract.functions.create(token_type, deposit_amount, min_amount)
            elif action == 'redeem':
                redeem_amount = await get_fifty_percent_balance(web3, token_type, sender_address)
                if redeem_amount == 0:
                    print(f"{Fore.RED}没有余额可以赎回{Style.RESET_ALL}")
                    return
                action_method = contract.functions.redeem(token_type, redeem_amount, min_amount)
            else:
                raise ValueError('无效的操作。请使用 "create" 或 "redeem"。')

            nonce = web3.eth.get_transaction_count(sender_address)
            gas_estimate = action_method.estimate_gas({'from': sender_address})
            tx = action_method.build_transaction({
                'from': sender_address,
                'gas': int(gas_estimate * 1.2),
                'nonce': nonce
            })

            signed_tx = web3.eth.account.sign_transaction(tx, private_key)
            tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"{Fore.BLUE}交易成功，哈希: {receipt.transactionHash.hex()}{Style.RESET_ALL}")
            return
        except Exception as e:
            attempt += 1
            print(f"{Fore.RED}执行 {action} 操作时，第 {attempt} 次尝试出错: {str(e)}{Style.RESET_ALL}")
            if attempt < max_retries:
                print(f"{Fore.RED}将在 {retry_delay_in_seconds} 秒后重试...{Style.RESET_ALL}")
                await asyncio.sleep(retry_delay_in_seconds)
            else:
                print(f"{Fore.RED}已达到最大重试次数，未能执行 {action} 操作{Style.RESET_ALL}")

# 从文件读取私钥
def read_private_keys():
    try:
        with open('private_keys.txt', 'r') as f:
            keys = [key.strip() for key in f.readlines() if key.strip()]
        cleaned_keys = []
        for i, key in enumerate(keys):
            if key.startswith('0x'):
                key = key[2:]
            if len(key) != 64:
                raise ValueError(f"第 {i + 1} 行的私钥长度为 {len(key)}，必须为32字节（64个字符）")
            try:
                bytes.fromhex(key)
            except ValueError:
                raise ValueError(f"第 {i + 1} 行的私钥包含无效的十六进制字符")
            cleaned_keys.append(key)
        return cleaned_keys
    except Exception as e:
        print(f"{Fore.RED}读取 private_keys.txt 时出错: {str(e)}{Style.RESET_ALL}")
        os._exit(1)

# 打印标题
def print_header():
    ascii_art = [
        "               ╔═╗╔═╦╗─╔╦═══╦═══╦═══╦═══╗",
        "               ╚╗╚╝╔╣║─║║╔══╣╔═╗║╔═╗║╔═╗║",
        "               ─╚╗╔╝║║─║║╚══╣║─╚╣║─║║║─║║",
        "               ─╔╝╚╗║║─║║╔══╣║╔═╣╚═╝║║─║║",
        "               ╔╝╔╗╚╣╚═╝║╚══╣╚╩═║╔═╗║╚═╝║",
        "               ╚═╝╚═╩═══╩═══╩═══╩╝─╚╩═══╝"
    ]
    info_lines = [
        "               关注tg频道：t.me/xuegaoz",
        "               我的gihub：github.com/Gzgod",
        "               我的推特：推特雪糕战神@Hy78516012"
    ]

    for line in ascii_art:
        print(f"{Fore.CYAN}{Style.BRIGHT}{line}{Style.RESET_ALL}")
    for line in info_lines:
        print(f"{Fore.BLUE}{line}{Style.RESET_ALL}")

# 询问是否使用代理
def ask_use_proxy():
    while True:
        response = input(f"{Fore.CYAN}是否使用代理？(y/n): {Style.RESET_ALL}").strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print(f"{Fore.RED}请输入 'y' 或 'n'{Style.RESET_ALL}")

# 处理钱包
async def process_wallets():
    global USE_PROXY  # 使用全局变量
    bond_token_type = 0
    leverage_token_type = 1
    min_amount = Web3.to_wei('0.00001', 'ether')

    print_header()
    # 仅在第一次运行时询问代理选择
    if USE_PROXY is None:
        USE_PROXY = ask_use_proxy()
    
    private_keys = read_private_keys()

    if USE_PROXY:
        proxies = read_proxies()
        if len(private_keys) != len(proxies):
            print(f"{Fore.RED}错误：private_keys.txt（{len(private_keys)}行）与 proxy.txt（{len(proxies)}行）的行数不匹配{Style.RESET_ALL}")
            os._exit(1)
    else:
        proxies = [None] * len(private_keys)  # 如果不使用代理，为每个私钥分配 None

    for i, (private_key, proxy) in enumerate(zip(private_keys, proxies)):
        web3_instance = create_web3_with_proxy(proxy)
        account = Account.from_key(private_key)
        wallet_address = account.address

        print(f"{Fore.RED}\n=== 开始处理钱包: {Fore.GREEN}{wallet_address}{Fore.RED}{' 使用代理: ' + proxy if proxy else ''} ==={Style.RESET_ALL}")

        print(f"{Fore.BLUE}正在为 {wallet_address} 申请水龙头...{Style.RESET_ALL}")
        await claim_faucet(wallet_address, proxy)

        await ensure_unlimited_spending(web3_instance, private_key, contractAddress)

        random_bond_amount = get_random_deposit_amount()
        print(f"{Fore.GREEN}使用金额 {Fore.RED}{Web3.from_wei(random_bond_amount, 'ether')} ETH 创建 Bond Token{Style.RESET_ALL}")
        await perform_action(web3_instance, 'create', bond_token_type, random_bond_amount, min_amount, private_key)

        random_leverage_amount = get_random_deposit_amount()
        print(f"{Fore.GREEN}使用金额 {Fore.RED}{Web3.from_wei(random_leverage_amount, 'ether')} ETH 创建 Leverage Token{Style.RESET_ALL}")
        await perform_action(web3_instance, 'create', leverage_token_type, random_leverage_amount, min_amount, private_key)

        print(f"{Fore.MAGENTA}正在赎回 Bond Token 余额的 50%...{Style.RESET_ALL}")
        await perform_action(web3_instance, 'redeem', bond_token_type, random_bond_amount, min_amount, private_key)

        print(f"{Fore.MAGENTA}正在赎回 Leverage Token 余额的 50%...{Style.RESET_ALL}")
        await perform_action(web3_instance, 'redeem', leverage_token_type, random_leverage_amount, min_amount, private_key)

        print(f"{Fore.RED}=== 已完成钱包处理: {Fore.GREEN}{wallet_address}{Fore.RED} ===\n{Style.RESET_ALL}")

        # 如果不是最后一个钱包，添加随机延迟
        if i < len(private_keys) - 1:
            delay = random.uniform(1, 15)  # 生成 1-15 秒的随机数
            print(f"{Fore.BLUE}在处理下一个钱包前，等待 {delay:.2f} 秒...{Style.RESET_ALL}")
            await asyncio.sleep(delay)

    print(f"{Fore.BLUE}=== 所有钱包已处理完成 ==={Style.RESET_ALL}")

# 获取下次运行时间，并返回随机 6-8 小时的延迟（使用 UTC+8）
def get_next_run_time():
    # 6-8 小时的随机毫秒数
    delay_in_hours = random.uniform(6, 8)
    delay_in_ms = int(delay_in_hours * 60 * 60 * 1000)
    # 使用 UTC 时间并转换为 UTC+8
    next_run_date = datetime.now(pytz.UTC).astimezone(UTC8) + timedelta(milliseconds=delay_in_ms)
    return next_run_date.strftime('%Y-%m-%d %H:%M:%S'), delay_in_ms

# 主运行函数
async def main():
    # 第一次运行
    await process_wallets()
    
    # 进入循环
    while True:
        next_run_time, delay_in_ms = get_next_run_time()
        print(f"{Fore.BLUE}第一次流程已完成。下次运行时间: {next_run_time} (UTC+8){Style.RESET_ALL}")
        await asyncio.sleep(delay_in_ms / 1000)  # 等待 6-8 小时
        print(f"{Fore.CYAN}{Style.BRIGHT}正在运行流程，时间: {datetime.now(UTC8).strftime('%Y-%m-%d %H:%M:%S')} (UTC+8){Style.RESET_ALL}")
        await process_wallets()

# 运行脚本
if __name__ == "__main__":
    asyncio.run(main())
