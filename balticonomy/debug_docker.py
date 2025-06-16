#!/usr/bin/env python3
"""
Debug script to check Docker environment for Selenium
"""
import os
import subprocess
import sys

def run_command(cmd):
    """Run a command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)

def check_chrome():
    """Check if Chrome is installed"""
    print("=== Chrome Check ===")
    code, stdout, stderr = run_command("google-chrome --version")
    if code == 0:
        print(f"✓ Chrome found: {stdout.strip()}")
        return True
    else:
        print(f"✗ Chrome not found: {stderr}")
        return False

def check_chromedriver():
    """Check ChromeDriver installation"""
    print("\n=== ChromeDriver Check ===")
    
    # Check common locations
    locations = [
        "/usr/local/bin/chromedriver",
        "/usr/bin/chromedriver",
        "/opt/chromedriver",
        "chromedriver"
    ]
    
    found = False
    for location in locations:
        if os.path.exists(location):
            print(f"✓ ChromeDriver found at: {location}")
            code, stdout, stderr = run_command(f"{location} --version")
            if code == 0:
                print(f"  Version: {stdout.strip()}")
            found = True
            break
    
    if not found:
        print("✗ ChromeDriver not found in common locations")
        # Try which command
        code, stdout, stderr = run_command("which chromedriver")
        if code == 0:
            print(f"✓ ChromeDriver found via which: {stdout.strip()}")
            found = True
    
    return found

def check_selenium():
    """Check Selenium installation"""
    print("\n=== Selenium Check ===")
    try:
        import selenium
        print(f"✓ Selenium installed: {selenium.__version__}")
        
        from selenium import webdriver
        print("✓ webdriver module available")
        
        from selenium.webdriver.chrome.options import Options
        print("✓ Chrome options available")
        
        return True
    except ImportError as e:
        print(f"✗ Selenium issue: {e}")
        return False

def check_permissions():
    """Check file permissions"""
    print("\n=== Permissions Check ===")
    
    # Check /tmp permissions
    code, stdout, stderr = run_command("ls -la /tmp")
    if code == 0:
        print("✓ /tmp directory accessible")
    else:
        print("✗ /tmp directory issue")
    
    # Check current user
    code, stdout, stderr = run_command("whoami")
    if code == 0:
        print(f"✓ Running as user: {stdout.strip()}")
    
    return True

def test_basic_selenium():
    """Test basic Selenium functionality"""
    print("\n=== Basic Selenium Test ===")
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        import tempfile
        
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument(f"--user-data-dir={tempfile.mkdtemp()}")
        
        print("Attempting to create Chrome driver...")
        driver = webdriver.Chrome(options=options)
        print("✓ Chrome driver created successfully")
        
        driver.get("data:text/html,<html><body><h1>Test</h1></body></html>")
        print("✓ Basic navigation works")
        
        driver.quit()
        print("✓ Driver cleanup successful")
        
        return True
        
    except Exception as e:
        print(f"✗ Selenium test failed: {e}")
        return False

def main():
    """Main debug function"""
    print("Docker Selenium Environment Debug")
    print("=" * 40)
    
    results = []
    results.append(("Chrome", check_chrome()))
    results.append(("ChromeDriver", check_chromedriver()))
    results.append(("Selenium", check_selenium()))
    results.append(("Permissions", check_permissions()))
    results.append(("Basic Test", test_basic_selenium()))
    
    print("\n" + "=" * 40)
    print("SUMMARY")
    print("=" * 40)
    
    all_good = True
    for name, status in results:
        status_str = "✓ PASS" if status else "✗ FAIL"
        print(f"{name:15} {status_str}")
        if not status:
            all_good = False
    
    if all_good:
        print("\n🎉 Environment looks good!")
    else:
        print("\n⚠️  Issues detected - see details above")
    
    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main())