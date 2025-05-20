import os
import sys
import subprocess
import shutil
import argparse
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("build_exe.log")
    ]
)
logger = logging.getLogger("build_exe")

def check_dependencies():
    """Check if required packages are installed"""
    try:
        import pyinstaller
        logger.info("PyInstaller is installed")
    except ImportError:
        logger.error("PyInstaller is not installed. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    try:
        import vosk
        logger.info("Vosk is installed")
    except ImportError:
        logger.error("Vosk is not installed. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "vosk"])
    
    try:
        import pyaudio
        logger.info("PyAudio is installed")
    except ImportError:
        logger.error("PyAudio is not installed. Installing...")
        
        if sys.platform == 'win32':
            logger.info("Windows platform detected, installing PyAudio via pipwin")
            try:
                import pipwin
            except ImportError:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "pipwin"])
            
            subprocess.check_call([sys.executable, "-m", "pipwin", "install", "pyaudio"])
        else:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyaudio"])

def check_vosk_model(model_path):
    """Check if the Vosk model exists at the specified path"""
    if not os.path.exists(model_path):
        logger.error(f"Vosk model not found at {model_path}")
        return False
    
    try:
        from vosk import Model
        Model(model_path)
        logger.info(f"Vosk model successfully loaded from {model_path}")
        return True
    except Exception as e:
        logger.error(f"Error loading Vosk model: {str(e)}")
        return False

def download_vosk_model(model_name="vosk-model-small-en-us-0.15"):
    """Download a Vosk model if not present"""
    import requests
    import zipfile
    from tqdm import tqdm
    
    model_dir = os.path.join(os.getcwd(), "model")
    
    # Create model directory if it doesn't exist
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)
    
    model_zip = f"{model_name}.zip"
    model_url = f"https://alphacephei.com/vosk/models/{model_zip}"
    model_zip_path = os.path.join(os.getcwd(), model_zip)
    
    # Download the model if not already downloaded
    if not os.path.exists(model_zip_path):
        logger.info(f"Downloading Vosk model from {model_url}")
        try:
            response = requests.get(model_url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024  # 1 Kibibyte
            
            with open(model_zip_path, 'wb') as f, tqdm(
                desc=model_zip,
                total=total_size,
                unit='iB',
                unit_scale=True,
                unit_divisor=1024,
            ) as bar:
                for data in response.iter_content(block_size):
                    size = f.write(data)
                    bar.update(size)
            
            logger.info(f"Model downloaded to {model_zip_path}")
        except Exception as e:
            logger.error(f"Error downloading model: {str(e)}")
            return None
    else:
        logger.info(f"Model already downloaded at {model_zip_path}")
    
    # Extract the model if not already extracted
    extracted_path = os.path.join(model_dir, model_name)
    
    if not os.path.exists(extracted_path):
        logger.info(f"Extracting model to {model_dir}")
        try:
            with zipfile.ZipFile(model_zip_path, 'r') as zip_ref:
                zip_ref.extractall(model_dir)
            logger.info(f"Model extracted to {model_dir}")
        except Exception as e:
            logger.error(f"Error extracting model: {str(e)}")
            return None
    else:
        logger.info(f"Model already extracted at {extracted_path}")
    
    return os.path.join(model_dir, model_name)

def build_executable(script_path, output_name=None, one_file=True, console=False, icon=None, include_model=True, model_path=None):
    """Build executable using PyInstaller"""
    logger.info("Building executable with PyInstaller")
    
    if not output_name:
        output_name = os.path.splitext(os.path.basename(script_path))[0]
    
    pyinstaller_args = [
        "pyinstaller",
        f"--name={output_name}",
        "--clean",
    ]
    
    if one_file:
        pyinstaller_args.append("--onefile")
    
    if not console:
        pyinstaller_args.append("--windowed")
    
    if icon and os.path.exists(icon):
        pyinstaller_args.append(f"--icon={icon}")
    
    # Add model directory if included
    if include_model and model_path and os.path.exists(model_path):
        # Get parent directory of model (typically the "model" folder)
        model_parent = os.path.dirname(model_path)
        model_name = os.path.basename(model_path)
        pyinstaller_args.append(f"--add-data={model_path}{os.pathsep}model/{model_name}")
    
    pyinstaller_args.append(script_path)
    
    try:
        logger.info(f"Running PyInstaller with args: {' '.join(pyinstaller_args)}")
        subprocess.check_call(pyinstaller_args)
        
        dist_path = os.path.join(os.getcwd(), "dist", output_name)
        if one_file:
            dist_path += ".exe" if sys.platform == "win32" else ""
        
        logger.info(f"Executable built successfully: {dist_path}")
        return dist_path
    except subprocess.CalledProcessError as e:
        logger.error(f"Error building executable: {str(e)}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Build Speech-to-Text executable")
    parser.add_argument("--script", default="vosk_speech_to_text.py", help="Path to the Python script")
    parser.add_argument("--output", default=None, help="Output executable name")
    parser.add_argument("--model", default=None, help="Path to Vosk model")
    parser.add_argument("--download-model", action="store_true", help="Download Vosk small model")
    parser.add_argument("--onedir", action="store_true", help="Create a directory instead of a single file")
    parser.add_argument("--console", action="store_true", help="Show console window")
    parser.add_argument("--icon", default=None, help="Path to icon file")
    
    args = parser.parse_args()
    
    # Check for required dependencies
    check_dependencies()
    
    # Handle model
    model_path = args.model
    if args.download_model or not model_path:
        downloaded_model = download_vosk_model()
        if downloaded_model:
            model_path = downloaded_model
    
    # Build executable
    exe_path = build_executable(
        script_path=args.script,
        output_name=args.output,
        one_file=not args.onedir,
        console=args.console,
        icon=args.icon,
        include_model=True if model_path else False,
        model_path=model_path
    )
    
    if exe_path:
        logger.info(f"Build completed successfully. Executable: {exe_path}")
        
        # If using a single file executable, remind about model requirements
        if not args.onedir and model_path:
            logger.info(
                "Note: For the single-file executable, you may need to manually copy "
                f"the model directory to the same location as the executable or "
                "specify the model path when running the application."
            )
    else:
        logger.error("Build failed")

if __name__ == "__main__":
    main()
