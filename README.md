## Prerequisites
You need to have MySQL server installed on your device (the project was developed using v. 8.4.0)

The app is built on Python 3.11.8. Some features may function improperly on older versions

## Installation
1\. Install python dependencies.

	pip install -r requirements.txt

2\. Create a config.py file, add your MySQL server host, user, password and a desired db name into it.

	DB_HOST = "localhost"
    DB_USER = "root"
    DB_PASSWORD = "628691"
    DB_NAME = "crypto_data"

3\. Run the main.py script in the project directory.

	python main.py

## Functionality overview

![py_crypto_dashboard](/resources/readme_files/main_page.gif)

### Assets watchlist
 
The assets watchlist displays the current market data for selected assets. The appearance of data can be configured in 
the asset settings window.

![py_crypto_dashboard](/resources/readme_files/watchlist_functionality.gif)

### Adding assets

You can add new assets to the watchlist in the "Add asset" window. It is opened through the sidebar menu.

![py_crypto_dashboard](/resources/readme_files/adding_assets.gif)

### Managing API keys

You can manage your CryptoCompare API keys in the API keys management menu. It is also opened through the sidebar menu.

![py_crypto_dashboard](/resources/readme_files/api_keys_settings.gif)
