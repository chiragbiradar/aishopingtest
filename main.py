import streamlit as st
import serpapi
from serpapi import GoogleSearch
import openai
import re
from datetime import datetime
from dotenv import load_dotenv
import os

# Load environment variables from a .env file
load_dotenv()

# Set up page configuration
st.set_page_config(page_title="Indian Smart Shopping Assistant", layout="wide")

# Set up API keys
# In a production app, use st.secrets to securely store API keys
if "SERPAPI_KEY" not in st.session_state:
    st.session_state["SERPAPI_KEY"] = os.getenv("SERPAPI_KEY")  # Load from environment variable

if "OPENAI_API_KEY" not in st.session_state:
    st.session_state["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")  # Load from environment variable

# Initialize OpenAI client
openai.api_key = st.session_state["OPENAI_API_KEY"]

# Function to extract price range from user preferences
def extract_price_range(user_preferences):
    # Look for price ranges like "₹50,000-₹1,00,000" or "between ₹50,000 and ₹1,00,000"
    # Also handle prices without ₹ symbol
    price_pattern = r'(?:between\s+)?(?:₹)?(\d+[,\d]*(?:\.\d+)?)\s*(?:to|-|and)\s*(?:₹)?(\d+[,\d]*(?:\.\d+)?)'
    match = re.search(price_pattern, user_preferences, re.IGNORECASE)
    
    if match:
        min_price = match.group(1).replace(',', '')
        max_price = match.group(2).replace(',', '')
        return float(min_price), float(max_price)
    return None, None

# Function to build search query based on user preferences
def build_search_query(base_product, user_preferences):
    query = base_product
    
    # Extract key features from user preferences to enhance search
    if "pro" in user_preferences.lower():
        query += " Pro"
    if "air" in user_preferences.lower():
        query += " Air"
    if "16" in user_preferences or "16-inch" in user_preferences.lower():
        query += " 16-inch"
    if "14" in user_preferences or "14-inch" in user_preferences.lower():
        query += " 14-inch"
    if "13" in user_preferences or "13-inch" in user_preferences.lower():
        query += " 13-inch"
    
    # Add storage specifications if mentioned
    if "512" in user_preferences:
        query += " 512GB"
    elif "1tb" in user_preferences.lower() or "1 tb" in user_preferences.lower():
        query += " 1TB"
    elif "2tb" in user_preferences.lower() or "2 tb" in user_preferences.lower():
        query += " 2TB"
    
    # Add RAM specifications if mentioned
    if "16gb" in user_preferences.lower() or "16 gb" in user_preferences.lower():
        query += " 16GB"
    elif "32gb" in user_preferences.lower() or "32 gb" in user_preferences.lower():
        query += " 32GB"
    
    # Check for color preferences
    colors = ["silver", "space grey", "space gray", "gold", "black", "white", "blue", "green", "purple", "red"]
    for color in colors:
        if color in user_preferences.lower():
            query += f" {color}"
    
    return query

# Function to check if a price is available
def price_available(price_str):
    if not price_str or price_str == "N/A":
        return False
    return True

# Function to convert price to INR if not already (assuming most prices will already be in INR from API)
def ensure_rupee_format(price_str):
    if not price_str or price_str == "N/A":
        return "N/A"
    
    # If price doesn't start with ₹, add it
    if not price_str.startswith("₹"):
        price_str = f"₹{price_str}"
    
    # If price contains $ or other currency symbols, attempt conversion (simplified)
    if "$" in price_str:
        # Extract numeric value
        price_value = re.search(r'[\d,]+\.?\d*', price_str)
        if price_value:
            # Simple conversion rate - in reality, would use an API
            usd_to_inr = 83.5  # Example rate as of April 2025
            try:
                price_in_usd = float(price_value.group().replace(',', ''))
                price_in_inr = price_in_usd * usd_to_inr
                price_str = f"₹{price_in_inr:,.2f}"
            except:
                pass
    
    return price_str

# Function to fetch shopping results using SerpAPI
def fetch_shopping_results(query, min_price=None, max_price=None):
    """Fetch shopping results from Google Shopping using SerpAPI with India as location."""
    try:
        params = {
            "engine": "google_shopping",
            "q": query,
            "api_key": st.session_state["SERPAPI_KEY"],
            "location": "New Delhi,Delhi,India",  # Set location to India
            "gl": "in",  # Google country code for India
            "hl": "en",  # Language (English)
            "currency": "INR"  # Set currency to Indian Rupees
        }
        
        # Add price filtering if provided
        if min_price is not None and max_price is not None:
            params["price_range"] = f"{min_price},{max_price}"
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        # Process shopping results to ensure prices are in rupees
        shopping_results = results.get("shopping_results", [])
        for result in shopping_results:
            if "price" in result:
                result["price"] = ensure_rupee_format(result["price"])
            if "old_price" in result:
                result["old_price"] = ensure_rupee_format(result["old_price"])
        
        return shopping_results
    except Exception as e:
        st.error(f"Error fetching shopping results: {e}")
        return []

# Function to filter results by user preferences
def filter_results(products, user_preferences):
    """Filter products based on detailed user preferences."""
    filtered_products = []
    preferences_lower = user_preferences.lower()
    
    for product in products:
        title_lower = product.get("title", "").lower()
        source_lower = product.get("source", "").lower()
        score = 0
        
        # Score products based on matching preferences
        if "pro" in preferences_lower and "pro" in title_lower:
            score += 5
        if "air" in preferences_lower and "air" in title_lower:
            score += 5
            
        # Screen size preference
        if "16" in preferences_lower and ("16" in title_lower or "16-inch" in title_lower):
            score += 4
        if "14" in preferences_lower and ("14" in title_lower or "14-inch" in title_lower):
            score += 4
        if "13" in preferences_lower and ("13" in title_lower or "13-inch" in title_lower):
            score += 4
            
        # Storage preference
        if "512" in preferences_lower and "512" in title_lower:
            score += 3
        if ("1tb" in preferences_lower or "1 tb" in preferences_lower) and ("1tb" in title_lower or "1 tb" in title_lower):
            score += 3
        if ("2tb" in preferences_lower or "2 tb" in preferences_lower) and ("2tb" in title_lower or "2 tb" in title_lower):
            score += 3
            
        # RAM preference
        if ("16gb" in preferences_lower or "16 gb" in preferences_lower) and ("16gb" in title_lower or "16 gb" in title_lower):
            score += 2
        if ("32gb" in preferences_lower or "32 gb" in preferences_lower) and ("32gb" in title_lower or "32 gb" in title_lower):
            score += 2
        
        # Color preferences
        colors = ["silver", "space grey", "space gray", "gold", "black", "white", "blue", "green", "purple", "red"]
        for color in colors:
            if color in preferences_lower and color in title_lower:
                score += 3
        
        # Preferred sellers in India
        preferred_sellers = ["amazon", "flipkart", "croma", "vijay sales", "reliance digital", "apple"]
        for seller in preferred_sellers:
            if seller in source_lower:
                score += 3
                
        # Exclude refurbished or used if looking for new
        if "new" in preferences_lower and ("refurbished" in title_lower or "used" in title_lower):
            score -= 10
            
        # Add product with its score
        product["match_score"] = score
        filtered_products.append(product)
    
    # Sort by matching score (descending)
    return sorted(filtered_products, key=lambda x: x.get("match_score", 0), reverse=True)

# Function to generate AI summary and recommendations with India-specific context
def generate_summary(products, user_preferences):
    """Generate an AI summary of the products using OpenAI API with Indian context."""
    try:
        # Create a detailed prompt about the products
        product_details = ""
        for i, product in enumerate(products[:10], 1):
            title = product.get("title", "N/A")
            price = product.get("price", "N/A")
            source = product.get("source", "N/A")
            rating = product.get("rating", "N/A")
            score = product.get("match_score", 0)
            product_details += f"{i}. Title: {title}, Price: {price}, Source: {source}, Rating: {rating}, Match Score: {score}/20\n"
        
        # Get current date for timeliness of recommendations
        current_date = datetime.now().strftime("%d %B, %Y")
        
        # Use chat completions API with Indian context
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful shopping assistant for Indian customers. Provide insights specific to the Indian market, including value for money analysis in the Indian context, local availability, and popular sellers like Amazon.in, Flipkart, etc. Always mention prices in rupees (₹)."},
                {"role": "user", "content": f"Today is {current_date}. An Indian customer has the following preferences: {user_preferences}\n\nHere are some relevant products available in India:\n\n{product_details}\n\nPlease provide a personalized summary (2-3 paragraphs) including:\n1. The price range in rupees and key features across these products\n2. Which products best match the user's preferences considering the Indian market\n3. Your top 1-2 recommendations based on value for money in India and feature match\n4. Any relevant information about warranties, EMI options, or special offers if applicable"}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        # Extract the content from the message
        return response.choices[0].message["content"].strip()
    except Exception as e:
        st.error(f"Error generating AI summary: {e}")
        return "Unable to generate summary."

# Helper function to ask follow-up questions for Indian market
def get_follow_up_questions(base_product):
    """Generate follow-up questions based on the product category with Indian market context."""
    if "macbook" in base_product.lower():
        return [
            "Do you prefer MacBook Pro or MacBook Air?",
            "What screen size are you looking for? (13-inch, 14-inch, 16-inch)",
            "How much storage do you need? (256GB, 512GB, 1TB)",
            "What's your budget range in rupees? (e.g., ₹90,000-₹1,50,000)",
            "Any specific RAM requirements? (8GB, 16GB, 32GB)",
            "Do you prefer any particular color? (Silver, Space Grey, Gold)",
            "Are you looking for new or refurbished?",
            "Do you have any preferred seller? (Amazon, Flipkart, Apple Store, Croma, etc.)",
            "Do you need EMI options?"
        ]
    elif "iphone" in base_product.lower():
        return [
            "Which iPhone model are you interested in? (e.g., 14, 15, Pro, Pro Max)",
            "What storage capacity do you need? (128GB, 256GB, 512GB, 1TB)",
            "What's your budget range in rupees?",
            "Do you have a color preference?",
            "Are you looking for new or refurbished?",
            "Do you have any preferred seller? (Amazon, Flipkart, Apple Store, Croma, etc.)",
            "Are you interested in exchange offers?",
            "Do you need EMI options?"
        ]
    else:
        return [
            "What's your budget range in rupees?",
            "Any specific features you're looking for?",
            "Do you have a brand preference?",
            "Are you looking for new or refurbished items?",
            "Do you have any preferred seller? (Amazon, Flipkart, etc.)",
            "Do you need EMI options?",
            "Is warranty an important factor for you?"
        ]

# Generate personalized greeting based on time of day
def get_greeting():
    hour = datetime.now().hour
    if 4 <= hour < 12:
        return "Good morning"
    elif 12 <= hour < 17:
        return "Good afternoon"
    elif 17 <= hour < 22:
        return "Good evening"
    else:
        return "Hello"

# Function to show payment/EMI options
def show_payment_options(price_str):
    if price_str == "N/A":
        return
    
    try:
        # Extract numeric price
        price_value = re.search(r'[\d,]+\.?\d*', price_str)
        if price_value:
            price = float(price_value.group().replace(',', ''))
            
            # Show EMI options
            st.markdown("##### EMI Options:")
            
            # Calculate some sample EMI options
            for months in [3, 6, 9, 12]:
                # Simple calculation (no interest for simplicity)
                monthly = price / months
                st.text(f"₹{monthly:,.2f}/month for {months} months")
            
            # Show bank offers
            st.markdown("##### Bank Offers:")
            st.text("10% instant discount with HDFC cards")
            st.text("5% cashback with Amazon Pay ICICI card")
    except:
        pass

# Main Streamlit app
st.title("🛍️ Indian Smart Shopping Assistant")
st.markdown(f"### {get_greeting()}! Find your perfect product at the best price")

# Set up custom theme with Indian flag colors
st.markdown("""
    <style>
    .main {
        background-color: #f9f9f9;
    }
    .stButton>button {
        background-color: #FF9933;
        color: white;
    }
    .stProgress > div > div {
        background-color: #138808;
    }
    h1, h2, h3 {
        color: #000080;
    }
    .price-tag {
        color: #FF9933;
        font-weight: bold;
        font-size: 1.5rem;
    }
    .discount {
        color: #138808;
        font-weight: bold;
    }
    .seller-tag {
        background-color: #f0f0f0;
        padding: 2px 5px;
        border-radius: 3px;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize session state for user preferences if not already done
if "user_preferences" not in st.session_state:
    st.session_state["user_preferences"] = ""
if "search_performed" not in st.session_state:
    st.session_state["search_performed"] = False
if "filtered_products" not in st.session_state:
    st.session_state["filtered_products"] = []
if "original_query" not in st.session_state:
    st.session_state["original_query"] = ""
if "user_name" not in st.session_state:
    st.session_state["user_name"] = ""

# Get user name for personalization
if not st.session_state["user_name"]:
    user_name = st.text_input("Your Name (for personalized recommendations)", placeholder="Optional")
    if user_name:
        st.session_state["user_name"] = user_name
        st.success(f"Hi {user_name}! Let's find you the perfect product.")

# Step 1: Ask for the base product
base_product = st.text_input("What product are you looking for?", placeholder="e.g., MacBook M3, iPhone 15")

if base_product and not st.session_state["search_performed"]:
    st.session_state["original_query"] = base_product
    
    # Step 2: Ask follow-up questions for preferences
    st.markdown("### Tell us more about your preferences")
    
    # Display multiple choice and text input options for preferences
    col1, col2 = st.columns(2)
    
    with col1:
        follow_up_questions = get_follow_up_questions(base_product)
        for i in range(0, len(follow_up_questions), 2):
            if i < len(follow_up_questions):
                st.text_input(follow_up_questions[i], key=f"q{i}")
    
    with col2:
        for i in range(1, len(follow_up_questions), 2):
            if i < len(follow_up_questions):
                st.text_input(follow_up_questions[i], key=f"q{i}")
    
    # Collect all preferences into one string
    if st.button("Find Products"):
        preferences = ""
        for i in range(len(follow_up_questions)):
            if f"q{i}" in st.session_state and st.session_state[f"q{i}"]:
                preferences += follow_up_questions[i] + ": " + st.session_state[f"q{i}"] + ". "
        
        # Add user name to preferences if available
        if st.session_state["user_name"]:
            preferences += f" For user: {st.session_state['user_name']}."
        
        st.session_state["user_preferences"] = preferences
        
        # Extract price range
        min_price, max_price = extract_price_range(preferences)
        
        # Build search query based on preferences
        search_query = build_search_query(base_product, preferences)
        
        # Fetch results
        with st.spinner("Searching for the best products in India..."):
            products = fetch_shopping_results(search_query, min_price, max_price)
            
            if products:
                # Filter and sort results based on user preferences
                filtered_products = filter_results(products, preferences)
                st.session_state["filtered_products"] = filtered_products
                st.session_state["search_performed"] = True
                st.rerun()
            else:
                st.error("No products found. Try different search terms or preferences.")

# Display results if search was performed
if st.session_state["search_performed"]:
    products = st.session_state["filtered_products"]
    user_preferences = st.session_state["user_preferences"]
    
    # Reset button
    if st.button("Start New Search"):
        st.session_state["search_performed"] = False
        st.session_state["user_preferences"] = ""
        st.session_state["filtered_products"] = []
        st.session_state["original_query"] = ""
        st.rerun()
    
    # Personalized greeting
    if st.session_state["user_name"]:
        st.markdown(f"### {st.session_state['user_name']}, here are your personalized results")
    
    # Display AI summary at the top
    with st.spinner("Analyzing products for you..."):
        if products:
            summary = generate_summary(products, user_preferences)
            st.markdown("### 🧠 AI Shopping Analysis")
            st.markdown(summary)
            st.markdown("---")
    
    # Show products
    st.markdown(f"### Top Products Based On Your Preferences")
    st.markdown(f"Showing results for: **{st.session_state['original_query']}** with your preferences")
    
    # Create tabs for different views
    tab1, tab2 = st.tabs(["Card View", "Detailed View"])
    
    with tab1:
        # Card view - Display products in a scrollable container
        for i, product in enumerate(products[:15]):  # Limit to top 15 matches
            title = product.get("title", "N/A")
            source = product.get("source", "N/A")
            price = product.get("price", "N/A")
            old_price = product.get("old_price", None)
            rating = product.get("rating", "N/A")
            reviews = product.get("reviews", "N/A")
            thumbnail = product.get("thumbnail", "")
            link = product.get("link", "#")
            match_score = product.get("match_score", 0)
            extensions = product.get("extensions", [])
            
            # Create card-like layout
            col1, col2, col3 = st.columns([1, 3, 1])
            
            with col1:
                if thumbnail:
                    st.image(thumbnail, width=100)
                    
                    # Display match score as a progress bar
                    match_percentage = min(100, int(match_score / 20 * 100))
                    st.progress(match_percentage / 100)
                    st.caption(f"Match: {match_percentage}%")
                    
                    # Show seller badge
                    st.markdown(f"<span class='seller-tag'>{source}</span>", unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"#### [{title}]({link})")
                
                if rating != "N/A":
                    st.markdown(f"**Rating:** {rating} ({'No reviews' if reviews == 'N/A' else f'{reviews} reviews'})")
                
                # Show product features if available
                if extensions:
                    st.markdown("**Features:** " + ", ".join(extensions[:3]))
            
            with col3:
                # Show current price with ₹ symbol if not already present
                formatted_price = price
                st.markdown(f"<p class='price-tag'>{formatted_price}</p>", unsafe_allow_html=True)
                
                # Show old price and calculate discount if available
                if old_price:
                    st.markdown(f"<s>{old_price}</s>", unsafe_allow_html=True)
                    
                    # Try to calculate discount percentage
                    try:
                        price_val = float(re.sub(r'[^\d.]', '', price))
                        old_price_val = float(re.sub(r'[^\d.]', '', old_price))
                        if old_price_val > price_val:
                            discount = ((old_price_val - price_val) / old_price_val) * 100
                            st.markdown(f"<span class='discount'>{discount:.0f}% off</span>", unsafe_allow_html=True)
                    except:
                        pass
                
                # EMI options button
                if st.button("EMI Options", key=f"emi_{i}"):
                    show_payment_options(price)
                
                # View product button
                st.markdown(f"[View on {source}]({link})")
            
            st.markdown("---")
    
    with tab2:
        # Detailed view - More comprehensive information
        for i, product in enumerate(products[:10]):  # Limit to top 10 matches
            title = product.get("title", "N/A")
            source = product.get("source", "N/A")
            price = product.get("price", "N/A")
            old_price = product.get("old_price", None)
            rating = product.get("rating", "N/A")
            reviews = product.get("reviews", "N/A")
            thumbnail = product.get("thumbnail", "")
            link = product.get("link", "#")
            match_score = product.get("match_score", 0)
            extensions = product.get("extensions", [])
            
            st.markdown(f"### {i+1}. {title}")
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                if thumbnail:
                    st.image(thumbnail, width=200)
            
            with col2:
                # Price information
                st.markdown(f"<p class='price-tag'>{price}</p>", unsafe_allow_html=True)
                
                if old_price:
                    st.markdown(f"<s>{old_price}</s>", unsafe_allow_html=True)
                    
                    # Try to calculate discount percentage
                    try:
                        price_val = float(re.sub(r'[^\d.]', '', price))
                        old_price_val = float(re.sub(r'[^\d.]', '', old_price))
                        if old_price_val > price_val:
                            discount = ((old_price_val - price_val) / old_price_val) * 100
                            st.markdown(f"<span class='discount'>{discount:.0f}% off</span>", unsafe_allow_html=True)
                    except:
                        pass
                
                # Seller and rating information
                st.markdown(f"**Seller:** {source}")
                if rating != "N/A":
                    st.markdown(f"**Rating:** {rating} ({'No reviews' if reviews == 'N/A' else f'{reviews} reviews'})")
                
                # Match score
                match_percentage = min(100, int(match_score / 20 * 100))
                st.markdown(f"**Match Score:** {match_percentage}%")
                st.progress(match_percentage / 100)
                
                # View button
                st.markdown(f"[View on {source}]({link})")
            
            # Show all features and specifications
            st.markdown("#### Product Features")
            if extensions:
                for feature in extensions:
                    st.markdown(f"- {feature}")
            else:
                st.markdown("No detailed features available")
            
            # Show payment options
            st.markdown("#### Payment Options")
            show_payment_options(price)
            
            # Add compare button (placeholder functionality)
            if st.button("Add to Compare", key=f"compare_{i}"):
                st.info("Product added to comparison list! Compare feature will be available soon.")
            
            st.markdown("---")
    
    # Show related searches and recommendations (placeholder)
    st.markdown("### You may also like")
    cols = st.columns(4)
    for i, col in enumerate(cols):
        with col:
            st.markdown(f"Similar Product {i+1}")
            st.image("/api/placeholder/150/150", width=100)
            st.markdown("₹XX,XXX")
            
    # Shopping tips specific to Indian context
    st.markdown("---")
    st.markdown("### Indian Shopping Tips")
    st.info("""
    - Check for Bank Offers: Many Indian e-commerce sites offer special discounts with specific bank cards
    - Compare across sellers: Prices often vary between Amazon, Flipkart, Croma, and Reliance Digital
    - Look for exchange offers: Many retailers offer discounts for exchanging old devices
    - GST is included: All prices shown include GST (Goods and Services Tax)
    """)
