# rob

A command-line tool for Robinhood portfolio management and AI-powered stock analysis.

```
┌────────────────────────────────────┐
│  Portfolio                         │
├────────────────────────────────────┤
│  Total      $125,432.00            │
│  Cash         $8,234.00            │
│  Invested   $117,198.00            │
└────────────────────────────────────┘

▶ 📊  View positions with ratings
  📈  Increase all positions by %
  📉  Decrease all positions by %
  🔍  Analyze a ticker
  ──────────────────────────────────
  ✗   Exit
```

## What It Does

### 🖥️ Interactive Dashboard

Run `rob` with no arguments to launch the interactive dashboard:

```bash
rob
```

This gives you a visual portfolio summary and menu to:

- View positions with ratings and allocation %
- Increase or decrease all positions by a percentage
- Analyze any ticker with AI
- Navigate with arrow keys, no commands to remember

### 📊 Portfolio Management

Increase or decrease **all** your Robinhood positions by a percentage with a single command. Perfect for systematic rebalancing or scaling in/out of your entire portfolio.

```bash
# Increase all positions by 5%
rob adjust --action increase --percentage 5

# Decrease all positions by 10% (taking profits)
rob adjust -a decrease -p 10

# Preview what would happen (no trades executed)
rob adjust -a increase -p 3 --dry-run
```

Features:

- **Cost estimation** before executing any trades
- **Balance checking** to prevent insufficient funds errors
- **Interactive confirmation** for each trade (or `--no-confirm` for automation)
- **Position-by-position control** with skip/abort options

### 🤖 AI Stock Analysis

Get comprehensive analysis on any stock using earnings data, transcripts, and real-time web search.

```bash
rob analyze AAPL
```

The analyzer:

1. Fetches latest **ticker data** (price, market cap, etc.)
2. Fetches latest **earnings report** (revenue, EPS, margins)
3. Fetches **earnings call transcript** (management commentary)
4. Runs analysis through **GPT-5.2 with web search** to:
   - Find comparable companies and relative valuation
   - Check recent news and analyst sentiment
   - Evaluate management credibility
   - Identify headwinds and tailwinds
   - Generate a 1-5 buy score with rationale

Results are **cached per quarter** - if you've already analyzed a stock for the current quarter, it shows the cached analysis instantly. Use `--refresh` to force a new analysis.

```bash
# Force fresh analysis even if cached
rob analyze AAPL --refresh
```

#### Analysis Output

Shows a compact summary first, then an interactive menu to drill into sections:

```
============================================================
         AAPL ANALYSIS SUMMARY
============================================================

  Rating: ★★★★☆ BUY
  Outlook: Long-term BULLISH | Short-term NEUTRAL
  Valuation: FAIRLY VALUED vs peers
  News: POSITIVE
  Management: 4/5
  ⚠ Top Risk: Smartphone market saturation in developed markets...
  ✦ Top Catalyst: Services revenue growing at 15% annually...

============================================================

  AAPL  ★★★★☆ BUY
  Strong services growth offsetting hardware maturity...

  ↑↓ Navigate  │  Enter Select  │  q Quit

▶ 📊 Summary & Rationale
  📈 Long-term Outlook
  📉 Short-term Outlook
  🏢 Comparables & Valuation
  📰 Recent News
  ⚠️  Risks & Headwinds
  🚀 Growth & Tailwinds
  👔 Management Assessment
  📋 Show All
  ✓ Done
```

### 📈 Interactive Position Viewer

```bash
rob positions
```

Browse all your positions sorted by value with allocation percentages and analysis ratings:

```
  Positions │ Select to analyze │ q Quit

▶ NVDA    $    45,200    35.2%  ★★★★★ BUY
  AAPL    $    32,500    25.3%  ★★★★☆ BUY
  MSFT    $    28,400    22.1%  ★★★★☆ BUY
  GOOGL   $    12,100     9.4%  ★★★☆☆ HOLD
  AMZN    $    10,200     7.9%
  ────────────────────────────────────────
  ✓ Done
```

Features:

- Positions sorted by value (largest first)
- Shows allocation percentage of total portfolio
- Displays cached buy/sell ratings (if analyzed)
- Select any position to view or run analysis
- Offer to refresh stale analyses

### 📊 Portfolio Summary

```bash
rob portfolio
```

Quick view of:

- Total portfolio value
- Available cash
- Each position with current price and value

## Installation

### Quick Install

```bash
git clone <repository-url>
cd rob
./install.sh
```

### Configure Credentials

```bash
rob config
```

You'll be prompted for:

**Robinhood Credentials:**

- **Username** (email)
- **Password**
- **TOTP secret** (optional, for automatic 2FA)

**API Keys (for `analyze` command):**

- **API Ninjas key** - for fetching earnings data and transcripts
- **OpenAI key** - for AI-powered analysis with GPT-5.2

All credentials are stored securely in `~/.config/rob/.env` with proper permissions (readable only by you).

### Getting API Keys

| Service    | Get Key                              | Notes                            |
| ---------- | ------------------------------------ | -------------------------------- |
| API Ninjas | https://api-ninjas.com/              | Free tier: 10,000 requests/month |
| OpenAI     | https://platform.openai.com/api-keys | Pay-per-use, ~$0.05 per analysis |

You can also pass keys directly via CLI options:

```bash
rob config --api-ninjas YOUR_KEY --openai YOUR_KEY
```

Or set individual keys without re-entering everything (just press Enter to keep existing values).

## Commands Reference

| Command              | Description                                         |
| -------------------- | --------------------------------------------------- |
| `rob`                | Interactive mode with portfolio dashboard and menus |
| `rob positions`      | Interactive position viewer with analysis ratings   |
| `rob portfolio`      | Show portfolio summary and positions (text output)  |
| `rob adjust`         | Bulk adjust positions by percentage                 |
| `rob analyze TICKER` | AI analysis of a stock                              |
| `rob config`         | Configure Robinhood credentials and API keys        |
| `rob --help`         | Show help                                           |

### `rob adjust` Options

| Option                   | Short | Description                                 |
| ------------------------ | ----- | ------------------------------------------- |
| `--action`               | `-a`  | `increase` or `decrease` (required)         |
| `--percentage`           | `-p`  | Percentage to adjust (0-100, required)      |
| `--confirm/--no-confirm` |       | Prompt before each trade (default: confirm) |
| `--dry-run`              |       | Preview trades without executing            |

### `rob analyze` Options

| Option      | Short | Description                       |
| ----------- | ----- | --------------------------------- |
| `--refresh` | `-r`  | Force new analysis even if cached |

### `rob config` Options

| Option          | Description                        |
| --------------- | ---------------------------------- |
| `--username`    | Robinhood username (email)         |
| `--password`    | Robinhood password                 |
| `--totp-secret` | TOTP secret for automatic 2FA      |
| `--api-ninjas`  | API Ninjas key (for earnings data) |
| `--openai`      | OpenAI API key (for AI analysis)   |

All options are interactive if not provided - just run `rob config` and follow the prompts.

## Examples

### Morning Portfolio Check

```bash
# Interactive dashboard - best for daily use
rob

# Or jump straight to positions with ratings
rob positions

# Quick text summary (no interactivity)
rob portfolio
```

### Scale Into Positions

```bash
# Preview first
rob adjust -a increase -p 5 --dry-run

# Execute with confirmation on each trade
rob adjust -a increase -p 5

# Execute without prompts (be careful!)
rob adjust -a increase -p 5 --no-confirm
```

### Research a Stock

```bash
rob analyze NVDA
```

### Analyze Multiple Stocks

```bash
for ticker in AAPL MSFT GOOGL; do
  rob analyze $ticker
done
```

## Setting Up Automatic 2FA

Instead of manually entering your 2FA code each time, configure automatic code generation:

### Getting Your TOTP Secret

**Option 1: Setting up 2FA for the first time**

1. When Robinhood shows you the QR code during 2FA setup
2. Look for "Can't scan? Enter manually"
3. Copy the secret key (looks like: `ABCD1234EFGH5678...`)
4. Run `rob config` and paste it when prompted

**Option 2: Already have 2FA enabled**

1. Temporarily disable 2FA in Robinhood security settings
2. Re-enable 2FA and grab the secret key when shown
3. Add it via `rob config`

**Option 3: From Google Authenticator**

1. Transfer accounts → Export accounts → Select Robinhood
2. Read QR code to get `otpauth-migration://offline?data={code}`
3. Use [otpauth](https://github.com/dim13/otpauth) to decode the secret

## How It Works

### Position Adjustment

1. Authenticates with Robinhood (uses saved token if available)
2. Fetches your current portfolio and positions
3. Calculates shares to trade for each position based on percentage
4. Shows estimated total cost and checks available cash
5. Iterates through each position:
   - Shows current position details
   - Calculates and displays proposed trade
   - Waits for confirmation (unless `--no-confirm`)
   - Executes market order
6. Logs out

### Stock Analysis

1. Checks for cached analysis from current quarter
2. If no cache or `--refresh`:
   - Fetches ticker data from API Ninjas
   - Fetches latest earnings transcript
   - Fetches earnings data for that quarter
   - Sends all data to GPT-5.2 with web search enabled
   - AI searches for comparables, recent news, analyst opinions
   - Generates structured analysis with buy score
   - Caches result for the quarter
3. Displays interactive analysis with drill-down menu

## Data Storage

- **Credentials**: `~/.config/rob/.env`
- **Auth token**: `./robinhood.pickle` (in current directory)
- **Analysis data**: `~/.config/rob/data/{TICKER}/`
  - `ticker_data.json` - Price, market cap, etc.
  - `earnings_YYYY_QN.json` - Quarterly earnings
  - `transcript_YYYY_QN.json` - Earnings call transcript
  - `analysis_YYYYMMDD.json` - AI analysis results

## Environment Variables

| Variable                | Description                       |
| ----------------------- | --------------------------------- |
| `ROBINHOOD_USERNAME`    | Robinhood email                   |
| `ROBINHOOD_PASSWORD`    | Robinhood password                |
| `ROBINHOOD_TOTP_SECRET` | TOTP secret for automatic 2FA     |
| `API_NINJAS_KEY`        | API Ninjas API key (for analysis) |
| `OPENAI_KEY`            | OpenAI API key (for analysis)     |
| `ROB_DEBUG`             | Set to `1` for debug output       |

## Troubleshooting

### Permission denied accessing ~/.config/rob/.env

If you see this error, the config directory was created with root ownership during installation. Fix it with:

```bash
sudo chown -R $USER ~/.config/rob
```

Then run `rob config` to set up your credentials.

## Disclaimer

⚠️ **This tool executes real trades on your Robinhood account.**

- Always review each trade carefully before confirming
- Use `--dry-run` to preview trades first
- The authors are not responsible for any financial losses
- AI analysis is for informational purposes only - not financial advice

## License

MIT
