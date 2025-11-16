#!/usr/bin/env python3
"""
setup_enhanced_system.py
One-click setup script for the enhanced football prediction system
Handles installation, configuration, and initial testing
"""

import os
import sys
import subprocess
import json
import shutil
from pathlib import Path
from datetime import datetime
import requests

# ============================================================================
# CONFIGURATION
# ============================================================================

REQUIRED_PACKAGES = [
    "numpy>=1.21.0",
    "pandas>=1.3.0",
    "scikit-learn>=1.0.0",
    "scipy>=1.7.0",
    "requests>=2.25.0",
    "openpyxl>=3.0.0",
    "python-dotenv>=0.19.0",
    "colorama>=0.4.4",
    "tqdm>=4.62.0",
    "tabulate>=0.8.9",
    "plotly>=5.3.0",
    "kaleido>=0.2.1",  # For plotly static images
]

OPTIONAL_PACKAGES = [
    "xgboost>=1.5.0",
    "lightgbm>=3.3.0",
    "catboost>=1.0.0",
    "optuna>=3.0.0",
    "torch>=1.12.0",
]

PROJECT_STRUCTURE = {
    "data": ["raw", "interim", "processed"],
    "models": [],
    "outputs": [],
    "cache": ["api_football"],
    "logs": [],
    "archives": [],
    "reports": ["html", "csv", "json"],
    "backups": []
}

# ============================================================================
# COLOR OUTPUT
# ============================================================================

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    
    def print_success(msg):
        print(f"{Fore.GREEN}✓ {msg}{Style.RESET_ALL}")
    
    def print_error(msg):
        print(f"{Fore.RED}✗ {msg}{Style.RESET_ALL}")
    
    def print_warning(msg):
        print(f"{Fore.YELLOW}⚠ {msg}{Style.RESET_ALL}")
    
    def print_info(msg):
        print(f"{Fore.CYAN}ℹ {msg}{Style.RESET_ALL}")
    
    def print_header(msg):
        print(f"\n{Fore.BLUE}{'='*60}")
        print(f"{msg}")
        print(f"{'='*60}{Style.RESET_ALL}")

except ImportError:
    # Fallback to regular print
    def print_success(msg): print(f"✓ {msg}")
    def print_error(msg): print(f"✗ {msg}")
    def print_warning(msg): print(f"⚠ {msg}")
    def print_info(msg): print(f"ℹ {msg}")
    def print_header(msg): print(f"\n{'='*60}\n{msg}\n{'='*60}")

# ============================================================================
# SETUP FUNCTIONS
# ============================================================================

class EnhancedSystemSetup:
    """Setup and configuration manager for enhanced system"""
    
    def __init__(self):
        self.root_dir = Path.cwd()
        self.config_file = self.root_dir / ".env"
        self.config = {}
        
    def run_full_setup(self):
        """Run complete setup process"""
        print_header("ENHANCED FOOTBALL PREDICTION SYSTEM SETUP")
        
        # Step 1: Check Python version
        self.check_python_version()
        
        # Step 2: Create directory structure
        self.create_directory_structure()
        
        # Step 3: Install packages
        self.install_packages()
        
        # Step 4: Configure API keys
        self.configure_api_keys()
        
        # Step 5: Download enhanced modules
        self.download_enhanced_modules()
        
        # Step 6: Test API connection
        self.test_api_connection()
        
        # Step 7: Backup existing files
        self.backup_existing_files()
        
        # Step 8: Integrate with existing system
        self.integrate_with_existing()
        
        # Step 9: Create shortcuts
        self.create_shortcuts()
        
        # Step 10: Final validation
        self.validate_setup()
        
        print_header("SETUP COMPLETE!")
        self.print_next_steps()
    
    def check_python_version(self):
        """Check if Python version is compatible"""
        print_header("CHECKING PYTHON VERSION")
        
        version = sys.version_info
        if version.major == 3 and version.minor >= 8:
            print_success(f"Python {version.major}.{version.minor}.{version.micro} is compatible")
        else:
            print_error(f"Python 3.8+ required (current: {version.major}.{version.minor})")
            sys.exit(1)
    
    def create_directory_structure(self):
        """Create required directory structure"""
        print_header("CREATING DIRECTORY STRUCTURE")
        
        for main_dir, subdirs in PROJECT_STRUCTURE.items():
            main_path = self.root_dir / main_dir
            main_path.mkdir(exist_ok=True)
            print_success(f"Created {main_dir}/")
            
            for subdir in subdirs:
                sub_path = main_path / subdir
                sub_path.mkdir(exist_ok=True)
                print_info(f"  └─ {subdir}/")
    
    def install_packages(self):
        """Install required Python packages"""
        print_header("INSTALLING PYTHON PACKAGES")
        
        # Install required packages
        print_info("Installing required packages...")
        for package in REQUIRED_PACKAGES:
            self._install_package(package, required=True)
        
        # Ask about optional packages
        print("\nOptional packages for advanced features:")
        install_optional = input("Install optional packages? (y/n, default=y): ").strip().lower()
        
        if install_optional != 'n':
            print_info("Installing optional packages...")
            for package in OPTIONAL_PACKAGES:
                self._install_package(package, required=False)
    
    def _install_package(self, package_spec, required=True):
        """Install a single package"""
        try:
            # Check if already installed
            package_name = package_spec.split(">=")[0].split("==")[0]
            subprocess.run(
                [sys.executable, "-c", f"import {package_name.replace('-', '_')}"],
                check=True,
                capture_output=True,
                text=True
            )
            print_info(f"  {package_name} already installed")
        except:
            # Install package
            try:
                print_info(f"  Installing {package_spec}...")
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", package_spec],
                    check=True,
                    capture_output=True,
                    text=True
                )
                print_success(f"  {package_spec} installed")
            except Exception as e:
                if required:
                    print_error(f"  Failed to install {package_spec}: {e}")
                    sys.exit(1)
                else:
                    print_warning(f"  Optional package {package_spec} not installed")
    
    def configure_api_keys(self):
        """Configure API keys and credentials"""
        print_header("CONFIGURING API KEYS")
        
        # Check for existing .env
        if self.config_file.exists():
            print_info("Found existing .env file")
            overwrite = input("Overwrite existing configuration? (y/n, default=n): ").strip().lower()
            if overwrite != 'y':
                self._load_existing_config()
                return
        
        print("\nEnter your API credentials (press Enter to skip):")
        
        # API-Football key
        api_key = input("API-Football key: ").strip()
        if api_key:
            self.config["API_FOOTBALL_KEY"] = api_key
            print_success("API-Football key configured")
        else:
            print_warning("API-Football key not set - enhanced features disabled")
        
        # Email configuration for reports
        print("\nEmail configuration (for automated reports):")
        email_sender = input("Sender email address: ").strip()
        if email_sender:
            self.config["EMAIL_SENDER"] = email_sender
            self.config["EMAIL_PASSWORD"] = input("Email password: ").strip()
            self.config["EMAIL_RECIPIENT"] = input("Recipient email: ").strip()
            self.config["EMAIL_SMTP_SERVER"] = input("SMTP server (default: smtp-mail.outlook.com): ").strip() or "smtp-mail.outlook.com"
            self.config["EMAIL_SMTP_PORT"] = input("SMTP port (default: 587): ").strip() or "587"
            print_success("Email configuration saved")
        
        # Training configuration
        print("\nTraining configuration:")
        self.config["TRAINING_START_YEAR"] = input("Training start year (default: 2020): ").strip() or "2020"
        self.config["OPTUNA_TRIALS"] = input("Optuna trials for tuning (default: 25): ").strip() or "25"
        
        # Save configuration
        self._save_config()
        print_success("Configuration saved to .env file")
    
    def _load_existing_config(self):
        """Load existing configuration"""
        try:
            with open(self.config_file, 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        self.config[key] = value
            print_success("Loaded existing configuration")
        except Exception as e:
            print_error(f"Failed to load configuration: {e}")
    
    def _save_config(self):
        """Save configuration to .env file"""
        with open(self.config_file, 'w') as f:
            f.write("# Enhanced Football Prediction System Configuration\n")
            f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for key, value in self.config.items():
                f.write(f"{key}={value}\n")
    
    def download_enhanced_modules(self):
        """Download or copy enhanced modules"""
        print_header("SETTING UP ENHANCED MODULES")
        
        modules = [
            "api_football_integration.py",
            "enhanced_features.py",
            "run_weekly_enhanced.py"
        ]
        
        # Check if modules already exist
        for module in modules:
            module_path = self.root_dir / module
            if module_path.exists():
                print_info(f"{module} already exists")
            else:
                # Copy from outputs if available
                output_path = Path("/mnt/user-data/outputs") / module
                if output_path.exists():
                    shutil.copy(output_path, module_path)
                    print_success(f"Copied {module}")
                else:
                    print_warning(f"{module} not found - manual installation required")
    
    def test_api_connection(self):
        """Test API-Football connection"""
        print_header("TESTING API CONNECTION")
        
        api_key = self.config.get("API_FOOTBALL_KEY")
        if not api_key:
            print_warning("No API key configured - skipping test")
            return
        
        try:
            # Test API connection
            headers = {"x-apisports-key": api_key}
            response = requests.get(
                "https://v3.football.api-sports.io/status",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("results"):
                    account = data["response"]["account"]
                    subscription = data["response"]["subscription"]
                    requests_info = data["response"]["requests"]
                    
                    print_success("API connection successful!")
                    print_info(f"  Account: {account.get('firstname', '')} {account.get('lastname', '')}")
                    print_info(f"  Plan: {subscription.get('plan', 'Unknown')}")
                    print_info(f"  Requests today: {requests_info.get('current', 0)}/{requests_info.get('limit_day', 0)}")
                else:
                    print_error("API key invalid or expired")
            else:
                print_error(f"API connection failed (status: {response.status_code})")
        
        except Exception as e:
            print_error(f"API test failed: {e}")
    
    def backup_existing_files(self):
        """Backup existing project files"""
        print_header("BACKING UP EXISTING FILES")
        
        backup_dir = self.root_dir / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        files_to_backup = [
            "run_weeklyOU.py",
            "models.py",
            "features.py",
            "predict.py",
            "config.py"
        ]
        
        backed_up = 0
        for file in files_to_backup:
            file_path = self.root_dir / file
            if file_path.exists():
                shutil.copy(file_path, backup_dir / file)
                backed_up += 1
        
        if backed_up > 0:
            print_success(f"Backed up {backed_up} files to {backup_dir}")
        else:
            print_info("No files to backup")
    
    def integrate_with_existing(self):
        """Integrate enhanced system with existing code"""
        print_header("INTEGRATING WITH EXISTING SYSTEM")
        
        # Check for existing main runner
        main_runner = self.root_dir / "run_weeklyOU.py"
        if main_runner.exists():
            print_info("Found existing run_weeklyOU.py")
            
            # Create enhanced version
            enhanced_runner = self.root_dir / "run_weeklyOU_enhanced.py"
            
            with open(enhanced_runner, 'w') as f:
                f.write("""#!/usr/bin/env python3
'''
Enhanced version of run_weeklyOU.py with API-Football integration
'''

import os
import sys

# Check for API key
API_KEY = os.environ.get('API_FOOTBALL_KEY', '')

if API_KEY:
    print("Running enhanced pipeline with API-Football...")
    from run_weekly_enhanced import run_enhanced_weekly_pipeline
    results = run_enhanced_weekly_pipeline()
else:
    print("Running standard pipeline...")
    # Import and run your original pipeline
    exec(open('run_weeklyOU.py').read())
""")
            
            print_success("Created run_weeklyOU_enhanced.py")
            print_info("Use this file to run with enhanced features")
        else:
            print_warning("No existing run_weeklyOU.py found")
    
    def create_shortcuts(self):
        """Create convenient shortcut scripts"""
        print_header("CREATING SHORTCUTS")
        
        # Create run script
        run_script = self.root_dir / "run.py"
        with open(run_script, 'w') as f:
            f.write("""#!/usr/bin/env python3
'''
Quick run script for weekly predictions
'''

import os
import sys
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Check which mode to run
if os.environ.get('API_FOOTBALL_KEY'):
    print("🚀 Running ENHANCED predictions with API-Football...")
    from run_weekly_enhanced import run_enhanced_weekly_pipeline
    results = run_enhanced_weekly_pipeline()
else:
    print("📊 Running standard predictions...")
    if Path('run_weeklyOU.py').exists():
        exec(open('run_weeklyOU.py').read())
    else:
        print("❌ No prediction system found!")
        print("Please run setup_enhanced_system.py first")
""")
        
        print_success("Created run.py shortcut")
        
        # Create test script
        test_script = self.root_dir / "test_system.py"
        with open(test_script, 'w') as f:
            f.write("""#!/usr/bin/env python3
'''
System test and validation script
'''

import os
import sys
from pathlib import Path

print("="*60)
print("SYSTEM TEST")
print("="*60)

# Test imports
tests_passed = 0
tests_failed = 0

print("\\nTesting core imports...")
try:
    import numpy as np
    import pandas as pd
    import sklearn
    print("✓ Core packages OK")
    tests_passed += 1
except ImportError as e:
    print(f"✗ Core packages failed: {e}")
    tests_failed += 1

print("\\nTesting enhanced modules...")
try:
    from api_football_integration import APIFootballClient
    from enhanced_features import FeatureEngineer
    print("✓ Enhanced modules OK")
    tests_passed += 1
except ImportError as e:
    print(f"✗ Enhanced modules failed: {e}")
    tests_failed += 1

print("\\nTesting API connection...")
from dotenv import load_dotenv
load_dotenv()

api_key = os.environ.get('API_FOOTBALL_KEY')
if api_key:
    try:
        from api_football_integration import APIFootballClient
        client = APIFootballClient(api_key)
        print("✓ API client initialized")
        tests_passed += 1
    except Exception as e:
        print(f"✗ API client failed: {e}")
        tests_failed += 1
else:
    print("⚠ No API key configured")

print("\\nTesting directory structure...")
required_dirs = ['data', 'models', 'outputs', 'cache']
for dir_name in required_dirs:
    if Path(dir_name).exists():
        print(f"✓ {dir_name}/ exists")
        tests_passed += 1
    else:
        print(f"✗ {dir_name}/ missing")
        tests_failed += 1

print("\\n" + "="*60)
print(f"Tests passed: {tests_passed}")
print(f"Tests failed: {tests_failed}")

if tests_failed == 0:
    print("✅ ALL TESTS PASSED - System ready!")
else:
    print("⚠️ Some tests failed - please review")
print("="*60)
""")
        
        print_success("Created test_system.py")
        
        # Make scripts executable on Unix
        if os.name != 'nt':
            os.chmod(run_script, 0o755)
            os.chmod(test_script, 0o755)
            print_info("Scripts made executable")
    
    def validate_setup(self):
        """Validate the complete setup"""
        print_header("VALIDATING SETUP")
        
        validation_passed = True
        
        # Check directory structure
        for main_dir in PROJECT_STRUCTURE.keys():
            if not (self.root_dir / main_dir).exists():
                print_error(f"Directory {main_dir}/ missing")
                validation_passed = False
        
        # Check configuration
        if not self.config_file.exists():
            print_warning("Configuration file .env not found")
        
        # Check modules
        required_modules = [
            "api_football_integration.py",
            "enhanced_features.py",
            "run_weekly_enhanced.py"
        ]
        
        for module in required_modules:
            if not (self.root_dir / module).exists():
                print_warning(f"Enhanced module {module} not found")
        
        if validation_passed:
            print_success("Setup validation passed!")
        else:
            print_warning("Some validation checks failed - review above")
    
    def print_next_steps(self):
        """Print next steps for user"""
        print("\n" + "="*60)
        print("NEXT STEPS")
        print("="*60)
        
        print("\n1. TEST YOUR SYSTEM:")
        print("   python test_system.py")
        
        print("\n2. RUN WEEKLY PREDICTIONS:")
        print("   python run.py")
        
        print("\n3. VIEW CONFIGURATION:")
        print("   cat .env")
        
        print("\n4. CHECK OUTPUTS:")
        print("   ls outputs/")
        
        if self.config.get("API_FOOTBALL_KEY"):
            print("\n✅ API-Football is configured - you have access to:")
            print("   • 300+ fixtures per week")
            print("   • 15+ betting markets per match")
            print("   • xG data and advanced statistics")
            print("   • Arbitrage detection")
            print("   • 30+ bookmaker odds")
        else:
            print("\n⚠️ No API key configured - get one at:")
            print("   https://dashboard.api-football.com")
            print("   Then add to .env file: API_FOOTBALL_KEY=your_key_here")
        
        print("\n" + "="*60)
        print("Happy betting! Remember to bet responsibly.")
        print("="*60)

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║   ENHANCED FOOTBALL PREDICTION SYSTEM - SETUP WIZARD     ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    print("This wizard will:")
    print("  • Install all required packages")
    print("  • Set up directory structure")
    print("  • Configure API keys")
    print("  • Integrate enhanced features")
    print("  • Create convenient shortcuts")
    print()
    
    proceed = input("Continue with setup? (y/n): ").strip().lower()
    
    if proceed == 'y':
        setup = EnhancedSystemSetup()
        
        try:
            setup.run_full_setup()
        except KeyboardInterrupt:
            print("\n\nSetup cancelled by user")
            sys.exit(1)
        except Exception as e:
            print(f"\n\nSetup failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        print("Setup cancelled")
