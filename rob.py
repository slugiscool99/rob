#!/usr/bin/env python3
"""
Robinhood Position Manager CLI Tool
Allows you to increase or decrease positions by a specified percentage
"""

import os
import sys
import time
import getpass
import json
import requests
from datetime import datetime
from typing import Dict, Tuple, Optional, List
from decimal import Decimal, ROUND_DOWN
from colorama import init, Fore, Style
import robin_stocks.robinhood as rs
from dotenv import load_dotenv
import pyotp
import click
from openai import OpenAI
from simple_term_menu import TerminalMenu

# Initialize colorama for colored output
init(autoreset=True)

class RobinhoodPositionManager:
    def __init__(self):
        """Initialize the position manager"""
        self.load_credentials()
        self.authenticated = False

    def load_credentials(self):
        """Load credentials from multiple possible locations"""
        # Try loading from current directory first
        load_dotenv()

        # If no credentials found, try user config directory
        if not (os.getenv('ROBINHOOD_USERNAME') and os.getenv('ROBINHOOD_PASSWORD')):
            # Try ~/.config/rob/.env
            config_dir = os.path.expanduser("~/.config/rob")
            config_env = os.path.join(config_dir, ".env")
            if os.path.exists(config_env):
                try:
                    load_dotenv(config_env)
                except PermissionError:
                    print(f"{Fore.RED}Permission denied accessing {config_env}{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}Try running with sudo: sudo rob{Style.RESET_ALL}")
                    sys.exit(1)

            # Try ~/.rob/.env as fallback
            elif os.path.exists(os.path.expanduser("~/.rob/.env")):
                try:
                    load_dotenv(os.path.expanduser("~/.rob/.env"))
                except PermissionError:
                    rob_env = os.path.expanduser("~/.rob/.env")
                    print(f"{Fore.RED}Permission denied accessing {rob_env}{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}Try running with sudo: sudo rob{Style.RESET_ALL}")
                    sys.exit(1)
        
    def authenticate(self) -> bool:
        """Authenticate with Robinhood"""
        pickle_path = os.path.join(os.getcwd(), "robinhood.pickle")
        
        print(f"{Fore.CYAN}Authentication token path: {pickle_path}{Style.RESET_ALL}")
        
        # Try to use existing pickle file first
        if os.path.exists(pickle_path):
            print(f"{Fore.GREEN}✓ Found existing authentication token{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Attempting to authenticate with saved token...{Style.RESET_ALL}")
            try:
                # Try to load existing session
                login = rs.login(store_session=True, pickle_name='robinhood')
                if login:
                    self.authenticated = True
                    print(f"{Fore.GREEN}✓ Successfully authenticated using saved token{Style.RESET_ALL}")
                    return True
                else:
                    print(f"{Fore.YELLOW}Saved token invalid or expired{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}Removing old token and requesting new login...{Style.RESET_ALL}")
                    os.remove(pickle_path)
            except Exception as e:
                print(f"{Fore.YELLOW}Could not use saved token: {e}{Style.RESET_ALL}")
                if os.path.exists(pickle_path):
                    try:
                        os.remove(pickle_path)
                        print(f"{Fore.CYAN}Removed invalid token file{Style.RESET_ALL}")
                    except:
                        pass
        
        # Get credentials
        username = os.getenv('ROBINHOOD_USERNAME')
        password = os.getenv('ROBINHOOD_PASSWORD')
        totp_secret = os.getenv('ROBINHOOD_TOTP_SECRET')  # The secret key for TOTP generation
        
        if not username:
            username = input("Enter your Robinhood username (email): ")
        if not password:
            password = getpass.getpass("Enter your Robinhood password: ")
        
        # Generate or get MFA code
        mfa_code = None
        if totp_secret:
            # Automatically generate MFA code using TOTP secret
            try:
                totp = pyotp.TOTP(totp_secret)
                mfa_code = totp.now()
                print(f"\n{Fore.GREEN}✓ Generated 2FA code automatically{Style.RESET_ALL}")
                print(f"{Fore.CYAN}Code: {mfa_code[:3]}xxx (expires in ~{30 - (time.time() % 30):.0f} seconds){Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.YELLOW}Warning: Could not generate TOTP code: {e}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Falling back to manual entry...{Style.RESET_ALL}")
        
        # Fall back to manual entry if no TOTP secret or generation failed
        if not mfa_code:
            # Check for hardcoded MFA code in env (not recommended)
            mfa_code = os.getenv('ROBINHOOD_MFA_CODE')
            if not mfa_code:
                print(f"\n{Fore.YELLOW}Note: 2FA code is required for first-time login{Style.RESET_ALL}")
                print(f"{Fore.CYAN}Tip: Add ROBINHOOD_TOTP_SECRET to your .env file to auto-generate codes{Style.RESET_ALL}")
                mfa_code = input("Enter your 2FA code (required if 2FA is enabled): ").strip()
        
        # Initial login attempt
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                print(f"\n{Fore.CYAN}Attempting authentication (attempt {attempt + 1}/{max_attempts})...{Style.RESET_ALL}")
                
                # Always provide mfa_code parameter (can be empty string)
                if mfa_code:
                    print(f"{Fore.CYAN}Using 2FA code: {mfa_code[:3]}...{Style.RESET_ALL}")
                    login = rs.login(
                        username=username, 
                        password=password, 
                        mfa_code=mfa_code, 
                        store_session=True,  # Explicitly request session storage
                        pickle_name='robinhood'
                    )
                else:
                    print(f"{Fore.CYAN}Attempting login without 2FA...{Style.RESET_ALL}")
                    login = rs.login(
                        username=username, 
                        password=password, 
                        store_session=True,  # Explicitly request session storage
                        pickle_name='robinhood'
                    )
                
                if login:
                    self.authenticated = True
                    print(f"{Fore.GREEN}✓ Successfully authenticated with Robinhood{Style.RESET_ALL}")
                    
                    # Check if pickle file was created
                    time.sleep(0.5)  # Give it a moment to write the file
                    
                    if os.path.exists(pickle_path):
                        file_size = os.path.getsize(pickle_path)
                        print(f"{Fore.GREEN}✓ Authentication token saved ({file_size} bytes){Style.RESET_ALL}")
                        print(f"{Fore.CYAN}  Token location: {pickle_path}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.YELLOW}⚠ Warning: Authentication token was not saved{Style.RESET_ALL}")
                        print(f"{Fore.YELLOW}  You'll need to authenticate again next time{Style.RESET_ALL}")
                        
                        # List all pickle files in directory
                        pickle_files = [f for f in os.listdir(os.getcwd()) if 'pickle' in f.lower()]
                        if pickle_files:
                            print(f"{Fore.CYAN}  Found these pickle files: {', '.join(pickle_files)}{Style.RESET_ALL}")
                    
                    return True
                else:
                    print(f"{Fore.RED}Authentication failed{Style.RESET_ALL}")
                    
            except Exception as e:
                error_msg = str(e)
                
                # The 'detail' error specifically means device verification is required
                if "'detail'" in error_msg or "detail" in error_msg:
                    print(f"\n{Fore.YELLOW}═══════════════════════════════════════════{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}     DEVICE VERIFICATION REQUIRED!{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}═══════════════════════════════════════════{Style.RESET_ALL}")
                    print(f"\n{Fore.CYAN}Robinhood needs you to approve this login:{Style.RESET_ALL}")
                    print(f"  1. {Fore.WHITE}Open your Robinhood app{Style.RESET_ALL}")
                    print(f"  2. {Fore.WHITE}Look for 'Is this you trying to log in?' notification{Style.RESET_ALL}")
                    print(f"  3. {Fore.WHITE}Tap 'Yes, it's me' to approve{Style.RESET_ALL}")
                    print(f"  4. {Fore.WHITE}Come back here and press ENTER{Style.RESET_ALL}")
                    
                    input(f"\n{Fore.YELLOW}➜ Press ENTER after approving on your device...{Style.RESET_ALL}")
                    
                    # Clear MFA for retry - it was already consumed
                    mfa_code = ''
                    print(f"\n{Fore.CYAN}Retrying authentication...{Style.RESET_ALL}")
                    
                    # Small delay to ensure device approval is registered
                    time.sleep(3)
                    continue
                
                # Other device/challenge errors
                elif 'challenge' in error_msg.lower() or 'device' in error_msg.lower():
                    print(f"\n{Fore.YELLOW}Authentication challenge detected: {error_msg}{Style.RESET_ALL}")
                    input(f"{Fore.YELLOW}Complete any required steps and press ENTER to retry...{Style.RESET_ALL}")
                    mfa_code = ''
                    time.sleep(2)
                    continue
                
                # Check for invalid MFA
                elif 'mfa' in error_msg.lower() or 'code' in error_msg.lower():
                    if totp_secret and attempt < max_attempts - 1:
                        # Regenerate TOTP code (it might have expired)
                        print(f"{Fore.YELLOW}2FA code may have expired. Regenerating...{Style.RESET_ALL}")
                        time.sleep(2)  # Wait a bit to ensure we get a new code
                        totp = pyotp.TOTP(totp_secret)
                        mfa_code = totp.now()
                        print(f"{Fore.CYAN}New code: {mfa_code[:3]}xxx{Style.RESET_ALL}")
                        continue
                    elif attempt == 0:
                        print(f"{Fore.RED}Invalid 2FA code. Trying without it...{Style.RESET_ALL}")
                        mfa_code = None
                        continue
                    else:
                        print(f"{Fore.RED}Authentication failed: Invalid credentials or 2FA code{Style.RESET_ALL}")
                        return False
                
                # Other errors
                else:
                    if attempt < max_attempts - 1:
                        print(f"{Fore.YELLOW}Retrying...{Style.RESET_ALL}")
                        time.sleep(2)
                        continue
                    else:
                        print(f"{Fore.RED}✗ Authentication failed after {max_attempts} attempts{Style.RESET_ALL}")
                        print(f"{Fore.YELLOW}Tips:{Style.RESET_ALL}")
                        print(f"  - Make sure your username and password are correct")
                        print(f"  - If using 2FA, ensure the code is current (within 30 seconds)")
                        print(f"  - Try logging into Robinhood website first to verify your account")
                        return False
        
        return False
    
    def get_portfolio_summary(self) -> Tuple[float, float, float]:
        """
        Get portfolio summary including total value and available cash
        
        Returns:
            Tuple of (portfolio_value, available_cash, positions_value)
        """
        try:
            # Get account profile data
            profile = rs.profiles.load_account_profile()
            
            # Get portfolio data
            portfolio = rs.profiles.load_portfolio_profile()
            
            # Get available cash (buying power)
            available_cash = float(profile.get('buying_power', 0))
            
            # Get total portfolio value (equity)
            portfolio_value = float(portfolio.get('extended_hours_equity') or 
                                   portfolio.get('equity') or 0)
            
            # Calculate positions value (portfolio minus cash)
            positions_value = portfolio_value - available_cash
            
            return portfolio_value, available_cash, positions_value
            
        except Exception as e:
            print(f"{Fore.RED}Error fetching portfolio summary: {e}{Style.RESET_ALL}")
            return 0.0, 0.0, 0.0
    
    def get_positions(self) -> Dict:
        """Get all current positions"""
        try:
            positions = rs.build_holdings()
            return positions
        except Exception as e:
            print(f"{Fore.RED}Error fetching positions: {e}{Style.RESET_ALL}")
            return {}
    
    def calculate_total_expected_cost(self, action: str, percentage: float) -> float:
        """
        Calculate the total expected cost for all positions
        
        Returns:
            Total expected cost/proceeds for the operation
        """
        positions = self.get_positions()
        if not positions:
            return 0.0
        
        total_cost = 0.0
        
        for symbol, position_data in positions.items():
            try:
                shares_to_trade, cost = self.calculate_shares_to_trade(
                    symbol, position_data, percentage, action
                )
                total_cost += cost
            except Exception:
                continue
        
        return total_cost
    
    def calculate_shares_to_trade(self, symbol: str, position_data: Dict, 
                                  percentage: float, action: str) -> Tuple[int, float]:
        """
        Calculate the number of shares to buy/sell and the estimated cost
        
        Returns:
            Tuple of (shares_to_trade, estimated_cost)
        """
        current_shares = float(position_data.get('quantity', 0))
        current_price = float(rs.stocks.get_latest_price(symbol)[0])
        
        if action == 'increase':
            # Calculate shares to add based on percentage of current position value
            current_value = current_shares * current_price
            amount_to_add = current_value * (percentage / 100)
            shares_to_buy = int(amount_to_add / current_price)
            estimated_cost = shares_to_buy * current_price
            return shares_to_buy, estimated_cost
            
        else:  # decrease
            # Calculate shares to sell based on percentage of current holdings
            shares_to_sell = int(current_shares * (percentage / 100))
            estimated_proceeds = shares_to_sell * current_price
            return shares_to_sell, estimated_proceeds
    
    def execute_trade(self, symbol: str, shares: int, action: str) -> bool:
        """Execute a buy or sell order"""
        try:
            if action == 'increase':
                # Place market buy order
                order = rs.orders.order_buy_market(
                    symbol=symbol,
                    quantity=shares,
                    timeInForce='gfd'  # Good for day
                )
                if order:
                    print(f"{Fore.GREEN}✓ Bought {shares} shares of {symbol}{Style.RESET_ALL}")
                    return True
            else:  # decrease
                # Place market sell order
                order = rs.orders.order_sell_market(
                    symbol=symbol,
                    quantity=shares,
                    timeInForce='gfd'
                )
                if order:
                    print(f"{Fore.GREEN}✓ Sold {shares} shares of {symbol}{Style.RESET_ALL}")
                    return True
            
            print(f"{Fore.RED}✗ Order failed for {symbol}{Style.RESET_ALL}")
            return False
            
        except Exception as e:
            print(f"{Fore.RED}✗ Trade execution error for {symbol}: {e}{Style.RESET_ALL}")
            return False
    
    def process_positions(self, action: str, percentage: float, dry_run: bool = False, auto_confirm: bool = False):
        """Process positions one by one"""
        positions = self.get_positions()

        if not positions:
            print(f"{Fore.YELLOW}No positions found in your account{Style.RESET_ALL}")
            return

        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        if dry_run:
            print(f"{Fore.CYAN}DRY RUN - Processing positions to {action} by {percentage}%{Style.RESET_ALL}")
        else:
            print(f"{Fore.CYAN}Processing positions to {action} by {percentage}%{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

        # Sort positions by symbol for consistent ordering
        sorted_positions = sorted(positions.items())
        total_positions = len(sorted_positions)

        for index, (symbol, position_data) in enumerate(sorted_positions, 1):
            try:
                # Get current price and calculate trade
                current_price = float(rs.stocks.get_latest_price(symbol)[0])
                current_shares = float(position_data.get('quantity', 0))
                avg_cost = float(position_data.get('average_buy_price', 0))

                shares_to_trade, cost = self.calculate_shares_to_trade(
                    symbol, position_data, percentage, action
                )

                if shares_to_trade == 0:
                    print(f"{Fore.YELLOW}Skipping {symbol} - calculated 0 shares to trade{Style.RESET_ALL}")
                    continue

                # Display position information
                print(f"{Fore.WHITE}[{index}/{total_positions}] {Fore.CYAN}{symbol}{Style.RESET_ALL}")
                print(f"  Current position: {current_shares:.2f} shares @ ${avg_cost:.2f} avg")
                print(f"  Current price: ${current_price:.2f}")

                if action == 'increase':
                    print(f"  {Fore.GREEN}→ BUY {shares_to_trade} shares for ~${cost:.2f}{Style.RESET_ALL}")
                else:
                    print(f"  {Fore.RED}→ SELL {shares_to_trade} shares for ~${cost:.2f}{Style.RESET_ALL}")

                # Handle confirmation based on mode
                if dry_run:
                    print(f"{Fore.CYAN}DRY RUN: Would execute trade{Style.RESET_ALL}")
                elif auto_confirm:
                    print(f"{Fore.GREEN}Auto-confirming trade...{Style.RESET_ALL}")
                    success = self.execute_trade(symbol, shares_to_trade, action)
                    if success:
                        time.sleep(1)  # Small delay between trades
                else:
                    # Wait for user confirmation
                    print(f"\n  {Fore.YELLOW}Press ENTER to execute, 'skip' to skip, or 'abort' to exit:{Style.RESET_ALL} ", end='')
                    user_input = input().strip().lower()

                    if user_input == 'abort':
                        print(f"\n{Fore.RED}Aborting... No further trades will be executed.{Style.RESET_ALL}")
                        break
                    elif user_input == 'skip' or user_input == 's':
                        print(f"{Fore.YELLOW}Skipping {symbol}{Style.RESET_ALL}")
                        print(f"{Fore.CYAN}{'-'*60}{Style.RESET_ALL}\n")
                        continue
                    elif user_input == '':
                        # Execute the trade
                        success = self.execute_trade(symbol, shares_to_trade, action)
                        if success:
                            time.sleep(1)  # Small delay between trades
                    else:
                        print(f"{Fore.YELLOW}Invalid input. Skipping {symbol}{Style.RESET_ALL}")

                print(f"{Fore.CYAN}{'-'*60}{Style.RESET_ALL}\n")

            except Exception as e:
                print(f"{Fore.RED}Error processing {symbol}: {e}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{'-'*60}{Style.RESET_ALL}\n")
                continue

        if dry_run:
            print(f"\n{Fore.GREEN}Dry run complete! No trades were executed.{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.GREEN}Position processing complete!{Style.RESET_ALL}")
    
    def logout(self):
        """Logout from Robinhood"""
        try:
            rs.logout()
            print(f"{Fore.GREEN}✓ Logged out successfully{Style.RESET_ALL}")
        except:
            pass


class TickerAnalyzer:
    """Fetches and stores earnings data from API Ninjas"""
    
    def __init__(self):
        """Initialize the analyzer and load API credentials"""
        self.load_credentials()
        self.data_dir = self._get_data_dir()
    
    def _get_data_dir(self) -> str:
        """Get or create the data directory, handling permission issues"""
        # Try primary location first
        primary_dir = os.path.expanduser("~/.config/rob/data")
        fallback_dir = os.path.expanduser("~/.rob/data")
        
        for data_dir in [primary_dir, fallback_dir]:
            try:
                os.makedirs(data_dir, exist_ok=True)
                # Test we can actually write to it
                test_file = os.path.join(data_dir, ".write_test")
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write("test")
                os.remove(test_file)
                return data_dir
            except PermissionError:
                continue
            except OSError:
                continue
        
        # If all else fails, use current directory
        local_dir = os.path.join(os.getcwd(), ".rob-data")
        os.makedirs(local_dir, exist_ok=True)
        print(f"{Fore.YELLOW}Warning: Using local data directory: {local_dir}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Run 'sudo chown -R $(whoami) ~/.config/rob' to fix permissions{Style.RESET_ALL}")
        return local_dir
        
    def load_credentials(self):
        """Load API Ninjas credentials from environment"""
        # Try loading from current directory first
        load_dotenv()
        
        # If no credentials found, try user config directory
        if not os.getenv('API_NINJAS_KEY'):
            config_dir = os.path.expanduser("~/.config/rob")
            config_env = os.path.join(config_dir, ".env")
            if os.path.exists(config_env):
                load_dotenv(config_env)
            elif os.path.exists(os.path.expanduser("~/.rob/.env")):
                load_dotenv(os.path.expanduser("~/.rob/.env"))
        
        self.api_base = "https://api.api-ninjas.com"
        self.api_key = os.getenv('API_NINJAS_KEY')
        self.openai_key = os.getenv('OPENAI_KEY')
        
        if not self.api_key:
            raise ValueError("API_NINJAS_KEY not found in environment. Add it to ~/.config/rob/.env")
    
    def get_ticker_dir(self, ticker: str) -> str:
        """Get the data directory for a specific ticker"""
        ticker_dir = os.path.join(self.data_dir, ticker.upper())
        os.makedirs(ticker_dir, exist_ok=True)
        return ticker_dir
    
    def clear_old_files(self, ticker: str, prefix: str):
        """Remove old files with given prefix for a ticker (keeps only latest)"""
        ticker_dir = self.get_ticker_dir(ticker)
        
        for filename in os.listdir(ticker_dir):
            if filename.startswith(prefix) and filename.endswith('.json'):
                filepath = os.path.join(ticker_dir, filename)
                try:
                    os.remove(filepath)
                except OSError:
                    pass
    
    def fetch_ticker_data(self, ticker: str) -> Optional[Dict]:
        """Fetch company/price data from API Ninjas"""
        url = f"{self.api_base}/v1/ticker"
        headers = {'X-Api-Key': self.api_key}
        params = {'ticker': ticker.upper()}
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                print(f"{Fore.YELLOW}No ticker data found for {ticker}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Error fetching ticker data: {e}{Style.RESET_ALL}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"{Fore.RED}Error fetching ticker data: {e}{Style.RESET_ALL}")
            return None
    
    def fetch_earnings(self, ticker: str, year: Optional[int] = None, quarter: Optional[int] = None) -> Optional[Dict]:
        """Fetch earnings data from API Ninjas"""
        url = f"{self.api_base}/v1/earnings"
        headers = {'X-Api-Key': self.api_key}
        params = {'ticker': ticker.upper()}
        
        if year is not None and quarter is not None:
            params['year'] = year
            params['quarter'] = quarter
        
        if os.getenv('ROB_DEBUG'):
            print(f"  [DEBUG] Earnings API request: {url}?{params}")
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if os.getenv('ROB_DEBUG'):
                print(f"  [DEBUG] Response status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    ci = data.get('company_info', {})
                    print(f"  [DEBUG] Returned: {ci.get('fiscal_year')} Q{ci.get('fiscal_quarter')}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                print(f"{Fore.YELLOW}No earnings data found for {ticker}{Style.RESET_ALL}")
            elif response.status_code == 400:
                print(f"{Fore.RED}Error fetching earnings: {e}{Style.RESET_ALL}")
                # Suggest common alternatives
                alternatives = {
                    'GOOG': 'GOOGL', 'GOOGL': 'GOOG',
                    'BRK.A': 'BRK-A', 'BRK.B': 'BRK-B',
                    'BRK-A': 'BRK.A', 'BRK-B': 'BRK.B',
                }
                if ticker in alternatives:
                    print(f"{Fore.YELLOW}  💡 Try using {alternatives[ticker]} instead{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Error fetching earnings: {e}{Style.RESET_ALL}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"{Fore.RED}Error fetching earnings: {e}{Style.RESET_ALL}")
            return None
    
    def fetch_transcript(self, ticker: str, year: Optional[int] = None, quarter: Optional[int] = None) -> Optional[Dict]:
        """Fetch earnings transcript from API Ninjas"""
        url = f"{self.api_base}/v1/earningstranscript"
        headers = {'X-Api-Key': self.api_key}
        params = {'ticker': ticker.upper()}
        
        if year is not None and quarter is not None:
            params['year'] = year
            params['quarter'] = quarter
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                print(f"{Fore.YELLOW}No transcript data found for {ticker}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Error fetching transcript: {e}{Style.RESET_ALL}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"{Fore.RED}Error fetching transcript: {e}{Style.RESET_ALL}")
            return None
    
    def fetch_earnings_calendar(self, ticker: str) -> Optional[List[Dict]]:
        """Fetch earnings calendar (historical EPS/revenue) from API Ninjas"""
        url = f"{self.api_base}/v1/earningscalendar"
        headers = {'X-Api-Key': self.api_key}
        params = {'ticker': ticker.upper()}
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()  # Returns a list
        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                print(f"{Fore.YELLOW}No earnings calendar found for {ticker}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Error fetching earnings calendar: {e}{Style.RESET_ALL}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"{Fore.RED}Error fetching earnings calendar: {e}{Style.RESET_ALL}")
            return None
    
    def save_earnings_calendar(self, ticker: str, data: List[Dict]) -> str:
        """Save earnings calendar data to file"""
        ticker_dir = self.get_ticker_dir(ticker)
        
        # Remove old earnings calendar files
        self.clear_old_files(ticker, 'earnings_calendar')
        
        filename = "earnings_calendar.json"
        filepath = os.path.join(ticker_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        return filepath
    
    def save_earnings(self, ticker: str, data: Dict) -> str:
        """Save earnings data to file, removing any old earnings files first"""
        ticker_dir = self.get_ticker_dir(ticker)
        
        # Remove old earnings files - only keep latest
        self.clear_old_files(ticker, 'earnings_')
        
        # Extract year and quarter from the data - try multiple locations
        year = None
        quarter = None
        
        # Try company_info first
        company_info = data.get('company_info', {})
        if company_info:
            year = company_info.get('fiscal_year')
            quarter = company_info.get('fiscal_quarter')
        
        # Fallback: try root level
        if not year or not quarter:
            year = data.get('year') or data.get('fiscal_year')
            quarter = data.get('quarter') or data.get('fiscal_quarter')
        
        # Fallback: try filing_info
        if not year or not quarter:
            filing_info = data.get('filing_info', {})
            if filing_info and filing_info.get('period_end_date'):
                # Parse from period_end_date if available
                pass  # Could extract from date string if needed
        
        if not year or not quarter:
            filename = "earnings_latest.json"
            print(f"{Fore.YELLOW}  Warning: Could not determine quarter from earnings data{Style.RESET_ALL}")
            if os.getenv('ROB_DEBUG'):
                print(f"  [DEBUG] company_info: {company_info}")
                print(f"  [DEBUG] root keys: {list(data.keys())}")
        else:
            # Ensure integers (API might return floats or strings)
            year = int(float(year)) if year else None
            quarter = int(float(quarter)) if quarter else None
            filename = f"earnings_{year}_Q{quarter}.json"
            if os.getenv('ROB_DEBUG'):
                print(f"  [DEBUG] Parsed year={year}, quarter={quarter} from earnings")
        
        filepath = os.path.join(ticker_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        return filepath
    
    def save_transcript(self, ticker: str, data: Dict) -> str:
        """Save transcript data to file, removing any old transcript files first"""
        ticker_dir = self.get_ticker_dir(ticker)
        
        # Remove old transcript files - only keep latest
        self.clear_old_files(ticker, 'transcript_')
        
        # Extract year and quarter from the data
        year = data.get('year')
        quarter = data.get('quarter')
        
        if not year or not quarter:
            filename = "transcript_latest.json"
        else:
            # Convert to int if string
            year = int(year)
            quarter = int(quarter)
            filename = f"transcript_{year}_Q{quarter}.json"
        
        filepath = os.path.join(ticker_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        return filepath
    
    def save_ticker_data(self, ticker: str, data: Dict) -> str:
        """Save ticker/price data to file, replacing any old ticker data"""
        ticker_dir = self.get_ticker_dir(ticker)
        
        # Remove old ticker files - only keep latest
        self.clear_old_files(ticker, 'ticker_')
        
        filename = "ticker_data.json"
        filepath = os.path.join(ticker_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        return filepath
    
    def save_analysis(self, ticker: str, analysis: Dict, earnings_quarter: Optional[Tuple[int, int]] = None) -> str:
        """Save AI analysis to file"""
        ticker_dir = self.get_ticker_dir(ticker)
        
        # Remove old analysis files
        self.clear_old_files(ticker, 'analysis_')
        
        # Include quarter info in the analysis for cache validation
        if earnings_quarter:
            analysis['_earnings_year'] = earnings_quarter[0]
            analysis['_earnings_quarter'] = earnings_quarter[1]
        
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = f"analysis_{timestamp}.json"
        filepath = os.path.join(ticker_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2)
        
        return filepath
    
    def load_existing_analysis(self, ticker: str) -> Optional[Dict]:
        """Load existing analysis if available"""
        ticker_dir = self.get_ticker_dir(ticker)
        
        for filename in os.listdir(ticker_dir):
            if filename.startswith('analysis_') and filename.endswith('.json'):
                filepath = os.path.join(ticker_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except (json.JSONDecodeError, OSError):
                    return None
        return None
    
    def get_latest_quarter_from_api(self, ticker: str) -> Optional[Tuple[int, int]]:
        """Quickly check what the latest quarter is from the API without full fetch"""
        # Use ticker endpoint which includes latest_earnings info
        ticker_data = self.fetch_ticker_data(ticker)
        if ticker_data:
            latest_earnings = ticker_data.get('latest_earnings', {})
            year = latest_earnings.get('year')
            quarter = latest_earnings.get('quarter')
            if year and quarter:
                return (int(year), int(quarter))
        return None
    
    def load_existing_data(self, ticker: str) -> Tuple[Optional[Dict], Optional[Dict], Optional[List[Dict]]]:
        """Load existing ticker, transcript, and earnings calendar data from disk"""
        ticker_dir = self.get_ticker_dir(ticker)
        ticker_data = None
        transcript_data = None
        earnings_calendar = None
        
        for filename in os.listdir(ticker_dir):
            filepath = os.path.join(ticker_dir, filename)
            try:
                if filename.startswith('ticker_') and filename.endswith('.json'):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        ticker_data = json.load(f)
                elif filename.startswith('transcript_') and filename.endswith('.json'):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        transcript_data = json.load(f)
                elif filename == 'earnings_calendar.json':
                    with open(filepath, 'r', encoding='utf-8') as f:
                        earnings_calendar = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
        
        return ticker_data, transcript_data, earnings_calendar
    
    def is_analysis_current(self, ticker: str) -> Tuple[bool, Optional[Dict], Optional[Tuple[int, int]]]:
        """Check if existing analysis matches the latest available quarter.
        Returns (is_current, existing_analysis, latest_quarter_from_api)
        
        Queries API to see if new data is available, but uses cached analysis
        if we already have that quarter analyzed.
        """
        existing = self.load_existing_analysis(ticker)
        
        # Check what the latest quarter is from API
        print(f"  Checking for new quarterly data...")
        latest = self.get_latest_quarter_from_api(ticker)
        
        if not existing:
            return False, None, latest
        
        # Get the quarter the analysis was based on
        analysis_year = existing.get('_earnings_year')
        analysis_quarter = existing.get('_earnings_quarter')
        
        if not analysis_year or not analysis_quarter:
            # Old analysis without quarter info, consider stale
            return False, existing, latest
        
        if not latest:
            # Can't determine latest from API, trust existing
            return True, existing, None
        
        # Compare: do we have analysis for the latest quarter?
        is_current = (analysis_year, analysis_quarter) == latest
        return is_current, existing, latest
    
    def analyze_with_ai(self, ticker: str, ticker_data: Dict, transcript_data: Dict, earnings_calendar: Optional[List[Dict]] = None) -> Optional[Dict]:
        """Use OpenAI to analyze the company data"""
        if not self.openai_key:
            print(f"{Fore.YELLOW}OPENAI_KEY not found - skipping AI analysis{Style.RESET_ALL}")
            return None
        
        client = OpenAI(api_key=self.openai_key)
        
        # Build context from saved data
        context_parts = []
        
        if ticker_data:
            context_parts.append(f"## Company Information\n```json\n{json.dumps(ticker_data, indent=2)}\n```")
        
        if earnings_calendar:
            context_parts.append(f"## Earnings History (Recent Quarters)\n```json\n{json.dumps(earnings_calendar, indent=2)}\n```")
        
        if transcript_data:
            # Include transcript but truncate if too long
            transcript_text = transcript_data.get('transcript', '')
            if len(transcript_text) > 50000:
                transcript_text = transcript_text[:50000] + "\n\n[TRANSCRIPT TRUNCATED]"
            transcript_copy = {**transcript_data, 'transcript': transcript_text}
            context_parts.append(f"## Earnings Call Transcript\n```json\n{json.dumps(transcript_copy, indent=2)}\n```")
        
        context = "\n\n".join(context_parts)
        
        prompt = f"""You are a ruthlessly objective public markets analyst. Analyze {ticker} using the data provided below.

Cut through PR fluff and management spin. Focus on what actually matters for investment decisions.

{context}

---

## IMPORTANT: USE WEB SEARCH FOR CONTEXT

### 1. Comparative Analysis
Use web search to look up 3-5 comparable companies in the same industry/sector. For each comparable:
- Find their current valuation multiples (P/E, EV/Revenue, EV/EBITDA)
- Check their recent earnings performance and guidance
- Compare growth rates, margins, and market position

Use this comparative data to contextualize {ticker}'s valuation and performance. Is it trading at a premium or discount to peers? Is that justified by fundamentals?

### 2. Recent News & Developments
Search for recent news (last 30 days) about:
- {ticker} specifically: earnings reactions, analyst upgrades/downgrades, management changes, product launches, legal issues
- Industry/sector trends: regulatory changes, competitive dynamics, macro factors affecting the sector
- Any material events that could impact the investment thesis

Incorporate relevant news into your analysis. Note any information asymmetries or catalysts the market may be mispricing.

---

## ANALYTICAL FRAMEWORK

### A. LONG-TERM: Business Trajectory (Structural Signal)

1. **Core Demand Reality**: Is end-customer demand real and durable, or artificial (pricing tricks, channel stuffing, pull-forward)?

2. **Competitive Position Drift**: Is the company gaining or losing leverage? Are price increases sticking? Is differentiation widening or compressing? Listen for discounting language, feature parity talk, sales friction.

3. **Margin Structure Sustainability**: Are margins improving structurally or temporarily? Has scale leverage peaked? Are costs becoming more fixed or variable?

4. **Capital Allocation Quality**: Where is incremental capital going? Are buybacks from excess cash or leverage? Is M&A strategic or defensive?

5. **Management Truthfulness & Control**: Does management name trade-offs clearly or hide behind abstraction? Are they in control or reacting? Is messaging consistent?

6. **Long-Range Optionality**: Are new initiatives logical or narrative-driven? Is optionality funded by profits or hope?

### B. SHORT-TERM: Market Perception & Stock Dynamics

7. **Expectation Gap**: What did the market expect vs what happened? Was guidance conservative or aggressive?

8. **Narrative Inflection**: Did the dominant story change? Are analysts forced to update their mental model?

9. **Forward Visibility**: Is management more or less certain about the next 2-3 quarters?

10. **Guidance Credibility**: Is guidance achievable or dependent on hope, back-half weighting, macro improvement?

11. **Management Language Drift**: What topics were dropped? What metrics are no longer emphasized? New qualifiers and hedges?

---

## YOUR OUTPUT (respond in valid JSON only)

Respond with ONLY a JSON object in this exact format:
{{
  "ticker": "{ticker}",
  "company_name": "<company name>",
  "analysis_date": "{datetime.now().strftime('%Y-%m-%d')}",
  "buy_score": <1-5 integer: 1=strong sell, 2=sell, 3=hold, 4=buy, 5=strong buy>,
  "buy_score_rationale": "<one sentence explaining the score>",
  "long_term_outlook": {{
    "rating": "<bullish|neutral|bearish>",
    "thesis": "<2-3 sentences on structural business trajectory>",
    "key_factors": ["<factor 1>", "<factor 2>", "<factor 3>"]
  }},
  "short_term_outlook": {{
    "rating": "<bullish|neutral|bearish>",
    "thesis": "<2-3 sentences on near-term stock dynamics>",
    "catalyst_timeline": "<expected timeframe for next major move>"
  }},
  "comparables": [
    {{"ticker": "<TICKER>", "relationship": "<why comparable>", "valuation_vs_target": "<premium|discount|inline>", "key_metric_comparison": "<e.g. 'trades at 25x P/E vs target's 18x'>"}},
    {{"ticker": "<TICKER>", "relationship": "<why comparable>", "valuation_vs_target": "<premium|discount|inline>", "key_metric_comparison": "<comparison>"}},
    {{"ticker": "<TICKER>", "relationship": "<why comparable>", "valuation_vs_target": "<premium|discount|inline>", "key_metric_comparison": "<comparison>"}}
  ],
  "relative_valuation": {{
    "vs_peers": "<undervalued|fairly_valued|overvalued>",
    "rationale": "<2-3 sentences explaining valuation relative to comparable companies>",
    "key_multiples": {{"target_pe": <number or null>, "peer_avg_pe": <number or null>, "target_ev_revenue": <number or null>, "peer_avg_ev_revenue": <number or null>}}
  }},
  "recent_news": {{
    "company_news": ["<significant recent development 1>", "<development 2>"],
    "industry_news": ["<relevant sector trend or news 1>", "<trend 2>"],
    "sentiment": "<positive|neutral|negative>",
    "news_impact": "<how recent news affects the investment thesis>"
  }},
  "headwinds": [
    {{"risk": "<specific risk>", "severity": "<high|medium|low>", "timeframe": "<near-term|medium-term|long-term>"}},
    {{"risk": "<specific risk>", "severity": "<high|medium|low>", "timeframe": "<near-term|medium-term|long-term>"}}
  ],
  "tailwinds": [
    {{"driver": "<growth driver>", "impact": "<high|medium|low>", "timeframe": "<near-term|medium-term|long-term>"}},
    {{"driver": "<growth driver>", "impact": "<high|medium|low>", "timeframe": "<near-term|medium-term|long-term>"}}
  ],
  "management_credibility": {{
    "score": <1-5 integer>,
    "notes": "<key observations about management tone and truthfulness>"
  }},
  "summary": "<3-4 sentence executive summary answering: Is the business structurally better/worse/unchanged? Did management gain/lose credibility? What must be true for this to work?>"
}}

Be specific and direct. No hedge words. State your conviction clearly."""

        try:
            print(f"{Fore.CYAN}Analyzing with AI...{Style.RESET_ALL}")
            
            # Use streaming to show progress
            response_text = ""
            search_count = 0
            thinking_shown = False
            generating_shown = False
            char_count = 0
            
            with client.responses.stream(
                model="gpt-5.2",
                tools=[{"type": "web_search"}],
                input=prompt
            ) as stream:
                for event in stream:
                    event_type = event.type
                    
                    # Debug: set ROB_DEBUG=1 to see event types (not text deltas - too noisy)
                    if os.getenv('ROB_DEBUG') and event_type != "response.output_text.delta":
                        print(f"  {Fore.WHITE}[DEBUG] {event_type}{Style.RESET_ALL}")
                    
                    # Show web search activity
                    if "web_search" in event_type:
                        if "in_progress" in event_type or "searching" in event_type or "created" in event_type:
                            search_count += 1
                            # Try various ways to get the query
                            query = None
                            for attr in ['query', 'search_query', 'q', 'text', 'input']:
                                query = getattr(event, attr, None)
                                if query:
                                    break
                            # Also check if event has a data/item attribute
                            if not query and hasattr(event, 'item'):
                                item = event.item
                                for attr in ['query', 'search_query', 'q']:
                                    query = getattr(item, attr, None)
                                    if query:
                                        break
                            if query:
                                print(f"  {Fore.YELLOW}🔍 Web search #{search_count}: {str(query)[:70]}{Style.RESET_ALL}")
                            else:
                                print(f"  {Fore.YELLOW}🔍 Web search #{search_count}...{Style.RESET_ALL}")
                        elif "completed" in event_type or "done" in event_type:
                            print(f"  {Fore.GREEN}✓ Search complete{Style.RESET_ALL}")
                    
                    # Show thinking/reasoning activity
                    elif "reasoning" in event_type or "thinking" in event_type:
                        if not thinking_shown:
                            print(f"  {Fore.MAGENTA}🧠 Thinking...{Style.RESET_ALL}", end="", flush=True)
                            thinking_shown = True
                        else:
                            # Show progress dots
                            print(f"{Fore.MAGENTA}.{Style.RESET_ALL}", end="", flush=True)
                    
                    # Show text generation progress - stream the actual text!
                    elif event_type == "response.output_text.delta":
                        delta = getattr(event, 'delta', '')
                        response_text += delta
                        char_count += len(delta)
                        
                        if not generating_shown:
                            if thinking_shown:
                                print()  # newline after thinking dots
                            print(f"\n  {Fore.CYAN}📝 Generating analysis:{Style.RESET_ALL}\n")
                            generating_shown = True
                        
                        # Stream the actual text as it comes in
                        print(f"{Fore.WHITE}{delta}{Style.RESET_ALL}", end="", flush=True)
                    
                    elif event_type == "response.completed":
                        # Clear entire screen and show completion
                        print("\033[2J\033[H", end="")  # Clear screen, move to top
                        print(f"\n  {Fore.GREEN}✓ Analysis complete ({char_count:,} chars){Style.RESET_ALL}\n")
            
            # If streaming didn't work, try getting from final response
            if not response_text:
                response_text = stream.get_final_response().output_text
            
            # Parse JSON from response
            # Find JSON in the response (it might have markdown code blocks)
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                analysis = json.loads(json_str)
                return analysis
            else:
                print(f"{Fore.RED}Could not parse AI response as JSON{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Response preview: {response_text[:500]}...{Style.RESET_ALL}")
                return None
                
        except json.JSONDecodeError as e:
            print(f"{Fore.RED}Error parsing AI response: {e}{Style.RESET_ALL}")
            return None
        except Exception as e:
            print(f"{Fore.RED}Error calling OpenAI: {e}{Style.RESET_ALL}")
            return None
    
    def display_analysis(self, analysis: Dict, interactive: bool = True):
        """Display the AI analysis - compact summary with interactive drill-down"""
        ticker = analysis.get('ticker', 'N/A')
        
        # Always show compact summary first
        self._display_compact_summary(analysis)
        
        # If interactive, show menu to drill down
        if interactive:
            self._interactive_analysis_menu(analysis)
    
    def _display_compact_summary(self, analysis: Dict):
        """Display a compact one-screen summary"""
        ticker = analysis.get('ticker', 'N/A')
        
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}         {ticker} ANALYSIS SUMMARY{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        
        # Buy Score - big and prominent
        score = analysis.get('buy_score', 0)
        score_colors = {1: Fore.RED, 2: Fore.RED, 3: Fore.YELLOW, 4: Fore.GREEN, 5: Fore.GREEN}
        score_labels = {1: 'STRONG SELL', 2: 'SELL', 3: 'HOLD', 4: 'BUY', 5: 'STRONG BUY'}
        score_color = score_colors.get(score, Fore.WHITE)
        print(f"\n  {Fore.WHITE}Rating:{Style.RESET_ALL} {score_color}{'★' * score}{'☆' * (5-score)} {score_labels.get(score, 'N/A')}{Style.RESET_ALL}")
        
        # Outlook row
        lt = analysis.get('long_term_outlook', {})
        st = analysis.get('short_term_outlook', {})
        lt_rating = lt.get('rating', 'N/A')
        st_rating = st.get('rating', 'N/A')
        lt_color = {'bullish': Fore.GREEN, 'neutral': Fore.YELLOW, 'bearish': Fore.RED}.get(lt_rating, Fore.WHITE)
        st_color = {'bullish': Fore.GREEN, 'neutral': Fore.YELLOW, 'bearish': Fore.RED}.get(st_rating, Fore.WHITE)
        print(f"  {Fore.WHITE}Outlook:{Style.RESET_ALL} Long-term {lt_color}{lt_rating.upper()}{Style.RESET_ALL} | Short-term {st_color}{st_rating.upper()}{Style.RESET_ALL}")
        
        # Valuation
        rel_val = analysis.get('relative_valuation', {})
        vs_peers = rel_val.get('vs_peers', 'N/A')
        val_color = {'undervalued': Fore.GREEN, 'fairly_valued': Fore.YELLOW, 'overvalued': Fore.RED}.get(vs_peers, Fore.WHITE)
        print(f"  {Fore.WHITE}Valuation:{Style.RESET_ALL} {val_color}{vs_peers.upper().replace('_', ' ')}{Style.RESET_ALL} vs peers")
        
        # News sentiment
        news = analysis.get('recent_news', {})
        sentiment = news.get('sentiment', 'N/A')
        sent_color = {'positive': Fore.GREEN, 'neutral': Fore.YELLOW, 'negative': Fore.RED}.get(sentiment, Fore.WHITE)
        print(f"  {Fore.WHITE}News:{Style.RESET_ALL} {sent_color}{sentiment.upper()}{Style.RESET_ALL}")
        
        # Management
        mgmt = analysis.get('management_credibility', {})
        mgmt_score = mgmt.get('score', 0)
        mgmt_color = {1: Fore.RED, 2: Fore.RED, 3: Fore.YELLOW, 4: Fore.GREEN, 5: Fore.GREEN}.get(mgmt_score, Fore.WHITE)
        print(f"  {Fore.WHITE}Management:{Style.RESET_ALL} {mgmt_color}{mgmt_score}/5{Style.RESET_ALL}")
        
        # Key risks/catalysts (one-liner each)
        headwinds = analysis.get('headwinds', [])
        tailwinds = analysis.get('tailwinds', [])
        if headwinds:
            top_risk = headwinds[0]
            print(f"  {Fore.RED}⚠ Top Risk:{Style.RESET_ALL} {top_risk.get('risk', '')[:60]}...")
        if tailwinds:
            top_catalyst = tailwinds[0]
            print(f"  {Fore.GREEN}✦ Top Catalyst:{Style.RESET_ALL} {top_catalyst.get('driver', '')[:60]}...")
        
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    
    def _interactive_analysis_menu(self, analysis: Dict):
        """Interactive arrow-key menu to explore analysis sections"""
        sections = [
            ('📊 Summary & Rationale', self._show_summary),
            ('📈 Long-term Outlook', self._show_long_term),
            ('📉 Short-term Outlook', self._show_short_term),
            ('🏢 Comparables & Valuation', self._show_comparables),
            ('📰 Recent News', self._show_news),
            ('⚠️  Risks & Headwinds', self._show_headwinds),
            ('🚀 Growth & Tailwinds', self._show_tailwinds),
            ('👔 Management Assessment', self._show_management),
            ('📋 Show All', self._show_all),
            ('✓ Done', None),
        ]
        
        menu_items = [label for label, _ in sections]
        
        # Build title with buy score
        ticker = analysis.get('ticker', '?')
        score = analysis.get('buy_score', 0)
        score_labels = {1: 'STRONG SELL', 2: 'SELL', 3: 'HOLD', 4: 'BUY', 5: 'STRONG BUY'}
        stars = '★' * score + '☆' * (5 - score)
        rationale = analysis.get('buy_score_rationale', '')[:80]
        
        title = f"\n  {ticker}  {stars} {score_labels.get(score, '?')}\n  {rationale}...\n\n  ↑↓ Navigate  │  Enter Select  │  q Quit\n"
        
        while True:
            terminal_menu = TerminalMenu(
                menu_items,
                title=title,
                menu_cursor="▶ ",
                menu_cursor_style=("fg_cyan", "bold"),
                menu_highlight_style=("fg_cyan", "bold"),
                cycle_cursor=True,
                clear_screen=True,
            )
            
            choice_idx = terminal_menu.show()
            
            if choice_idx is None or choice_idx == len(sections) - 1:  # None = q/Esc, last = Done
                break
            
            # Show the selected section
            _, handler = sections[choice_idx]
            if handler:
                handler(analysis)
                input(f"\n{Fore.CYAN}Press Enter to continue...{Style.RESET_ALL}")
    
    def _wrap_text(self, text: str, width: int = 52, indent: str = "  ") -> str:
        """Wrap text to specified width with indentation"""
        import textwrap
        if not text:
            return ""
        wrapped = textwrap.fill(text, width=width, initial_indent=indent, subsequent_indent=indent)
        return wrapped
    
    def _display_width(self, text: str) -> int:
        """Calculate display width accounting for ANSI codes and wide characters (emojis)"""
        import re
        import unicodedata
        # Strip ANSI codes
        ansi_escape = re.compile(r'\x1B\[[0-9;]*[mK]')
        visible = ansi_escape.sub('', text)
        # Count display width (emojis and wide chars are 2 columns)
        width = 0
        for char in visible:
            if unicodedata.east_asian_width(char) in ('W', 'F'):
                width += 2
            elif ord(char) > 0x1F000:  # Emoji range
                width += 2
            else:
                width += 1
        return width
    
    def _print_wrapped_line(self, text: str, width: int = 56):
        """Print a line padded to fit in a box of given width"""
        visible_width = self._display_width(text)
        padding = width - visible_width
        if padding > 0:
            print(f"{Fore.CYAN}│{Style.RESET_ALL}{text}{' ' * padding}{Fore.CYAN}│{Style.RESET_ALL}")
        else:
            print(f"{Fore.CYAN}│{Style.RESET_ALL}{text}{Fore.CYAN}│{Style.RESET_ALL}")
    
    def _print_section(self, title: str, content: str, title_color=None):
        """Print a nicely formatted section"""
        color = title_color or Fore.WHITE
        print(f"\n{Fore.CYAN}┌{'─'*56}┐{Style.RESET_ALL}")
        print(f"{Fore.CYAN}│{Style.RESET_ALL} {color}{title}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}├{'─'*56}┤{Style.RESET_ALL}")
        if content:
            wrapped = self._wrap_text(content, width=54, indent="  ")
            for line in wrapped.split('\n'):
                print(f"{Fore.CYAN}│{Style.RESET_ALL}{line:<57}{Fore.CYAN}│{Style.RESET_ALL}")
        print(f"{Fore.CYAN}└{'─'*56}┘{Style.RESET_ALL}")
    
    def _show_summary(self, analysis: Dict):
        """Show summary and rationale"""
        score = analysis.get('buy_score', 0)
        score_colors = {1: Fore.RED, 2: Fore.RED, 3: Fore.YELLOW, 4: Fore.GREEN, 5: Fore.GREEN}
        score_color = score_colors.get(score, Fore.WHITE)
        stars = '★' * score + '☆' * (5 - score)
        
        print(f"\n{Fore.CYAN}┌{'─'*56}┐{Style.RESET_ALL}")
        self._print_wrapped_line(f" {Fore.WHITE}BUY SCORE:{Style.RESET_ALL} {score_color}{stars} {score}/5{Style.RESET_ALL}")
        print(f"{Fore.CYAN}├{'─'*56}┤{Style.RESET_ALL}")
        
        rationale = analysis.get('buy_score_rationale', '')
        if rationale:
            for line in self._wrap_text(rationale, 52).split('\n'):
                self._print_wrapped_line(line)
        
        print(f"{Fore.CYAN}├{'─'*56}┤{Style.RESET_ALL}")
        self._print_wrapped_line(f" {Fore.WHITE}SUMMARY{Style.RESET_ALL}")
        print(f"{Fore.CYAN}├{'─'*56}┤{Style.RESET_ALL}")
        
        summary = analysis.get('summary', '')
        if summary:
            for line in self._wrap_text(summary, 52).split('\n'):
                self._print_wrapped_line(line)
        
        print(f"{Fore.CYAN}└{'─'*56}┘{Style.RESET_ALL}")
    
    def _show_long_term(self, analysis: Dict):
        """Show long-term outlook"""
        lt = analysis.get('long_term_outlook', {})
        lt_rating = lt.get('rating', 'N/A')
        lt_color = {'bullish': Fore.GREEN, 'neutral': Fore.YELLOW, 'bearish': Fore.RED}.get(lt_rating, Fore.WHITE)
        
        print(f"\n{Fore.CYAN}┌{'─'*56}┐{Style.RESET_ALL}")
        self._print_wrapped_line(f" {Fore.WHITE}LONG-TERM OUTLOOK:{Style.RESET_ALL} {lt_color}{lt_rating.upper()}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}├{'─'*56}┤{Style.RESET_ALL}")
        
        thesis = lt.get('thesis', '')
        if thesis:
            for line in self._wrap_text(thesis, 52).split('\n'):
                self._print_wrapped_line(line)
        
        if lt.get('key_factors'):
            print(f"{Fore.CYAN}├{'─'*56}┤{Style.RESET_ALL}")
            self._print_wrapped_line(f" {Fore.WHITE}Key Factors:{Style.RESET_ALL}")
            for factor in lt['key_factors']:
                for line in self._wrap_text(f"• {factor}", 50, indent="   ").split('\n'):
                    self._print_wrapped_line(line)
        
        print(f"{Fore.CYAN}└{'─'*56}┘{Style.RESET_ALL}")
    
    def _show_short_term(self, analysis: Dict):
        """Show short-term outlook"""
        st = analysis.get('short_term_outlook', {})
        st_rating = st.get('rating', 'N/A')
        st_color = {'bullish': Fore.GREEN, 'neutral': Fore.YELLOW, 'bearish': Fore.RED}.get(st_rating, Fore.WHITE)
        
        print(f"\n{Fore.CYAN}┌{'─'*56}┐{Style.RESET_ALL}")
        self._print_wrapped_line(f" {Fore.WHITE}SHORT-TERM OUTLOOK:{Style.RESET_ALL} {st_color}{st_rating.upper()}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}├{'─'*56}┤{Style.RESET_ALL}")
        
        thesis = st.get('thesis', '')
        if thesis:
            for line in self._wrap_text(thesis, 52).split('\n'):
                self._print_wrapped_line(line)
        
        catalyst = st.get('catalyst_timeline', '')
        if catalyst:
            print(f"{Fore.CYAN}├{'─'*56}┤{Style.RESET_ALL}")
            self._print_wrapped_line(f" {Fore.YELLOW}Catalyst Timeline:{Style.RESET_ALL}")
            for line in self._wrap_text(catalyst, 52).split('\n'):
                self._print_wrapped_line(line)
        
        print(f"{Fore.CYAN}└{'─'*56}┘{Style.RESET_ALL}")
    
    def _show_comparables(self, analysis: Dict):
        """Show comparables and valuation"""
        rel_val = analysis.get('relative_valuation', {})
        vs_peers = rel_val.get('vs_peers', 'N/A') if rel_val else 'N/A'
        val_color = {'undervalued': Fore.GREEN, 'fairly_valued': Fore.YELLOW, 'overvalued': Fore.RED}.get(vs_peers, Fore.WHITE)
        val_icon = {'undervalued': '↓', 'fairly_valued': '→', 'overvalued': '↑'}.get(vs_peers, '•')
        
        print(f"\n{Fore.CYAN}┌{'─'*56}┐{Style.RESET_ALL}")
        self._print_wrapped_line(f" {Fore.WHITE}🏢 VALUATION:{Style.RESET_ALL} {val_color}{val_icon} {vs_peers.upper().replace('_', ' ')}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}├{'─'*56}┤{Style.RESET_ALL}")
        
        if rel_val:
            rationale = rel_val.get('rationale', '')
            if rationale:
                for line in self._wrap_text(rationale, 52).split('\n'):
                    self._print_wrapped_line(line)
            
            multiples = rel_val.get('key_multiples', {})
            if multiples:
                print(f"{Fore.CYAN}├{'─'*56}┤{Style.RESET_ALL}")
                self._print_wrapped_line(f" {Fore.WHITE}Multiples:{Style.RESET_ALL}")
                if multiples.get('target_pe'):
                    self._print_wrapped_line(f"  P/E: {multiples['target_pe']} vs peers {multiples.get('peer_avg_pe', 'N/A')}")
                if multiples.get('target_ev_revenue'):
                    self._print_wrapped_line(f"  EV/Rev: {multiples['target_ev_revenue']}x vs peers {multiples.get('peer_avg_ev_revenue', 'N/A')}x")
        
        # Comparables
        comps = analysis.get('comparables', [])
        if comps:
            print(f"{Fore.CYAN}├{'─'*56}┤{Style.RESET_ALL}")
            self._print_wrapped_line(f" {Fore.WHITE}Comparable Companies:{Style.RESET_ALL}")
            for comp in comps:
                ticker = comp.get('ticker', 'N/A')
                relationship = comp.get('relationship', '')
                metric = comp.get('key_metric_comparison', '')
                val_vs = comp.get('valuation_vs_target', '')
                c_color = {'premium': Fore.RED, 'discount': Fore.GREEN, 'inline': Fore.YELLOW}.get(val_vs, Fore.WHITE)
                
                self._print_wrapped_line(f"  {Fore.YELLOW}{ticker}{Style.RESET_ALL}")
                if relationship:
                    for line in self._wrap_text(relationship, 48, indent="    ").split('\n'):
                        self._print_wrapped_line(line)
                if metric:
                    self._print_wrapped_line(f"    {c_color}{metric}{Style.RESET_ALL}")
        
        print(f"{Fore.CYAN}└{'─'*56}┘{Style.RESET_ALL}")
    
    def _show_news(self, analysis: Dict):
        """Show recent news"""
        news = analysis.get('recent_news', {})
        sentiment = news.get('sentiment', 'N/A')
        sent_color = {'positive': Fore.GREEN, 'neutral': Fore.YELLOW, 'negative': Fore.RED}.get(sentiment, Fore.WHITE)
        sent_icon = {'positive': '↑', 'neutral': '→', 'negative': '↓'}.get(sentiment, '•')
        
        print(f"\n{Fore.CYAN}┌{'─'*56}┐{Style.RESET_ALL}")
        self._print_wrapped_line(f" {Fore.WHITE}📰 RECENT NEWS:{Style.RESET_ALL} {sent_color}{sent_icon} {sentiment.upper()}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}├{'─'*56}┤{Style.RESET_ALL}")
        
        if news.get('company_news'):
            self._print_wrapped_line(f" {Fore.WHITE}Company:{Style.RESET_ALL}")
            for item in news['company_news']:
                for line in self._wrap_text(f"• {item}", 52, indent="   ").split('\n'):
                    self._print_wrapped_line(line)
        
        if news.get('industry_news'):
            self._print_wrapped_line(f" {Fore.WHITE}Industry:{Style.RESET_ALL}")
            for item in news['industry_news']:
                for line in self._wrap_text(f"• {item}", 52, indent="   ").split('\n'):
                    self._print_wrapped_line(line)
        
        if news.get('news_impact'):
            print(f"{Fore.CYAN}├{'─'*56}┤{Style.RESET_ALL}")
            self._print_wrapped_line(f" {Fore.YELLOW}Impact:{Style.RESET_ALL}")
            for line in self._wrap_text(news['news_impact'], 52, indent="   ").split('\n'):
                self._print_wrapped_line(line)
        
        print(f"{Fore.CYAN}└{'─'*56}┘{Style.RESET_ALL}")
    
    def _show_headwinds(self, analysis: Dict):
        """Show risks and headwinds"""
        headwinds = analysis.get('headwinds', [])
        
        print(f"\n{Fore.CYAN}┌{'─'*56}┐{Style.RESET_ALL}")
        self._print_wrapped_line(f" {Fore.RED}⚠ HEADWINDS / RISKS{Style.RESET_ALL}")
        print(f"{Fore.CYAN}├{'─'*56}┤{Style.RESET_ALL}")
        
        if headwinds:
            for hw in headwinds:
                severity = hw.get('severity', '')
                severity_color = {'high': Fore.RED, 'medium': Fore.YELLOW, 'low': Fore.GREEN}.get(severity, Fore.WHITE)
                severity_icon = {'high': '●', 'medium': '◐', 'low': '○'}.get(severity, '•')
                risk_text = hw.get('risk', '')
                timeframe = hw.get('timeframe', '')
                
                self._print_wrapped_line(f" {severity_color}{severity_icon} [{severity.upper()}]{Style.RESET_ALL}")
                for line in self._wrap_text(risk_text, 50, indent="   ").split('\n'):
                    self._print_wrapped_line(line)
                if timeframe:
                    self._print_wrapped_line(f"   {Fore.WHITE}Timeframe:{Style.RESET_ALL} {timeframe}")
        else:
            self._print_wrapped_line("  No significant headwinds identified.")
        
        print(f"{Fore.CYAN}└{'─'*56}┘{Style.RESET_ALL}")
    
    def _show_tailwinds(self, analysis: Dict):
        """Show growth drivers and tailwinds"""
        tailwinds = analysis.get('tailwinds', [])
        
        print(f"\n{Fore.CYAN}┌{'─'*56}┐{Style.RESET_ALL}")
        self._print_wrapped_line(f" {Fore.GREEN}🚀 TAILWINDS / GROWTH DRIVERS{Style.RESET_ALL}")
        print(f"{Fore.CYAN}├{'─'*56}┤{Style.RESET_ALL}")
        
        if tailwinds:
            for tw in tailwinds:
                impact = tw.get('impact', '')
                impact_color = {'high': Fore.GREEN, 'medium': Fore.YELLOW, 'low': Fore.WHITE}.get(impact, Fore.WHITE)
                impact_icon = {'high': '●', 'medium': '◐', 'low': '○'}.get(impact, '•')
                driver_text = tw.get('driver', '')
                timeframe = tw.get('timeframe', '')
                
                self._print_wrapped_line(f" {impact_color}{impact_icon} [{impact.upper()}]{Style.RESET_ALL}")
                for line in self._wrap_text(driver_text, 50, indent="   ").split('\n'):
                    self._print_wrapped_line(line)
                if timeframe:
                    self._print_wrapped_line(f"   {Fore.WHITE}Timeframe:{Style.RESET_ALL} {timeframe}")
        else:
            self._print_wrapped_line("  No significant tailwinds identified.")
        
        print(f"{Fore.CYAN}└{'─'*56}┘{Style.RESET_ALL}")
    
    def _show_management(self, analysis: Dict):
        """Show management assessment"""
        mgmt = analysis.get('management_credibility', {})
        mgmt_score = mgmt.get('score', 0)
        mgmt_color = {1: Fore.RED, 2: Fore.RED, 3: Fore.YELLOW, 4: Fore.GREEN, 5: Fore.GREEN}.get(mgmt_score, Fore.WHITE)
        stars = '★' * mgmt_score + '☆' * (5 - mgmt_score)
        
        print(f"\n{Fore.CYAN}┌{'─'*56}┐{Style.RESET_ALL}")
        self._print_wrapped_line(f" {Fore.WHITE}👔 MANAGEMENT:{Style.RESET_ALL} {mgmt_color}{stars} {mgmt_score}/5{Style.RESET_ALL}")
        print(f"{Fore.CYAN}├{'─'*56}┤{Style.RESET_ALL}")
        
        notes = mgmt.get('notes', '')
        if notes:
            for line in self._wrap_text(notes, 52).split('\n'):
                self._print_wrapped_line(line)
        
        print(f"{Fore.CYAN}└{'─'*56}┘{Style.RESET_ALL}")
    
    def _show_all(self, analysis: Dict):
        """Show the full report (all sections)"""
        self._show_summary(analysis)
        self._show_long_term(analysis)
        self._show_short_term(analysis)
        self._show_comparables(analysis)
        self._show_news(analysis)
        self._show_headwinds(analysis)
        self._show_tailwinds(analysis)
        self._show_management(analysis)
    
    def analyze(self, ticker: str, force_refresh: bool = False) -> bool:
        """
        Fetch and save latest ticker, earnings, and transcript data for a ticker.
        Only keeps the most recent data.
        Returns True if any data was saved.
        
        If an analysis already exists for the latest quarter, displays it without re-fetching.
        Use force_refresh=True to force a new analysis.
        """
        ticker = ticker.upper()
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}         Analyzing {ticker}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
        
        # Check for existing analysis (unless force refresh)
        need_fresh_data = force_refresh
        
        if not force_refresh:
            print(f"{Fore.CYAN}Checking for existing analysis...{Style.RESET_ALL}")
            is_current, existing_analysis, latest_quarter = self.is_analysis_current(ticker)
            
            if is_current and existing_analysis:
                year = existing_analysis.get('_earnings_year', '?')
                quarter = existing_analysis.get('_earnings_quarter', '?')
                print(f"{Fore.GREEN}✓ Analysis for {year} Q{quarter} is current{Style.RESET_ALL}")
                self.display_analysis(existing_analysis)
                return True
            elif existing_analysis and latest_quarter:
                old_year = existing_analysis.get('_earnings_year', '?')
                old_quarter = existing_analysis.get('_earnings_quarter', '?')
                print(f"{Fore.YELLOW}New data available: {latest_quarter[0]} Q{latest_quarter[1]} (have {old_year} Q{old_quarter}){Style.RESET_ALL}")
                need_fresh_data = True  # Must fetch new data!
            elif existing_analysis:
                print(f"{Fore.YELLOW}Have analysis but can't verify if current, refreshing...{Style.RESET_ALL}")
                need_fresh_data = True
            else:
                print(f"{Fore.YELLOW}No existing analysis found{Style.RESET_ALL}")
                need_fresh_data = True
        
        # Check if we have saved data we can reuse (only if not needing fresh data)
        saved_ticker, saved_transcript, saved_calendar = self.load_existing_data(ticker)
        
        if saved_ticker and saved_transcript and not need_fresh_data:
            # We have all data cached AND it's current
            # Check if we also have a cached analysis we can use
            existing_analysis = self.load_existing_analysis(ticker)
            if existing_analysis:
                print(f"{Fore.GREEN}✓ Using cached analysis{Style.RESET_ALL}")
                self.display_analysis(existing_analysis)
                return True
            
            # No cached analysis, but have cached data - will run AI
            print(f"{Fore.GREEN}✓ Using cached data (ticker, transcript, earnings history){Style.RESET_ALL}")
            ticker_data = saved_ticker
            transcript_data = saved_transcript
            earnings_calendar = saved_calendar
            
            # Get quarter from cached transcript
            year = saved_transcript.get('year')
            quarter = saved_transcript.get('quarter')
            earnings_quarter = (int(year), int(quarter)) if year and quarter else None
            
            saved_any = True
        else:
            # Need to fetch fresh data
            saved_any = False
            earnings_quarter = None
            ticker_data = None
            transcript_data = None
            earnings_calendar = None
            transcript_year = None
            transcript_quarter = None
            
            # Fetch ticker/price data
            print(f"\n{Fore.CYAN}Fetching ticker data for {ticker}...{Style.RESET_ALL}")
            ticker_data = self.fetch_ticker_data(ticker)
            
            if ticker_data:
                try:
                    filepath = self.save_ticker_data(ticker, ticker_data)
                    print(f"{Fore.GREEN}✓ Saved ticker data: {filepath}{Style.RESET_ALL}")
                    saved_any = True
                    
                    # Display summary
                    name = ticker_data.get('name')
                    price = ticker_data.get('latest_price')
                    market_cap = ticker_data.get('latest_market_cap')
                    exchange = ticker_data.get('exchange')
                    
                    if name:
                        print(f"  Company: {name}")
                    if price:
                        print(f"  Price: ${price:,.2f}")
                    if market_cap:
                        print(f"  Market Cap: ${market_cap:,.0f}")
                    if exchange:
                        print(f"  Exchange: {exchange}")
                except Exception as e:
                    print(f"{Fore.RED}Error saving ticker data: {e}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}No ticker data returned{Style.RESET_ALL}")
            
            # Fetch latest transcript FIRST (to get the quarter for earnings)
            print(f"\n{Fore.CYAN}Fetching latest transcript for {ticker}...{Style.RESET_ALL}")
            transcript_data = self.fetch_transcript(ticker)
            
            if transcript_data:
                try:
                    filepath = self.save_transcript(ticker, transcript_data)
                    print(f"{Fore.GREEN}✓ Saved transcript: {filepath}{Style.RESET_ALL}")
                    saved_any = True
                    
                    # Extract year/quarter from transcript for earnings fetch
                    transcript_year = transcript_data.get('year')
                    transcript_quarter = transcript_data.get('quarter')
                    if transcript_year:
                        transcript_year = int(transcript_year)
                    if transcript_quarter:
                        transcript_quarter = int(transcript_quarter)
                    
                    # Display summary
                    transcript_text = transcript_data.get('transcript', '')
                    if transcript_text:
                        word_count = len(transcript_text.split())
                        print(f"  Date: {transcript_data.get('date', 'N/A')}")
                        print(f"  Quarter: {transcript_year} Q{transcript_quarter}")
                        print(f"  Word count: {word_count:,}")
                    # Use transcript quarter for analysis cache
                    if transcript_year and transcript_quarter:
                        earnings_quarter = (transcript_year, transcript_quarter)
                except Exception as e:
                    print(f"{Fore.RED}Error saving transcript: {e}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}No transcript data returned{Style.RESET_ALL}")
            
            # Fetch earnings calendar (historical EPS/revenue for recent quarters)
            print(f"\n{Fore.CYAN}Fetching earnings history for {ticker}...{Style.RESET_ALL}")
            earnings_calendar = self.fetch_earnings_calendar(ticker)
            
            if earnings_calendar:
                try:
                    filepath = self.save_earnings_calendar(ticker, earnings_calendar)
                    print(f"{Fore.GREEN}✓ Saved earnings history: {filepath}{Style.RESET_ALL}")
                    saved_any = True
                    
                    # Display summary
                    print(f"  Quarters: {len(earnings_calendar)}")
                    for entry in earnings_calendar[:3]:
                        date = entry.get('date', 'N/A')
                        actual_eps = entry.get('actual_eps')
                        actual_rev = entry.get('actual_revenue')
                        if actual_eps and actual_rev:
                            print(f"  {date}: EPS ${actual_eps:.2f}, Revenue ${actual_rev/1e9:.1f}B")
                except Exception as e:
                    print(f"{Fore.RED}Error saving earnings calendar: {e}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}No earnings history returned{Style.RESET_ALL}")
        
        # Data collection summary
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        ticker_dir = self.get_ticker_dir(ticker)
        print(f"{Fore.GREEN}Data directory: {ticker_dir}{Style.RESET_ALL}")
        
        if saved_any:
            print(f"{Fore.GREEN}✓ Data collection complete{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}Data collection complete - no data saved{Style.RESET_ALL}")
        
        # Run AI analysis if we have data
        if saved_any and (ticker_data or transcript_data):
            print(f"\n{Fore.CYAN}Running AI analysis...{Style.RESET_ALL}")
            analysis = self.analyze_with_ai(ticker, ticker_data, transcript_data, earnings_calendar)
            
            if analysis:
                # Save the analysis with quarter info for cache validation
                analysis_path = self.save_analysis(ticker, analysis, earnings_quarter)
                print(f"{Fore.GREEN}✓ Saved analysis: {analysis_path}{Style.RESET_ALL}")
                
                # Display the analysis
                self.display_analysis(analysis)
            else:
                print(f"{Fore.YELLOW}AI analysis could not be completed{Style.RESET_ALL}")
        
        return saved_any


@click.group()
@click.version_option(version="1.0.0", prog_name="rob")
def cli():
    """Robinhood Position Manager - Manage your portfolio positions in bulk"""
    pass

@cli.command()
@click.option('--action', '-a', type=click.Choice(['increase', 'decrease']), required=True,
              help='Action to perform on positions')
@click.option('--percentage', '-p', type=float, required=True,
              help='Percentage to increase or decrease positions by')
@click.option('--confirm/--no-confirm', default=True,
              help='Auto-confirm the operation without prompting')
@click.option('--dry-run', is_flag=True,
              help='Show what would be done without executing trades')
def adjust(action, percentage, confirm, dry_run):
    """Adjust positions by a percentage"""
    if not (0 < percentage <= 100):
        click.echo(f"{Fore.RED}Error: Percentage must be between 0 and 100{Style.RESET_ALL}")
        return

    manager = RobinhoodPositionManager()

    try:
        # Header
        click.echo(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        click.echo(f"{Fore.CYAN}         Robinhood Position Manager{Style.RESET_ALL}")
        click.echo(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

        # Authenticate
        if not manager.authenticate():
            sys.exit(1)

        # Fetch and display portfolio summary
        click.echo(f"{Fore.CYAN}Fetching portfolio information...{Style.RESET_ALL}")
        portfolio_value, available_cash, positions_value = manager.get_portfolio_summary()

        click.echo(f"\n{Fore.WHITE}Portfolio Summary:{Style.RESET_ALL}")
        click.echo(f"  {Fore.GREEN}Total Portfolio Value: ${portfolio_value:,.2f}{Style.RESET_ALL}")
        click.echo(f"  {Fore.YELLOW}Available Cash: ${available_cash:,.2f}{Style.RESET_ALL}")
        click.echo(f"  {Fore.CYAN}Positions Value: ${positions_value:,.2f}{Style.RESET_ALL}")

        # Calculate and display expected cost
        click.echo(f"\n{Fore.CYAN}Calculating expected cost...{Style.RESET_ALL}")
        expected_cost = manager.calculate_total_expected_cost(action, percentage)

        click.echo(f"\n{Fore.WHITE}Operation Summary:{Style.RESET_ALL}")
        click.echo(f"  Action: {Fore.CYAN}{action.upper()}{Style.RESET_ALL} positions by {Fore.YELLOW}{percentage}%{Style.RESET_ALL}")

        if action == 'increase':
            click.echo(f"  Expected Total Cost: {Fore.RED}${expected_cost:,.2f}{Style.RESET_ALL}")
            click.echo(f"  Available Cash: {Fore.GREEN}${available_cash:,.2f}{Style.RESET_ALL}")

            # Check if user has enough cash
            if expected_cost > available_cash:
                click.echo(f"\n{Fore.RED}❌ ERROR: Insufficient funds!{Style.RESET_ALL}")
                click.echo(f"{Fore.RED}You need ${expected_cost:,.2f} but only have ${available_cash:,.2f} available.{Style.RESET_ALL}")
                click.echo(f"{Fore.YELLOW}Try a smaller percentage or sell some positions first.{Style.RESET_ALL}")
                return
            else:
                click.echo(f"  Remaining Cash After: {Fore.GREEN}${available_cash - expected_cost:,.2f}{Style.RESET_ALL}")
        else:
            click.echo(f"  Expected Proceeds: {Fore.GREEN}${expected_cost:,.2f}{Style.RESET_ALL}")
            click.echo(f"  Cash After Selling: {Fore.GREEN}${available_cash + expected_cost:,.2f}{Style.RESET_ALL}")

        # Confirm before proceeding
        if confirm and not dry_run:
            if not click.confirm(f"\n{Fore.YELLOW}Proceed with {action}ing positions?{Style.RESET_ALL}"):
                click.echo(f"\n{Fore.YELLOW}Operation cancelled.{Style.RESET_ALL}")
                return

        if dry_run:
            click.echo(f"\n{Fore.YELLOW}DRY RUN - No trades will be executed{Style.RESET_ALL}")

        # Process positions
        manager.process_positions(action, percentage, dry_run=dry_run, auto_confirm=not confirm)

    except KeyboardInterrupt:
        click.echo(f"\n\n{Fore.YELLOW}Interrupted by user{Style.RESET_ALL}")
    except Exception as e:
        click.echo(f"\n{Fore.RED}Unexpected error: {e}{Style.RESET_ALL}")
    finally:
        manager.logout()

@cli.command()
def portfolio():
    """Show portfolio summary"""
    manager = RobinhoodPositionManager()

    try:
        # Authenticate
        if not manager.authenticate():
            sys.exit(1)

        # Fetch and display portfolio summary
        click.echo(f"{Fore.CYAN}Fetching portfolio information...{Style.RESET_ALL}")
        portfolio_value, available_cash, positions_value = manager.get_portfolio_summary()

        click.echo(f"\n{Fore.WHITE}Portfolio Summary:{Style.RESET_ALL}")
        click.echo(f"  {Fore.GREEN}Total Portfolio Value: ${portfolio_value:,.2f}{Style.RESET_ALL}")
        click.echo(f"  {Fore.YELLOW}Available Cash: ${available_cash:,.2f}{Style.RESET_ALL}")
        click.echo(f"  {Fore.CYAN}Positions Value: ${positions_value:,.2f}{Style.RESET_ALL}")

        # Show positions
        positions = manager.get_positions()
        if positions:
            click.echo(f"\n{Fore.WHITE}Current Positions:{Style.RESET_ALL}")
            for symbol, data in sorted(positions.items()):
                shares = float(data.get('quantity', 0))
                price = float(rs.stocks.get_latest_price(symbol)[0])
                value = shares * price
                click.echo(f"  {Fore.CYAN}{symbol}{Style.RESET_ALL}: {shares:.2f} shares @ ${price:.2f} = ${value:.2f}")

    except Exception as e:
        click.echo(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
    finally:
        manager.logout()

def _interactive_positions_menu(manager: RobinhoodPositionManager):
    """
    Interactive position viewer with analysis ratings.
    Takes an already-authenticated manager instance.
    """
    import threading
    import itertools
    
    # Animated spinner while loading
    stop_spinner = threading.Event()
    positions_result = [None]  # Use list to allow mutation in thread
    
    def fetch_positions():
        positions_result[0] = manager.get_positions()
        stop_spinner.set()
    
    def show_spinner():
        spinner = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
        while not stop_spinner.is_set():
            print(f"\r  {Fore.CYAN}{next(spinner)} Loading positions...{Style.RESET_ALL}", end="", flush=True)
            stop_spinner.wait(0.08)
    
    # Start fetch in background, show spinner in foreground
    fetch_thread = threading.Thread(target=fetch_positions)
    fetch_thread.start()
    show_spinner()
    fetch_thread.join()
    
    print("\r" + " " * 35 + "\r", end="")  # Clear line
    positions_data = positions_result[0]
    
    if not positions_data:
        print(f"{Fore.YELLOW}No positions found{Style.RESET_ALL}")
        return
    
    # Create analyzer to check for cached analyses
    try:
        analyzer = TickerAnalyzer()
    except ValueError:
        # API keys not configured - still show positions, just no analysis
        analyzer = None
    
    # Build position list with ratings (prices already included from build_holdings)
    position_list = []
    for symbol, data in sorted(positions_data.items()):
        shares = float(data.get('quantity', 0))
        price = float(data.get('price', 0))
        value = float(data.get('equity', 0))
        
        # Check for cached analysis
        rating_str = ""
        analysis = None
        if analyzer:
            analysis = analyzer.load_existing_analysis(symbol)
            if analysis:
                score = analysis.get('buy_score', 0)
                score_labels = {1: 'SELL', 2: 'SELL', 3: 'HOLD', 4: 'BUY', 5: 'BUY'}
                stars = '★' * score + '☆' * (5 - score)
                rating_str = f" {stars} {score_labels.get(score, '?')}"
        
        position_list.append({
            'symbol': symbol,
            'shares': shares,
            'price': price,
            'value': value,
            'rating_str': rating_str,
            'analysis': analysis
        })
    
    # Clear loading line
    print("\r" + " " * 50 + "\r", end="")
    
    # Calculate total portfolio value for percentages
    total_value = sum(pos['value'] for pos in position_list)
    
    # Sort by value descending
    position_list.sort(key=lambda x: x['value'], reverse=True)
    
    # Interactive menu loop
    while True:
        # Build menu items
        menu_items = []
        for pos in position_list:
            pct = (pos['value'] / total_value * 100) if total_value > 0 else 0
            rating_display = pos['rating_str'] if pos['rating_str'] else ""
            # Format: AAPL    $12,345    12.3%  ★★★★☆ BUY
            menu_items.append(
                f"{pos['symbol']:6}  ${pos['value']:>10,.0f}  {pct:>5.1f}%{rating_display}"
            )
        menu_items.append("─" * 40)
        menu_items.append("✓ Done")
        
        title = f"\n  {Fore.CYAN}Positions{Style.RESET_ALL} │ Select to analyze │ q Quit\n"
        
        terminal_menu = TerminalMenu(
            menu_items,
            title=title,
            menu_cursor="▶ ",
            menu_cursor_style=("fg_cyan", "bold"),
            menu_highlight_style=("fg_cyan", "bold"),
            cycle_cursor=True,
            clear_screen=False,  # Don't clear screen between selections
        )
        
        choice_idx = terminal_menu.show()
        
        # Handle exit conditions
        if choice_idx is None or choice_idx >= len(position_list):
            break
        
        # User selected a position - analyze it
        selected = position_list[choice_idx]
        symbol = selected['symbol']
        
        print(f"\n{Fore.CYAN}{'─'*60}{Style.RESET_ALL}")
        
        if selected['analysis']:
            # Show full interactive analysis menu
            analyzer.display_analysis(selected['analysis'], interactive=True)
            
            # After exiting the menu, offer to refresh
            refresh_menu = TerminalMenu(
                ["← Back to positions", "🔄 Refresh analysis"],
                title=f"\n  {symbol} Analysis\n",
                menu_cursor="▶ ",
                menu_cursor_style=("fg_cyan", "bold"),
                clear_screen=False,
            )
            if refresh_menu.show() == 1:
                print(f"\n{Fore.CYAN}Refreshing analysis for {symbol}...{Style.RESET_ALL}")
                analyzer.analyze(symbol, force_refresh=True)
                # Reload the analysis
                selected['analysis'] = analyzer.load_existing_analysis(symbol)
                if selected['analysis']:
                    score = selected['analysis'].get('buy_score', 0)
                    score_labels = {1: 'SELL', 2: 'SELL', 3: 'HOLD', 4: 'BUY', 5: 'BUY'}
                    stars = '★' * score + '☆' * (5 - score)
                    selected['rating_str'] = f" {stars} {score_labels.get(score, '?')}"
        else:
            # No existing analysis - offer to run one
            if analyzer:
                print(f"{Fore.YELLOW}No analysis found for {symbol}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Press Enter to analyze, or 's' to skip...{Style.RESET_ALL}")
                user_input = input().strip().lower()
                if user_input != 's':
                    analyzer.analyze(symbol)
                    # Reload the analysis
                    selected['analysis'] = analyzer.load_existing_analysis(symbol)
                    if selected['analysis']:
                        score = selected['analysis'].get('buy_score', 0)
                        score_labels = {1: 'SELL', 2: 'SELL', 3: 'HOLD', 4: 'BUY', 5: 'BUY'}
                        stars = '★' * score + '☆' * (5 - score)
                        selected['rating_str'] = f" {stars} {score_labels.get(score, '?')}"
            else:
                print(f"{Fore.RED}Analysis not available - configure API_NINJAS_KEY and OPENAI_KEY{Style.RESET_ALL}")
                input(f"{Fore.CYAN}Press Enter to continue...{Style.RESET_ALL}")
        
        print(f"{Fore.CYAN}{'─'*60}{Style.RESET_ALL}\n")


@cli.command()
def positions():
    """Interactive position viewer with analysis ratings"""
    manager = RobinhoodPositionManager()
    
    try:
        # Authenticate
        if not manager.authenticate():
            sys.exit(1)
        
        # Fetch and show portfolio summary
        click.echo(f"{Fore.CYAN}Fetching portfolio information...{Style.RESET_ALL}")
        portfolio_value, available_cash, positions_value = manager.get_portfolio_summary()
        
        click.echo(f"\n{Fore.WHITE}Portfolio Summary:{Style.RESET_ALL}")
        click.echo(f"  {Fore.GREEN}Total Portfolio Value: ${portfolio_value:,.2f}{Style.RESET_ALL}")
        click.echo(f"  {Fore.YELLOW}Available Cash: ${available_cash:,.2f}{Style.RESET_ALL}")
        click.echo(f"  {Fore.CYAN}Positions Value: ${positions_value:,.2f}{Style.RESET_ALL}")
        
        # Run the interactive menu
        _interactive_positions_menu(manager)
    
    except KeyboardInterrupt:
        click.echo(f"\n{Fore.YELLOW}Interrupted{Style.RESET_ALL}")
    except Exception as e:
        click.echo(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
    finally:
        manager.logout()


@cli.command()
@click.option('--username', '-u', help='Robinhood username (email)')
@click.option('--password', '-p', help='Robinhood password')
@click.option('--totp-secret', '-t', help='TOTP secret for automatic 2FA')
@click.option('--api-ninjas', help='API Ninjas key (for earnings data)')
@click.option('--openai', help='OpenAI API key (for AI analysis)')
def config(username, password, totp_secret, api_ninjas, openai):
    """Configure credentials and API keys"""

    # Create config directory
    config_dir = os.path.expanduser("~/.config/rob")
    os.makedirs(config_dir, exist_ok=True)

    env_file = os.path.join(config_dir, ".env")

    # Read existing values if file exists
    existing_values = {}
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    existing_values[key] = value

    print(f"\n{Fore.CYAN}═══ Robinhood Credentials ═══{Style.RESET_ALL}")
    
    # Get Robinhood credentials interactively if not provided
    if not username:
        existing_user = existing_values.get('ROBINHOOD_USERNAME', '')
        display = f" [{existing_user[:3]}...{existing_user[-4:]}]" if existing_user else ""
        username = input(f"Robinhood username (email){display}: ").strip()
        if not username and existing_user:
            username = existing_user

    if not password:
        existing_pass = existing_values.get('ROBINHOOD_PASSWORD', '')
        display = " [********]" if existing_pass else ""
        password = getpass.getpass(f"Robinhood password{display}: ").strip()
        if not password and existing_pass:
            password = existing_pass

    if not totp_secret:
        existing_totp = existing_values.get('ROBINHOOD_TOTP_SECRET', '')
        display = " [configured]" if existing_totp else " (optional)"
        totp_secret = input(f"TOTP secret for 2FA{display}: ").strip()
        if not totp_secret and existing_totp:
            totp_secret = existing_totp

    print(f"\n{Fore.CYAN}═══ API Keys (for analyze command) ═══{Style.RESET_ALL}")
    
    # API Ninjas key
    if not api_ninjas:
        existing_ninjas = existing_values.get('API_NINJAS_KEY', '')
        display = " [configured]" if existing_ninjas else ""
        api_ninjas = input(f"API Ninjas key{display}: ").strip()
        if not api_ninjas and existing_ninjas:
            api_ninjas = existing_ninjas
    
    # OpenAI key
    if not openai:
        existing_openai = existing_values.get('OPENAI_KEY', '')
        display = " [configured]" if existing_openai else ""
        openai = input(f"OpenAI API key{display}: ").strip()
        if not openai and existing_openai:
            openai = existing_openai

    # Write to .env file
    with open(env_file, 'w', encoding='utf-8') as f:
        if username:
            f.write(f"ROBINHOOD_USERNAME={username}\n")
        if password:
            f.write(f"ROBINHOOD_PASSWORD={password}\n")
        if totp_secret:
            f.write(f"ROBINHOOD_TOTP_SECRET={totp_secret}\n")
        if api_ninjas:
            f.write(f"API_NINJAS_KEY={api_ninjas}\n")
        if openai:
            f.write(f"OPENAI_KEY={openai}\n")

    # Set permissions to be secure (readable only by owner)
    os.chmod(env_file, 0o600)

    print(f"\n{Fore.GREEN}✓ Configuration saved to {env_file}{Style.RESET_ALL}")
    
    # Show what's configured
    configured = []
    if username: configured.append("Robinhood")
    if api_ninjas: configured.append("API Ninjas")
    if openai: configured.append("OpenAI")
    
    if configured:
        print(f"{Fore.CYAN}Configured: {', '.join(configured)}{Style.RESET_ALL}")

@cli.command()
@click.argument('ticker')
@click.option('--refresh', '-r', is_flag=True, help='Force refresh even if current analysis exists')
def analyze(ticker, refresh):
    """Fetch and save earnings data for a ticker
    
    TICKER: Stock ticker symbol (e.g., AAPL, MSFT)
    
    If an analysis already exists for the latest quarter, it will be displayed
    without re-fetching data. Use --refresh to force a new analysis.
    """
    try:
        analyzer = TickerAnalyzer()
        analyzer.analyze(ticker, force_refresh=refresh)
    except ValueError as e:
        click.echo(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}Unexpected error: {e}{Style.RESET_ALL}")
        sys.exit(1)


@cli.command()
def interactive():
    """Run in interactive mode"""
    # Create position manager instance
    manager = RobinhoodPositionManager()

    try:
        # Header
        print(f"\n  {Fore.CYAN}rob{Style.RESET_ALL} · Robinhood Portfolio Manager\n")

        # Authenticate
        if not manager.authenticate():
            sys.exit(1)

        # Fetch portfolio summary
        print(f"\n{Fore.CYAN}Loading portfolio...{Style.RESET_ALL}")
        portfolio_value, available_cash, positions_value = manager.get_portfolio_summary()

        # Main loop
        while True:
            # Clear screen and print header
            print("\033[2J\033[H", end="")  # Clear screen and move cursor to top
            
            # Print portfolio box
            total_str = f"${portfolio_value:,.2f}"
            cash_str = f"${available_cash:,.2f}"
            invested_str = f"${positions_value:,.2f}"
            
            print(f"\n  {Fore.CYAN}┌────────────────────────────────┐{Style.RESET_ALL}")
            print(f"  {Fore.CYAN}│{Style.RESET_ALL}  {Fore.WHITE}Portfolio{Style.RESET_ALL}                     {Fore.CYAN}│{Style.RESET_ALL}")
            print(f"  {Fore.CYAN}├────────────────────────────────┤{Style.RESET_ALL}")
            print(f"  {Fore.CYAN}│{Style.RESET_ALL}  {Fore.GREEN}Total{Style.RESET_ALL}      {total_str:>17}  {Fore.CYAN}│{Style.RESET_ALL}")
            print(f"  {Fore.CYAN}│{Style.RESET_ALL}  {Fore.YELLOW}Cash{Style.RESET_ALL}       {cash_str:>17}  {Fore.CYAN}│{Style.RESET_ALL}")
            print(f"  {Fore.CYAN}│{Style.RESET_ALL}  {Fore.CYAN}Invested{Style.RESET_ALL}   {invested_str:>17}  {Fore.CYAN}│{Style.RESET_ALL}")
            print(f"  {Fore.CYAN}└────────────────────────────────┘{Style.RESET_ALL}\n")
            
            menu_items = [
                "📊  View positions with ratings",
                "📈  Increase all positions by %",
                "📉  Decrease all positions by %",
                "🔍  Analyze a ticker",
                "─" * 34,
                "✗   Exit",
            ]
            
            terminal_menu = TerminalMenu(
                menu_items,
                menu_cursor="▶ ",
                menu_cursor_style=("fg_cyan", "bold"),
                menu_highlight_style=("fg_cyan", "bold"),
                cycle_cursor=True,
                clear_screen=False,  # We handle clearing ourselves
            )
            
            choice_idx = terminal_menu.show()
            
            if choice_idx is None or choice_idx == 5:  # q/Esc or Exit
                print(f"\n{Fore.YELLOW}Goodbye!{Style.RESET_ALL}\n")
                break
            
            if choice_idx == 4:  # Separator line
                continue
            
            if choice_idx == 0:  # View positions
                print(f"\n{Fore.CYAN}{'─'*60}{Style.RESET_ALL}")
                _interactive_positions_menu(manager)
                print(f"{Fore.CYAN}{'─'*60}{Style.RESET_ALL}\n")
            
            elif choice_idx in [1, 2]:  # Increase/Decrease
                action = 'increase' if choice_idx == 1 else 'decrease'
                action_emoji = '📈' if action == 'increase' else '📉'
                
                print(f"\n{Fore.CYAN}{'─'*60}{Style.RESET_ALL}")
                print(f"{action_emoji}  {Fore.WHITE}{action.upper()} POSITIONS{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{'─'*60}{Style.RESET_ALL}")
                
                # Get percentage
                while True:
                    try:
                        pct_input = input(f"\n{Fore.YELLOW}Enter percentage (1-100), or 'c' to cancel: {Style.RESET_ALL}").strip()
                        if pct_input.lower() == 'c':
                            print(f"{Fore.YELLOW}Cancelled.{Style.RESET_ALL}")
                            break
                        percentage = float(pct_input)
                        if percentage <= 0 or percentage > 100:
                            print(f"{Fore.RED}Please enter a number between 1 and 100{Style.RESET_ALL}")
                            continue
                        
                        # Calculate cost
                        print(f"\n{Fore.CYAN}Calculating...{Style.RESET_ALL}")
                        expected_cost = manager.calculate_total_expected_cost(action, percentage)
                        
                        # Show summary
                        print(f"\n{Fore.WHITE}Operation Summary:{Style.RESET_ALL}")
                        print(f"  Action: {Fore.CYAN}{action.upper()}{Style.RESET_ALL} all positions by {Fore.YELLOW}{percentage}%{Style.RESET_ALL}")
                        
                        if action == 'increase':
                            print(f"  Cost:   {Fore.RED}${expected_cost:,.2f}{Style.RESET_ALL}")
                            print(f"  Cash:   {Fore.GREEN}${available_cash:,.2f}{Style.RESET_ALL}")
                            
                            if expected_cost > available_cash:
                                print(f"\n{Fore.RED}❌ Insufficient funds!{Style.RESET_ALL}")
                                print(f"{Fore.YELLOW}Need ${expected_cost:,.2f} but only have ${available_cash:,.2f}{Style.RESET_ALL}")
                                break
                            print(f"  After:  {Fore.GREEN}${available_cash - expected_cost:,.2f}{Style.RESET_ALL}")
                        else:
                            print(f"  Proceeds: {Fore.GREEN}${expected_cost:,.2f}{Style.RESET_ALL}")
                            print(f"  Cash after: {Fore.GREEN}${available_cash + expected_cost:,.2f}{Style.RESET_ALL}")
                        
                        # Confirm
                        confirm_menu = TerminalMenu(
                            ["✓ Yes, proceed", "✗ Cancel"],
                            title=f"\n  {Fore.YELLOW}Execute trades?{Style.RESET_ALL}\n",
                            menu_cursor="▶ ",
                            menu_cursor_style=("fg_yellow", "bold"),
                            clear_screen=False,
                        )
                        if confirm_menu.show() == 0:
                            manager.process_positions(action, percentage, dry_run=False, auto_confirm=False)
                            # Refresh portfolio values
                            portfolio_value, available_cash, positions_value = manager.get_portfolio_summary()
                        else:
                            print(f"{Fore.YELLOW}Cancelled.{Style.RESET_ALL}")
                        break
                        
                    except ValueError:
                        print(f"{Fore.RED}Please enter a valid number{Style.RESET_ALL}")
                
                print(f"{Fore.CYAN}{'─'*60}{Style.RESET_ALL}\n")
            
            elif choice_idx == 3:  # Analyze ticker
                print(f"\n{Fore.CYAN}{'─'*60}{Style.RESET_ALL}")
                print(f"🔍  {Fore.WHITE}ANALYZE TICKER{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{'─'*60}{Style.RESET_ALL}")
                
                ticker = input(f"\n{Fore.YELLOW}Enter ticker symbol (or 'c' to cancel): {Style.RESET_ALL}").strip().upper()
                if ticker and ticker != 'C':
                    refresh_menu = TerminalMenu(
                        ["Use cached (if available)", "Force fresh analysis"],
                        title=f"\n  Analyze {Fore.CYAN}{ticker}{Style.RESET_ALL}\n",
                        menu_cursor="▶ ",
                        menu_cursor_style=("fg_cyan", "bold"),
                        clear_screen=False,
                    )
                    force_refresh = refresh_menu.show() == 1
                    
                    try:
                        analyzer = TickerAnalyzer()
                        analyzer.analyze(ticker, force_refresh=force_refresh)
                    except ValueError as e:
                        print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
                    except Exception as e:
                        print(f"{Fore.RED}Unexpected error: {e}{Style.RESET_ALL}")
                
                print(f"{Fore.CYAN}{'─'*60}{Style.RESET_ALL}\n")

    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Interrupted{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}Unexpected error: {e}{Style.RESET_ALL}")
    finally:
        manager.logout()

def main():
    """Fallback to interactive mode if no arguments provided"""
    if len(sys.argv) == 1:
        # No arguments provided, run interactive mode
        interactive()
    else:
        # Arguments provided, use Click CLI
        cli()

if __name__ == '__main__':
    main()
