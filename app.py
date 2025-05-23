from flask import Flask, render_template, request, send_file, make_response, jsonify
import datetime
import re
import io
import os
import urllib.parse
import uuid
import json

app = Flask(__name__)

# --- Analytics Storage ---
ANALYTICS_FILE = 'analytics_data.json'

def load_analytics_data():
    """Loads analytics data from the JSON file."""
    try:
        with open(ANALYTICS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {} # Return empty dict if file not found or invalid

def save_analytics_data(data):
    """Saves analytics data to the JSON file."""
    try:
        with open(ANALYTICS_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except IOError as e:
        print(f"Error saving analytics data: {e}") # Basic error logging

# Initialize analytics file if it doesn't exist
if not os.path.exists(ANALYTICS_FILE):
    save_analytics_data({})

# Color Palettes
COLOR_PALETTES = {
    "default_dark": {
        "primary": "#00bcd4", "secondary": "#2196f3", "accent": "#7c4dff",
        "dark": "#1a1a2e", "light": "#f0f8ff", "description": "Default Dark (Cyan, Blue, Purple)"
    },
    "futuristic_neon": {
        "primary": "#FF00FF", "secondary": "#00FFFF", "accent": "#FAFAFA", # Magenta, Cyan, White
        "dark": "#1A001A", "light": "#E0E0E0", "description": "Futuristic Neon (Pink, Cyan, Dark)"
    },
    "forest_green": {
        "primary": "#4CAF50", "secondary": "#8BC34A", "accent": "#FFC107", # Green, Light Green, Amber
        "dark": "#303030", "light": "#F5F5F5", "description": "Forest Green (Greens, Amber)"
    },
    "sunset_orange": {
        "primary": "#FF9800", "secondary": "#FF5722", "accent": "#607D8B", # Orange, Deep Orange, Blue Grey
        "dark": "#212121", "light": "#FAFAFA", "description": "Sunset Orange (Oranges, Grey)"
    },
    "ocean_blue": {
        "primary": "#03A9F4", "secondary": "#00BCD4", "accent": "#FFEB3B", # Light Blue, Cyan, Yellow
        "dark": "#263238", "light": "#ECEFF1", "description": "Ocean Blue (Blues, Yellow)"
    },
    "warm_red": {
        "primary": "#F44336", "secondary": "#FF5722", "accent": "#FFC107", # Red, Deep Orange, Amber
        "dark": "#424242", "light": "#FBE9E7", "description": "Warm Red (Reds, Amber)"
    },
    "royal_purple": {
        "primary": "#673AB7", "secondary": "#9C27B0", "accent": "#FFD700", # Deep Purple, Purple, Gold
        "dark": "#311B92", "light": "#EDE7F6", "description": "Royal Purple (Purples, Gold)"
    },
    "grayscale": {
        "primary": "#9E9E9E", "secondary": "#616161", "accent": "#FFFFFF", # Grey, Dark Grey, White
        "dark": "#212121", "light": "#FAFAFA", "description": "Grayscale (Greys, Black/White)"
    }
}

def get_youtube_embed_url(url):
    """Extracts YouTube video ID and returns embed URL."""
    if not url:
        return ""
    
    video_id = None
    try:
        parsed_url = urllib.parse.urlparse(url)
        if parsed_url.hostname == 'youtu.be':
            video_id = parsed_url.path[1:] # Path is /VIDEO_ID
        elif parsed_url.hostname in ('youtube.com', 'www.youtube.com'):
            if parsed_url.path == '/watch':
                query = urllib.parse.parse_qs(parsed_url.query)
                video_id = query.get('v', [None])[0]
            elif parsed_url.path.startswith('/embed/'):
                video_id = parsed_url.path.split('/')[2]
            elif parsed_url.path.startswith('/v/'):
                video_id = parsed_url.path.split('/')[2]
        
        # Basic check for valid ID format (alphanumeric, -, _)
        if video_id and re.match(r'^[A-Za-z0-9_\-]+$', video_id):
            return f"https://www.youtube.com/embed/{video_id}"
    except Exception:
        # Ignore parsing errors
        pass
    
    return "" # Return empty if no valid ID found

def generate_vcard_filename(contact_name, company_name):
    """Generates a clean filename for the vCard."""
    base_name = f"{contact_name} {company_name} Contact"
    clean_name = re.sub(r'[^a-zA-Z0-9\s-]', '', base_name)
    final_name = re.sub(r'\s+', '-', clean_name)
    return f"{final_name}.vcf"

@app.route('/')
def index():
    """Displays the form to input details."""
    return render_template('index.html', palettes=COLOR_PALETTES)

@app.route('/generate', methods=['POST'])
def generate_html():
    """Generates the HTML file based on form input."""
    # --- Get Form Data --- 
    data = request.form
    
    # --- Determine Selected Palette Colors ---
    selected_palette_name = data.get('color_palette', 'default_dark') 
    selected_palette = {}
    default_palette_colors = COLOR_PALETTES['default_dark'] # For fallback

    if selected_palette_name == 'custom':
        # Basic hex color validation regex (allows #RGB and #RRGGBB)
        hex_pattern = re.compile(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$')
        
        def get_custom_color(key):
            custom_val = data.get(f'custom_{key}')
            if custom_val and hex_pattern.match(custom_val):
                return custom_val
            return default_palette_colors[key] # Fallback to default dark

        selected_palette = {
            'primary': get_custom_color('primary'),
            'secondary': get_custom_color('secondary'),
            'accent': get_custom_color('accent'),
            'dark': get_custom_color('dark'),
            'light': get_custom_color('light'),
        }
    else:
        # Use predefined palette (fallback to default if name is invalid for some reason)
        selected_palette = COLOR_PALETTES.get(selected_palette_name, default_palette_colors)

    # --- Get Remaining Form Data ---
    company_name = data.get('company_name', 'Your Company') # Add defaults just in case
    tagline = data.get('tagline', 'Your Tagline')
    contact_name = data.get('contact_name', 'Your Name')
    phone_raw = data.get('phone_raw', '+1000000000')
    phone_display = data.get('phone_display') or phone_raw # Default to raw if empty
    email = data.get('email', 'email@example.com')
    address = data.get('address', 'Your City, Your Country')
    maps_url = data.get('maps_url') or "https://www.google.com/maps" # Default if empty
    website_url = data.get('website_url', 'https://example.com')
    website_display = data.get('website_display') or website_url.replace('https://','').replace('http://','') # Default if empty

    # Social Media
    instagram_username = data.get('instagram_username', '')
    facebook_username = data.get('facebook_username', '')
    tiktok_username = data.get('tiktok_username', '')
    youtube_handle = data.get('youtube_handle', '')
    linkedin_profile_name = data.get('linkedin_profile_name', '')

    # Social Media Visibility Flags
    show_instagram = data.get('show_instagram') == 'true' and bool(instagram_username) # Only show if checked AND username provided
    show_facebook = data.get('show_facebook') == 'true' and bool(facebook_username)
    show_tiktok = data.get('show_tiktok') == 'true' and bool(tiktok_username)
    show_youtube = data.get('show_youtube') == 'true' and bool(youtube_handle)
    show_linkedin = data.get('show_linkedin') == 'true' and bool(linkedin_profile_name)

    # Construct Social URLs (only construct if needed, otherwise default to #)
    instagram_url = f"https://www.instagram.com/{instagram_username}/" if show_instagram else "#"
    facebook_url = f"https://www.facebook.com/{facebook_username}/" if show_facebook else "#"
    if tiktok_username and not tiktok_username.startswith('@'):
        tiktok_username = '@' + tiktok_username
    tiktok_url = f"https://www.tiktok.com/{tiktok_username}" if show_tiktok else "#"
    if youtube_handle and not youtube_handle.startswith('@'):
         # Ensure the handle starts with @ (form validation should also help)
         youtube_handle = '@' + youtube_handle
    youtube_url = f"https://www.youtube.com/{youtube_handle}" if show_youtube else "#"
    linkedin_url = f"https://www.linkedin.com/in/{linkedin_profile_name}/" if show_linkedin else "#"

    # Content Sections
    hero_headline = data.get('hero_headline', 'Your Headline')
    hero_description = data.get('hero_description', 'Your description here.')
    image_url = data.get('image_url', '') # Needs a default or validation
    image_alt = data.get('image_alt') or f"{company_name} Image" # Default if empty
    feature1_title = data.get('feature1_title', 'Feature 1')
    feature1_desc = data.get('feature1_desc', 'Description 1')
    feature2_title = data.get('feature2_title', 'Feature 2')
    feature2_desc = data.get('feature2_desc', 'Description 2')
    feature3_title = data.get('feature3_title', 'Feature 3')
    feature3_desc = data.get('feature3_desc', 'Description 3')
    contact_prompt = data.get('contact_prompt', 'Get in touch!')
    # Feature Icons (add defaults)
    feature1_icon = data.get('feature1_icon', 'fas fa-check-circle')
    feature2_icon = data.get('feature2_icon', 'fas fa-cog')
    feature3_icon = data.get('feature3_icon', 'fas fa-lightbulb')

    # Add youtube video url
    youtube_video_url = data.get('youtube_video_url', '')
    youtube_video_embed_url = get_youtube_embed_url(youtube_video_url)

    # --- Prepare Placeholder Dictionary ---
    current_year = datetime.datetime.now().year
    full_contact_name = f"{contact_name} - {company_name}"
    vcard_filename = generate_vcard_filename(contact_name, company_name)

    # --- Generate Unique ID and Dashboard URL ---
    page_id = str(uuid.uuid4())
    dashboard_url = f"/dashboard/{page_id}"

    # --- Prepare Context for Jinja Rendering ---
    template_context = {
        "PAGE_ID": page_id,
        "COMPANY_NAME": company_name,
        "TAGLINE": tagline,
        "CONTACT_NAME": contact_name,
        "FULL_CONTACT_NAME": full_contact_name,
        "PHONE_NUMBER_RAW": phone_raw,
        "PHONE_NUMBER_DISPLAY": phone_display,
        "EMAIL_ADDRESS": email,
        "ADDRESS": address,
        "MAPS_URL": maps_url,
        "WEBSITE_URL": website_url,
        "WEBSITE_DISPLAY": website_display,
        "INSTAGRAM_URL": instagram_url,
        "FACEBOOK_URL": facebook_url,
        "TIKTOK_URL": tiktok_url,
        "YOUTUBE_URL": youtube_url,
        "LINKEDIN_URL": linkedin_url,
        "HERO_HEADLINE": hero_headline,
        "HERO_DESCRIPTION": hero_description,
        "IMAGE_URL": image_url,
        "IMAGE_ALT": image_alt,
        "FEATURE1_TITLE": feature1_title,
        "FEATURE1_DESCRIPTION": feature1_desc,
        "FEATURE2_TITLE": feature2_title,
        "FEATURE2_DESCRIPTION": feature2_desc,
        "FEATURE3_TITLE": feature3_title,
        "FEATURE3_DESCRIPTION": feature3_desc,
        "YOUTUBE_VIDEO_EMBED_URL": youtube_video_embed_url,
        "CONTACT_PROMPT": contact_prompt,
        "VCARD_FILENAME": vcard_filename,
        "FEATURE1_ICON": feature1_icon,
        "FEATURE2_ICON": feature2_icon,
        "FEATURE3_ICON": feature3_icon,
        "CURRENT_YEAR": str(current_year),
        "COLOR_PRIMARY": selected_palette['primary'],
        "COLOR_SECONDARY": selected_palette['secondary'],
        "COLOR_ACCENT": selected_palette['accent'],
        "COLOR_DARK": selected_palette['dark'],
        "COLOR_LIGHT": selected_palette['light'],
        "SHOW_INSTAGRAM": show_instagram,
        "SHOW_FACEBOOK": show_facebook,
        "SHOW_TIKTOK": show_tiktok,
        "SHOW_YOUTUBE": show_youtube,
        "SHOW_LINKEDIN": show_linkedin,
    }

    # --- Render Template using Jinja ---
    try:
        generated_content = render_template('template.html', **template_context)
    except Exception as e:
        # Consider more specific error handling/logging
        return f"Error rendering template.html: {e}", 500

    # --- Render Results Page --- 
    output_filename = "generated_page.html"
    return render_template('results.html', 
                           generated_html=generated_content, 
                           filename=output_filename,
                           dashboard_url=dashboard_url)

# Add a route to handle the download from the results page
@app.route('/download', methods=['POST'])
def download_html():
    html_content = request.form.get('html_content', '')
    filename = request.form.get('filename', 'generated_page.html')

    # Create an in-memory bytes buffer
    bytes_buffer = io.BytesIO(html_content.encode('utf-8'))

    response = make_response(send_file(
        bytes_buffer,
        mimetype='text/html',
        as_attachment=True,
        download_name=filename
    ))
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response

# --- Analytics Routes ---

@app.route('/track_click', methods=['POST'])
def track_click():
    data = request.get_json()
    if not data or 'page_id' not in data or 'link_type' not in data:
        return jsonify(success=False, error='Missing data'), 400

    page_id = data['page_id']
    link_type = data['link_type']

    analytics_data = load_analytics_data()

    # Ensure page_id exists
    if page_id not in analytics_data:
        analytics_data[page_id] = {}

    # Increment count for the link_type
    analytics_data[page_id][link_type] = analytics_data[page_id].get(link_type, 0) + 1

    save_analytics_data(analytics_data)

    return jsonify(success=True)

@app.route('/dashboard/<page_id>')
def dashboard(page_id):
    analytics_data = load_analytics_data()
    page_stats = analytics_data.get(page_id, {}) # Get stats or empty dict if page not tracked yet
    # Add page_id itself to the context for display
    return render_template('dashboard.html', page_id=page_id, stats=page_stats)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000)) # Get port from environment or default to 5000
    app.run(host='0.0.0.0', port=port, debug=False) # Listen on 0.0.0.0 and disable debug for production 
