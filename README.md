# PLAZA FINANCE BOT 使用默认认为知晓女巫风险 女巫风险自负！
Plaza是一个在Base上提供链上债券和杠杆的平台。

Plaza是一个在Base上构建的Solidity智能合约集，用于创建可编程衍生品。它提供两种核心产品：bondETH和levETH，这些是基于ETH流动性质押衍生品（LSTs）和流动性再质押衍生品（LRTs）如wstETH的可编程衍生品。用户可以存入基础池资产如wstETH，并接收levETH或bondETH，这些以ERC20代币形式体现。这些代币可以与DEX、借贷市场、再质押平台等协议进行组合。

![banner](image/image.png)

- 网站 [https://testnet.plaza.finance/](https://testnet.plaza.finance/rewards/0WkJP1uDWPis)
- 推特 [@plaza_finance](https://x.com/plaza_finance)


## 特性

- **每日自动交易**
- **自动获取水龙头**
- **支持使用代理**
- **钱包之间随机时间**
- **循环之间随机时间**

## 要求

- **Python**: 请确保已安装 Python 环境。
- **钱包必须在eth/base/arb主网上有$1以获取水龙头**

## 设置
**首先把私钥填入private_keys.txt，不带0x前缀！**
**支持代理，填入proxy.txt，注意要和私钥数量一致，可以选择不用代理运行**

1. 克隆此仓库：
   ```bash
   git clone https://github.com/Gzgod/plazabot.git
   cd plazabot
   ```
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 运行脚本
   ```bash
   python main.py
   ```

