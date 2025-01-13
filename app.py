from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def setup_chrome_driver():
    try:
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        logger.info("Installing Chrome driver...")
        service = Service(ChromeDriverManager().install())
        
        logger.info("Creating Chrome driver instance...")
        driver = webdriver.Chrome(service=service, options=options)
        logger.info("Chrome driver setup successful")
        return driver
    except Exception as e:
        logger.error(f"Error setting up Chrome driver: {str(e)}")
        raise

def scrape_github_users(keywords, location=None, language=None, page_count=1):
    logger.info(f"Starting scrape with keywords: {keywords}, location: {location}, language: {language}")
    driver = setup_chrome_driver()
    candidates = []
    
    try:
        # Construct search URL
        base_url = "https://github.com/search?type=users"
        query = f"&q={keywords}"
        if location:
            query += f"+location:{location}"
        if language:
            query += f"+language:{language}"
        
        page_url = f"{base_url}{query}"
        logger.info(f"Accessing URL: {page_url}")
        
        driver.get(page_url)
        time.sleep(3)  # Increased wait time
        
        logger.info("Waiting for user elements...")
        # Wait for user elements to be present
        user_elements = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.user-list-item"))
        )
        logger.info(f"Found {len(user_elements)} user elements")
        
        # Extract information for each user
        for user in user_elements[:10]:
            try:
                logger.info("Extracting user data...")
                username = user.find_element(By.CSS_SELECTOR, "a.mr-1").text
                profile_url = user.find_element(By.CSS_SELECTOR, "a.mr-1").get_attribute("href")
                logger.info(f"Processing user: {username}")
                
                try:
                    bio = user.find_element(By.CSS_SELECTOR, "p.color-fg-muted").text
                except:
                    bio = ""
                    logger.warning(f"No bio found for user {username}")
                
                try:
                    location = user.find_element(By.CSS_SELECTOR, "div.color-fg-muted").text
                except:
                    location = ""
                    logger.warning(f"No location found for user {username}")
                
                # Visit profile page
                logger.info(f"Visiting profile: {profile_url}")
                driver.get(profile_url)
                time.sleep(2)
                
                try:
                    repos = driver.find_element(By.CSS_SELECTOR, "span.Counter").text
                except:
                    repos = "0"
                    logger.warning(f"No repository count found for user {username}")
                
                try:
                    contributions = driver.find_element(
                        By.CSS_SELECTOR, 
                        "h2.f4.text-normal.mb-2"
                    ).text.split()[0]
                except:
                    contributions = "0"
                    logger.warning(f"No contributions found for user {username}")
                
                candidate = {
                    "username": username,
                    "profile_url": profile_url,
                    "bio": bio,
                    "location": location,
                    "repositories": repos,
                    "contributions": contributions
                }
                
                candidates.append(candidate)
                logger.info(f"Successfully added user {username} to candidates")
                
            except Exception as e:
                logger.error(f"Error extracting user data: {str(e)}")
                continue
            
    except Exception as e:
        logger.error(f"Error during scraping: {str(e)}")
        return {"error": str(e)}
        
    finally:
        logger.info("Closing Chrome driver")
        driver.quit()
        
    logger.info(f"Scraping completed. Found {len(candidates)} candidates")
    return candidates

@app.route('/api/search', methods=['POST'])
def search_candidates():
    try:
        data = request.get_json()
        logger.info(f"Received search request with data: {data}")
        
        if not data:
            logger.error("No data provided in request")
            return jsonify({"error": "No data provided"}), 400
            
        keywords = data.get('keywords')
        location = data.get('location')
        language = data.get('language')
        
        if not keywords:
            logger.error("No keywords provided")
            return jsonify({"error": "Keywords are required"}), 400
            
        logger.info("Starting search with parameters: " +
                   f"keywords={keywords}, location={location}, language={language}")
        
        results = scrape_github_users(keywords, location, language)
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Error in search endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/')
def home():
    return app.send_static_file('index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000) 