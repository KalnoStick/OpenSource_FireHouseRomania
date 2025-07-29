import os
import logging

# Set up logging FIRST
log_dir = os.path.join(os.getenv('APPDATA'), 'FireHouseRomania')
#log_dir=os.path.abspath("logs")
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, 'app.log')
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)