[README.md](https://github.com/user-attachments/files/33017797/README.md)
# 🧾 BillTrack — Bill & Payment Management System

> **Note**: This project was custom-built by **AI (Google Antigravity)** specifically tailored for personal and business use to track sales bills, purchase records, cheque deposit dates, and payments efficiently.

---

## 🌟 Overview

**BillTrack** is a lightweight, responsive local web application designed to track sales bills issued to retail shops and purchase bills received from factories. It includes payment tracking, cheque deposit scheduling, PDF bill attachments, automated balance calculation, and data export/backup utilities.

---

## ✨ Features

- **📊 Dashboard & Metrics**:
  - Overview of total outstanding amounts, fully paid bills, partial payments, and unpaid bills.
  - Interactive **Cheque Deposit Calendar** to visualize and manage cheque clearance dates.

- **📤 Sales Bills Management**:
  - Record bill numbers, dates, retail shop names, and assigned sales areas.
  - Support for multiple incremental payments (Cash, Cheque, Bank Transfer).
  - Outstanding balance calculated automatically.
  - PDF bill file attachments (up to 3MB) with inline preview support.

- **📥 Purchase Bills Management**:
  - Track factory purchases, bill numbers, dates, and total amounts.
  - PDF document attachment support.

- **🔒 Account & Security**:
  - First-time launcher admin setup screen.
  - Secure PBKDF2 HMAC password hashing and session tokens.
  - **In-App Password Change**: Option under Settings to update your login password.
  - **CLI Password Reset**: Easily reset credentials via terminal if locked out.

- **💾 Data Backup & Restore**:
  - Export Sales & Purchase bills as CSV files for Excel/Sheets.
  - Full database backup & restore in `.json` format.
  - Local SQLite database storage.

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.x** installed on your system.
- Modern web browser (Chrome, Firefox, Edge, Brave, etc.).

---

## 💻 Running the Application

### 🐧 On Linux

1. Clone or download this repository.
2. Open terminal in the project directory and grant execution permissions (if needed):
   ```bash
   chmod +x BillTrack.sh
   ```
3. Run the launcher script:
   ```bash
   ./BillTrack.sh
   ```
4. The server will start at `http://localhost:3000` and automatically open your default web browser.

---

### 🪟 On Windows

1. Double-click **`BillTrack.bat`** (located in the `local_version/` directory).
2. The batch script will start the Python server and open `http://localhost:3000` in your default browser.

---

### 🔑 First-Time Setup & Logging In

1. Upon opening `http://localhost:3000` for the first time, you will see the **First Launch Setup** screen.
2. Enter your desired **Username** and **Password** (minimum 6 characters).
3. Click **Create Admin & Sign In** to access your dashboard.

---

## 🛠 Command Line Tools

### Reset Password / Clear User Credentials
If you forget your password or get locked out:

1. Open terminal inside `local_version/` directory.
2. Run:
   ```bash
   python3 server.py --reset-password
   ```
3. Relaunch BillTrack to create your new username and password. Existing sales and purchase records will **not** be affected.

---

## ⚙️ Tech Stack

- **Frontend**: HTML5, CSS3 (Modern Glassmorphism Design), Vanilla JavaScript (ES6+)
- **Backend**: Python 3 (`http.server`, `sqlite3`, `hashlib`, `secrets`)
- **Database**: SQLite3
