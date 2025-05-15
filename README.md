# 🎟️ SolMeet – Decentralized Event & Attendance Platform on Solana

SolMeet is a **Telegram-integrated Web3 platform** built on the **Solana blockchain** that allows organizers to **create events**, generate **QR-based participation claims**, and let attendees claim **on-chain proof of attendance** using auto-created or connected wallets.

> 🔗 Live WebApp: [sol-meet.vercel.app](https://sol-meet.vercel.app)

---

## 🚀 Features

- 💧 **Unlimited Faucet Support** – You’ll never run out of gas on Devnet!

- ✅ **On-Chain Event Creation** (via Anchor smart contract)
- ✅ **QR Code-Based Claiming** with Unique Event IDs
- ✅ **Telegram Bot Interface** for interaction & UX
- ✅ **Compressed Proofs ** (lightweight attendance tokens)
- ✅ **Real-Time Web Dashboard** for event tracking

---

## 📦 Tech Stack

| Layer        | Tech                        |
|-------------|-----------------------------|
| Smart Contract | 🦀 Rust + Anchor (Solana Devnet) |
| Web App     | ⚛️ Next.js + TailwindCSS     |
| Telegram Bot | 🤖 Python + python-telegram-bot |
| Wallets     | 🔐 Create Wallet (Mini App ready) |
| Claim UX    | 📱 QR Code + Telegram WebApp |

---

## 📌 Problem Statement

> Traditional event systems lack trust, decentralization, and on-chain verifiability.

- ❌ Attendance can be faked or manipulated
- ❌ No blockchain-backed verification of presence
- ❌ Complex onboarding for Web3 events
- ❌ No unified experience for organizers + participants

---

## ✅ Our Solution

SolMeet solves these with:

- 🛠️ Smart contract to store events & claims on-chain
- 📲 QR-based WebApp/Telegram claiming system
- 👛 Auto wallet generation 
- 🔐 Cryptographic guarantee that claims are unique & verified

---

## 🔍 Architecture Overview

1. Organizer creates an event using the Telegram bot or WebApp
2. A **unique on-chain event ID** is created via smart contract
3. A QR Code is generated for that event
4. Attendees scan the QR and claim via Here Wallet or generated wallet
5. Claims are validated and stored on Solana blockchain
6. Organizer views real-time claims via Web UI

---

## 🧠 Use Cases

- 🏫 University hackathons / workshops
- 🧑‍💻 Web3 & DAO community meetups
- 🎉 Local or global IRL events
- 🚀 NFT airdrop-based attendance rewards

---

## 💻 Live Demos

- 🌐 WebApp: [https://sol-meet.vercel.app](https://sol-meet.vercel.app)
- 🤖 Telegram Bot: (https://t.me/SolMeet_bot)
- 🔗 Program ID: `Gx3muwmBzRr8DVvyPdW46PNbT815TGcVqSf7q1WUeHwj`

---

## 📂 Folder Structure

```
SolMeet/
├── programs/solmeet/      # Rust-based Anchor smart contract
├── handlers/              # Telegram bot event handlers
├── utils/                 # Wallet, QR, and blockchain helpers
├── qr_codes/              # Pre-generated event claim QR codes
├── wallets/               # User wallet keypairs
├── attached_assets/       # IDL and config files
```

---

## 🛠 Setup Guide

```bash
# 1. Install dependencies
anchor install
pip install python-telegram-bot

# 2. Build and deploy program
anchor build
anchor deploy

# 3. Run Telegram Bot
python3 bot.py

# 4. Visit Web App
open https://sol-meet.vercel.app
```

---

## 📜 License

MIT License. Feel free to fork, build, and enhance the event experience for the decentralized world.

---

## 🤝 Contributions Welcome

Pull requests, ideas, and forks are welcome. If you’re a designer, dev, or blockchain builder — jump in!

> 💬 For any queries, reach out via Telegram or GitHub Discussions.

---

## 🌟 Credits

- Built by Mech-X
- Supported by Solana Devnet, Anchor, Vercel
- X/Twitter- https://x.com/_solmeet

---

> _“Events bring people together. SolMeet makes them verifiable, trustless, and fun.”_
