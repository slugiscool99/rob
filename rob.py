#!/usr/bin/env python3
"""
Robinhood Position Manager CLI Tool
Allows you to increase or decrease positions by a specified percentage
"""

import os
import sys
import time
import getpass
from typing import Dict, List, Tuple, Optional
from decimal import Decimal, ROUND_DOWN
from colorama import init, Fore, Style
import robin_stocks.robinhood as rs
from dotenv import load_dotenv
import pyotp
import click

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

@cli.command()
@click.option('--username', '-u', help='Robinhood username (email)')
@click.option('--password', '-p', help='Robinhood password')
@click.option('--totp-secret', '-t', help='TOTP secret for automatic 2FA')
def config(username, password, totp_secret):
    """Configure Robinhood credentials"""
    import getpass

    # Create config directory
    config_dir = os.path.expanduser("~/.config/rob")
    os.makedirs(config_dir, exist_ok=True)

    env_file = os.path.join(config_dir, ".env")

    # Read existing values if file exists
    existing_values = {}
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    existing_values[key] = value

    # Get credentials interactively if not provided
    if not username:
        username = input(f"Enter Robinhood username (email) [{existing_values.get('ROBINHOOD_USERNAME', '')}]: ").strip()
        if not username and 'ROBINHOOD_USERNAME' in existing_values:
            username = existing_values['ROBINHOOD_USERNAME']

    if not password:
        password = getpass.getpass("Enter Robinhood password: ").strip()
        if not password and 'ROBINHOOD_PASSWORD' in existing_values:
            password = existing_values['ROBINHOOD_PASSWORD']

    if not totp_secret:
        totp_prompt = f"Enter TOTP secret (optional, for automatic 2FA) [{existing_values.get('ROBINHOOD_TOTP_SECRET', '')}]: "
        totp_secret = input(totp_prompt).strip()
        if not totp_secret and 'ROBINHOOD_TOTP_SECRET' in existing_values:
            totp_secret = existing_values['ROBINHOOD_TOTP_SECRET']

    # Write to .env file
    with open(env_file, 'w') as f:
        if username:
            f.write(f"ROBINHOOD_USERNAME={username}\n")
        if password:
            f.write(f"ROBINHOOD_PASSWORD={password}\n")
        if totp_secret:
            f.write(f"ROBINHOOD_TOTP_SECRET={totp_secret}\n")

    # Set permissions to be secure (readable only by owner)
    os.chmod(env_file, 0o600)

    click.echo(f"{Fore.GREEN}✓ Credentials saved to {env_file}{Style.RESET_ALL}")
    click.echo(f"{Fore.CYAN}You can now use rob from anywhere!{Style.RESET_ALL}")

@cli.command()
def interactive():
    """Run in interactive mode (legacy behavior)"""
    # Create position manager instance
    manager = RobinhoodPositionManager()

    try:
        # Header
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}         Robinhood Position Manager{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

        # Authenticate
        if not manager.authenticate():
            sys.exit(1)

        # Fetch and display portfolio summary
        print(f"\n{Fore.CYAN}Fetching portfolio information...{Style.RESET_ALL}")
        portfolio_value, available_cash, positions_value = manager.get_portfolio_summary()

        print(f"\n{Fore.WHITE}Portfolio Summary:{Style.RESET_ALL}")
        print(f"  {Fore.GREEN}Total Portfolio Value: ${portfolio_value:,.2f}{Style.RESET_ALL}")
        print(f"  {Fore.YELLOW}Available Cash: ${available_cash:,.2f}{Style.RESET_ALL}")
        print(f"  {Fore.CYAN}Positions Value: ${positions_value:,.2f}{Style.RESET_ALL}")

        # Get action from user
        print(f"\n{Fore.WHITE}What would you like to do?{Style.RESET_ALL}")
        print(f"  1) Increase positions")
        print(f"  2) Decrease positions")
        print(f"  3) Exit")

        while True:
            choice = input(f"\n{Fore.YELLOW}Enter your choice (1-3): {Style.RESET_ALL}").strip()
            if choice == '1':
                action = 'increase'
                break
            elif choice == '2':
                action = 'decrease'
                break
            elif choice == '3':
                print(f"\n{Fore.YELLOW}Exiting...{Style.RESET_ALL}")
                return
            else:
                print(f"{Fore.RED}Invalid choice. Please enter 1, 2, or 3.{Style.RESET_ALL}")

        # Get percentage from user
        while True:
            try:
                percentage = float(input(f"\n{Fore.YELLOW}Enter the percentage to {action} positions by: {Style.RESET_ALL}"))
                if percentage <= 0 or percentage > 100:
                    print(f"{Fore.RED}Please enter a percentage between 0 and 100{Style.RESET_ALL}")
                    continue
                break
            except ValueError:
                print(f"{Fore.RED}Please enter a valid number{Style.RESET_ALL}")

        # Calculate and display expected cost
        print(f"\n{Fore.CYAN}Calculating expected cost...{Style.RESET_ALL}")
        expected_cost = manager.calculate_total_expected_cost(action, percentage)

        print(f"\n{Fore.WHITE}Operation Summary:{Style.RESET_ALL}")
        print(f"  Action: {Fore.CYAN}{action.upper()}{Style.RESET_ALL} positions by {Fore.YELLOW}{percentage}%{Style.RESET_ALL}")

        if action == 'increase':
            print(f"  Expected Total Cost: {Fore.RED}${expected_cost:,.2f}{Style.RESET_ALL}")
            print(f"  Available Cash: {Fore.GREEN}${available_cash:,.2f}{Style.RESET_ALL}")

            # Check if user has enough cash
            if expected_cost > available_cash:
                print(f"\n{Fore.RED}❌ ERROR: Insufficient funds!{Style.RESET_ALL}")
                print(f"{Fore.RED}You need ${expected_cost:,.2f} but only have ${available_cash:,.2f} available.{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Try a smaller percentage or sell some positions first.{Style.RESET_ALL}")
                return
            else:
                print(f"  Remaining Cash After: {Fore.GREEN}${available_cash - expected_cost:,.2f}{Style.RESET_ALL}")
        else:
            print(f"  Expected Proceeds: {Fore.GREEN}${expected_cost:,.2f}{Style.RESET_ALL}")
            print(f"  Cash After Selling: {Fore.GREEN}${available_cash + expected_cost:,.2f}{Style.RESET_ALL}")

        # Confirm before proceeding
        confirm = input(f"\n{Fore.YELLOW}Proceed with {action}ing positions? (yes/no): {Style.RESET_ALL}").strip().lower()
        if confirm not in ['yes', 'y']:
            print(f"\n{Fore.YELLOW}Operation cancelled.{Style.RESET_ALL}")
            return

        # Process positions
        manager.process_positions(action, percentage, dry_run=False, auto_confirm=False)

    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Interrupted by user{Style.RESET_ALL}")
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
