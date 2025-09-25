# rob

Rob lets you manage your Robinhood Portfolio in bulk. Increase or decrease all of your positions by some percentage

## Features

- **Portfolio Overview**: Displays total portfolio value and available cash on startup
- **Cost Estimation**: Shows expected total cost before processing any trades
- **Balance Checking**: Prevents trades if insufficient funds available
- **Bulk position management**: Increase or decrease all your positions by a percentage
- **Interactive confirmation**: Review each trade before execution
- **Safety features**: Skip or abort at any time
- **Clear display**: Shows current position, shares to trade, and estimated cost
- **Secure authentication**: Supports 2FA and secure password input

## Installation

1. Install dependencies:

```bash
pip3 install -r requirements.txt
```

2. (Optional) Create a `.env` file for credentials:

```bash
ROBINHOOD_USERNAME=your_email@example.com
ROBINHOOD_PASSWORD=your_password

# For automatic 2FA code generation (highly recommended!)
ROBINHOOD_TOTP_SECRET=YOUR_SECRET_KEY_HERE
```

### Setting Up Automatic 2FA Code Generation

Instead of manually entering your 2FA code each time, you can configure automatic code generation:

**How to get your TOTP secret:**

**Option 1: If setting up 2FA for the first time:**

1. When Robinhood shows you the QR code during 2FA setup
2. Look for "Can't scan? Enter manually" or similar option
3. Copy the secret key shown (looks like: `ABCD1234EFGH5678...`)
4. Add it to your `.env` file as `ROBINHOOD_TOTP_SECRET`

**Option 2: If you already have 2FA enabled:**

1. Temporarily disable 2FA in your Robinhood security settings
2. Re-enable 2FA and grab the secret key when shown
3. Add it to your `.env` file as `ROBINHOOD_TOTP_SECRET`
4. Keep this secret secure - it's like a password!

**Option 3: If you have Google Authenticator:**

1. Transfer accounts
2. Export accounts
3. Select robinhood
4. Read QR code, you should get something like `otpauth-migration://offline?data={code}`
5. Use [this package](https://github.com/dim13/otpauth) or something similar to decode the secret value (looks like `ACBDEFGH12345678`)

With the TOTP secret configured, the tool will automatically generate fresh 2FA codes when needed, eliminating the need to check your authenticator app.

Note: After first successful login, the tool saves an authentication token to `robinhood.pickle` for faster subsequent logins.

## Usage

Simply run the script with no arguments:

```bash
python3 rob.py
```

## Example Session

```
$ python3 rob.py

============================================================
         Robinhood Position Manager
============================================================

Enter your Robinhood username (email): user@example.com
Enter your Robinhood password:
Enter your 2FA code (if applicable, press Enter to skip): 123456
✓ Successfully authenticated with Robinhood

Fetching portfolio information...

Portfolio Summary:
  Total Portfolio Value: $50,000.00
  Available Cash: $5,000.00
  Positions Value: $45,000.00

What would you like to do?
  1) Increase positions
  2) Decrease positions
  3) Exit

Enter your choice (1-3): 1

Enter the percentage to increase positions by: 5

Calculating expected cost...

Operation Summary:
  Action: INCREASE positions by 5%
  Expected Total Cost: $2,250.00
  Available Cash: $5,000.00
  Remaining Cash After: $2,750.00

Proceed with increasing positions? (yes/no): yes

============================================================
Processing positions to increase by 5.0%
============================================================

[1/3] AAPL
  Current position: 100.00 shares @ $150.00 avg
  Current price: $175.00
  → BUY 5 shares for ~$875.00

  Press ENTER to execute, 'skip' to skip, or 'abort' to exit: [ENTER]
✓ Bought 5 shares of AAPL
------------------------------------------------------------

[2/3] TSLA
  Current position: 50.00 shares @ $200.00 avg
  Current price: $250.00
  → BUY 2 shares for ~$500.00

  Press ENTER to execute, 'skip' to skip, or 'abort' to exit: skip
Skipping TSLA
------------------------------------------------------------

Position processing complete!
✓ Logged out successfully
```

## Disclaimer

This tool executes real trades on your Robinhood account. Use at your own risk. Always review each trade carefully before confirming. The authors are not responsible for any financial losses incurred through the use of this tool.
