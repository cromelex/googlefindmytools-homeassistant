#
#  GoogleFindMyTools - A set of tools to interact with the Google Find My API
#  Copyright © 2024 Leon Böttger. All rights reserved.
#

import logging
import os
import platform
import shutil
import subprocess

import undetected_chromedriver as uc

logger = logging.getLogger("GoogleFindMyTools")

def find_chrome():
    """Find Chrome executable using known paths and system commands, including Flatpak."""
    possiblePaths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\ProgramData\chocolatey\bin\chrome.exe",
        r"C:\Users\%USERNAME%\AppData\Local\Google\Chrome\Application\chrome.exe",
        "/usr/bin/google-chrome",
        "/usr/local/bin/google-chrome",
        "/opt/google/chrome/chrome",
        "/snap/bin/chromium",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    ]

    # Check predefined paths first
    for path in possiblePaths:
        if os.path.exists(path):
            return path

    # Check for Flatpak Chrome installations
    if platform.system() == "Linux":
        flatpak_chrome_apps = [
            "com.google.Chrome",
            "org.chromium.Chromium"
        ]

        # Check if flatpak command exists
        if shutil.which("flatpak"):
            try:
                # List installed flatpak applications
                result = subprocess.run(["flatpak", "list", "--app"],
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    installed_apps = result.stdout

                    for app_id in flatpak_chrome_apps:
                        if app_id in installed_apps:
                            logger.info(f"Found Flatpak Chrome installation: {app_id}")
                            return f"flatpak run {app_id}"

            except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
                logger.warning(f"Error checking Flatpak installations: {e}")

    # Use system command to find Chrome
    try:
        if platform.system() == "Windows":
            chrome_path = shutil.which("chrome")
        else:
            chrome_path = shutil.which("google-chrome") or shutil.which("chromium")
        if chrome_path:
            return chrome_path
    except Exception as e:
        logger.error(f"Error while searching system paths for Chrome: {e}")

    return None


def get_options():
    chrome_options = uc.ChromeOptions()
    chrome_options.add_argument("--start-maximised")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    # Run in headless mode if the HEADLESS environment variable is set to "true"
    # This is useful for running in a Docker container or on a server without a GUI.
    if os.environ.get("HEADLESS", "false").lower() == "true":
        chrome_options.add_argument("--headless=new")

    return chrome_options


def create_flatpak_wrapper_script(flatpak_command):
    """Create a temporary wrapper script for Flatpak Chrome execution."""
    import tempfile

    # Create a temporary script that can be used as the browser executable
    wrapper_content = f"""#!/bin/bash
exec {flatpak_command} "$@"
"""

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
        f.write(wrapper_content)
        wrapper_path = f.name

    # Make it executable
    os.chmod(wrapper_path, 0o755)

    logger.info(f"Created Flatpak wrapper script at: {wrapper_path}")
    return wrapper_path


def create_driver():
    """Create a Chrome WebDriver with undetected_chromedriver."""

    try:
        chrome_options = get_options()
        driver = uc.Chrome(options=chrome_options)
        logger.info("ChromeDriver installed and browser started.")
        return driver
    except Exception:
        logger.warning("Default ChromeDriver creation failed. Trying alternative paths...")

        chrome_path = find_chrome()
        if chrome_path:
            chrome_options = get_options()

            # Handle Flatpak Chrome specially
            if chrome_path.startswith("flatpak run"):
                try:
                    # For Flatpak, we need to create a wrapper script
                    wrapper_script = create_flatpak_wrapper_script(chrome_path)
                    chrome_options.binary_location = wrapper_script

                    # Additional Flatpak-specific options
                    chrome_options.add_argument("--disable-dev-shm-usage")
                    chrome_options.add_argument("--disable-setuid-sandbox")

                    driver = uc.Chrome(options=chrome_options, browser_executable_path=wrapper_script)
                    logger.info(f"ChromeDriver started using Flatpak Chrome: {chrome_path}")
                    return driver

                except Exception as e:
                    logger.error(f"ChromeDriver failed using Flatpak Chrome {chrome_path}: {e}")
                    # Clean up wrapper script if creation failed
                    if 'wrapper_script' in locals() and os.path.exists(wrapper_script):
                        try:
                            os.unlink(wrapper_script)
                        except:
                            pass
            else:
                # Standard Chrome installation
                chrome_options.binary_location = chrome_path
                try:
                    driver = uc.Chrome(options=chrome_options, browser_executable_path=chrome_path)
                    logger.info(f"ChromeDriver started using browser_executable_path: {chrome_path}")
                    return driver
                except Exception as e:
                    logger.error(f"ChromeDriver failed using path {chrome_path}: {e}")
        else:
            logger.error("No Chrome executable found in known paths or Flatpak installations.")

        raise Exception(
            "[ChromeDriver] Failed to install ChromeDriver. A current version of Chrome was not detected on your system.\n"
            "If you know that Chrome is installed (including Flatpak versions), update Chrome to the latest version. "
            "If the script is still not working, set the path to your Chrome executable manually inside the script.\n"
            "For Flatpak Chrome, ensure you have either 'com.google.Chrome' or 'org.chromium.Chromium' installed."
        )


if __name__ == '__main__':
    create_driver()
