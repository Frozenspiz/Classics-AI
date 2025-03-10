import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import os
import re
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pytube
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import json

# Page configuration
st.set_page_config(
    page_title="ClassicsAI Music Player",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for classical theme
def apply_classical_theme():
    # Define classical theme colors
    PARCHMENT_LIGHT = "#F5F2E9"
    PARCHMENT = "#EAE6D9"
    GOLD = "#D4AF37"
    BURGUNDY = "#800020"
    DARK_BROWN = "#3A2718"
    
    # Apply CSS
    st.markdown(f"""
    <style>
        .stApp {{
            background-color: {PARCHMENT};
        }}
        .stTabs [data-baseweb="tab-list"] {{
            background-color: {BURGUNDY};
            border-radius: 8px 8px 0px 0px;
        }}
        .stTabs [data-baseweb="tab"] {{
            color: {PARCHMENT_LIGHT};
            font-family: 'Garamond', serif;
        }}
        .stTabs [aria-selected="true"] {{
            background-color: {GOLD};
            color: {DARK_BROWN};
            font-weight: bold;
        }}
        h1, h2, h3 {{
            font-family: 'Garamond', serif;
            color: {DARK_BROWN};
        }}
        .playlist-item {{
            background-color: {PARCHMENT_LIGHT};
            border: 1px solid {GOLD};
            border-radius: 5px;
            padding: 10px;
            margin: 5px 0;
        }}
        .playlist-title {{
            background-color: {BURGUNDY};
            color: {PARCHMENT_LIGHT};
            padding: 5px 10px;
            border-radius: 5px 5px 0 0;
            font-family: 'Garamond', serif;
            font-weight: bold;
        }}
        .stButton button {{
            background-color: {GOLD};
            color: {DARK_BROWN};
            font-family: 'Garamond', serif;
            border: none;
            border-radius: 5px;
        }}
        .stButton button:hover {{
            background-color: {BURGUNDY};
            color: {PARCHMENT_LIGHT};
        }}
        .search-result {{
            border-left: 3px solid {GOLD};
            padding-left: 10px;
            margin: 10px 0;
        }}
        .decorative-header {{
            background-color: {GOLD};
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 20px;
            text-align: center;
        }}
        .decorative-header h1 {{
            color: {DARK_BROWN};
            margin: 0;
            font-size: 2.5em;
        }}
        .decorative-header p {{
            color: {DARK_BROWN};
            font-style: italic;
            margin: 5px 0 0 0;
        }}
        .stTextInput input, .stSelectbox, .stMultiselect {{
            background-color: {PARCHMENT_LIGHT};
            border: 1px solid {GOLD};
        }}
    </style>
    """, unsafe_allow_html=True)

# Apply classical theme
apply_classical_theme()

# Create decorative header with musical notes
def create_decorative_header():
    # Create a decorative header with musical notes
    header_html = """
    <div class="decorative-header">
        <h1>♪ ClassicsAI Music Player ♪</h1>
        <p>AI-Generated Classical Music from YouTube</p>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)

# Authentication Helper Functions
def save_config(config):
    """Save updated config to yaml file"""
    with open("config.yaml", 'w') as file:
        yaml.dump(config, file, default_flow_style=False)

def register_user(username, email, password):
    """Register a new user and add to config.yaml"""
    if os.path.exists("config.yaml"):
        with open("config.yaml") as file:
            config = yaml.load(file, Loader=SafeLoader)
        
        # Check if username already exists
        if username in config["credentials"]["usernames"]:
            return False, "Username already exists"
        
        # Check if email already exists
        for user_data in config["credentials"]["usernames"].values():
            if user_data["email"] == email:
                return False, "Email already exists"
        
        # Hash the password
        hashed_password = stauth.Hasher([password]).generate()[0]
        
        # Add the new user
        config["credentials"]["usernames"][username] = {
            "email": email,
            "name": username,  # Use username as the name
            "password": hashed_password
        }
        
        # Add to preauthorized emails if not already there
        if email not in config["preauthorized"]["emails"]:
            config["preauthorized"]["emails"].append(email)
        
        # Save updated config
        save_config(config)
        return True, "Registration successful"
    else:
        return False, "Configuration file not found"

# Authentication
def get_authenticator():
    if os.path.exists("config.yaml"):
        with open("config.yaml") as file:
            config = yaml.load(file, Loader=SafeLoader)
            
        authenticator = stauth.Authenticate(
            config["credentials"],
            config["cookie"]["name"],
            config["cookie"]["key"],
            config["cookie"]["expiry_days"],
            config["preauthorized"]
        )
        return authenticator
    else:
        st.error("Configuration file not found. Please create a config.yaml file.")
        return None

# YouTube API setup
def get_youtube_api():
    try:
        # Try to get API key from environment variable
        api_key = os.environ.get("YOUTUBE_API_KEY")
        
        # If not found in environment, check Streamlit secrets
        if not api_key and hasattr(st, 'secrets') and 'YOUTUBE_API_KEY' in st.secrets:
            api_key = st.secrets["YOUTUBE_API_KEY"]
            
        # If still not found, show a clear error message
        if not api_key:
            st.error("""
            YouTube API key not found. Please set up your API key using one of these methods:
            
            1. Set an environment variable named YOUTUBE_API_KEY
            2. Add it to your Streamlit secrets.toml file
            3. Deploy to Streamlit Cloud and add YOUTUBE_API_KEY to your app secrets
            
            To get a YouTube API key:
            1. Go to https://console.cloud.google.com/
            2. Create a project
            3. Enable the YouTube Data API v3
            4. Create an API key
            """)
            return None
            
        youtube = build("youtube", "v3", developerKey=api_key)
        return youtube
    except Exception as e:
        st.error(f"Error initializing YouTube API: {str(e)}")
        return None

# Extract video ID from YouTube URL
def extract_video_id(url):
    pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, url)
    return match.group(1) if match else None

# Function to create embedded YouTube player
def embed_youtube_video(video_id):
    # Create a unique div ID for the player
    player_div_id = f"youtube-player-{video_id}"
    
    # HTML for embedding YouTube video with autoplay detection
    html = f"""
    <div id="{player_div_id}" style="width:100%;">
        <iframe
            id="player-{video_id}"
            width="100%"
            height="315"
            src="https://www.youtube.com/embed/{video_id}?enablejsapi=1"
            frameborder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowfullscreen
        ></iframe>
    </div>
    
    <script>
        // Load YouTube API
        var tag = document.createElement('script');
        tag.src = "https://www.youtube.com/iframe_api";
        var firstScriptTag = document.getElementsByTagName('script')[0];
        firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
        
        // Create YouTube player and handle events
        var player;
        function onYouTubeIframeAPIReady() {{
            player = new YT.Player('player-{video_id}', {{
                events: {{
                    'onStateChange': onPlayerStateChange
                }}
            }});
        }}
        
        // Handle state changes (0 = ended)
        function onPlayerStateChange(event) {{
            if (event.data == 0) {{
                // Video ended - notify Streamlit
                setTimeout(function() {{
                    // Use Streamlit's session state to trigger next song
                    window.parent.postMessage({{
                        type: "streamlit:setComponentValue",
                        value: "video_ended"
                    }}, "*");
                }}, 1000);
            }}
        }}
    </script>
    """
    
    # Display the HTML
    st.components.v1.html(html, height=350)

# Function to load and save playlists
def load_playlists():
    if os.path.exists("playlists.json"):
        with open("playlists.json", "r") as f:
            return json.load(f)
    return {}

def save_playlists(playlists):
    with open("playlists.json", "w") as f:
        json.dump(playlists, f)

# Featured playlists
def get_featured_playlists():
    return {
        "Best of Beethoven Piano Concertos": [
            {"url": "https://www.youtube.com/watch?v=xVphVzGIcpY", "title": "Beethoven - New Piano Concerto 30"},
            {"url": "https://www.youtube.com/watch?v=pJTY7keAUdA", "title": "Beethoven - New Piano Concerto 32"},
            {"url": "https://www.youtube.com/watch?v=zj_-_Oh113Q", "title": "Beethoven - New Piano Concerto 37"},
            {"url": "https://www.youtube.com/watch?v=sM8X93lJUOg", "title": "Beethoven - New Piano Concerto 40"},
            {"url": "https://www.youtube.com/watch?v=36jdYoQkjek", "title": "Beethoven - New Piano Concerto 41"},
            {"url": "https://www.youtube.com/watch?v=x1j0ylFzIMU", "title": "Beethoven - New Piano Concerto 42"},
            {"url": "https://www.youtube.com/watch?v=-n4TGb1HrBc", "title": "Beethoven - New Piano Concerto 43"},
            {"url": "https://www.youtube.com/watch?v=TRUr9uotKA0", "title": "Beethoven - New Piano Concerto 25"},
            {"url": "https://www.youtube.com/watch?v=-UCvjD2bCks", "title": "Beethoven - New Piano Concerto 23"}
        ],
        "Best of Beethoven Violin Concertos": [
            {"url": "https://www.youtube.com/watch?v=p5iCHb3Axbc", "title": "Beethoven - New Violin Concerto 17"},
            {"url": "https://www.youtube.com/watch?v=4VNfql1DfqM", "title": "Beethoven - New Violin Concerto 20"},
            {"url": "https://www.youtube.com/watch?v=5BWNvmBcENE", "title": "Beethoven - New Violin Concerto 21"},
            {"url": "https://www.youtube.com/watch?v=v9YiqJ3Qyz0", "title": "Beethoven - New Violin Concerto 22"},
            {"url": "https://www.youtube.com/watch?v=XF0aobxJ2nw", "title": "Beethoven - New Violin Concerto 23"},
            {"url": "https://www.youtube.com/watch?v=OD1Q6R8tNzY", "title": "Beethoven - New Violin Concerto 26"},
            {"url": "https://www.youtube.com/watch?v=l0nHnYIbCRc", "title": "Beethoven - New Violin Concerto 30"}
        ],
        "Best of Mozart Piano Concertos": [
            {"url": "https://www.youtube.com/watch?v=QQe00ki35Nc", "title": "Mozart - New Piano Concerto 13"},
            {"url": "https://www.youtube.com/watch?v=xf31QPpscBk", "title": "Mozart - New Piano Concerto 14"},
            {"url": "https://www.youtube.com/watch?v=ixPpNBes5Nk", "title": "Mozart - New Piano Concerto 15"},
            {"url": "https://www.youtube.com/watch?v=7K4cNureKEE", "title": "Mozart - New Piano Concerto 25"},
            {"url": "https://www.youtube.com/watch?v=1Iycz4mXlCM", "title": "Mozart - New Piano Concerto 26"},
            {"url": "https://www.youtube.com/watch?v=FKFlOXxb4xE", "title": "Mozart - New Piano Concerto 27"},
            {"url": "https://www.youtube.com/watch?v=sfL8ezD8gBg", "title": "Mozart - New Piano Concerto 28"}
        ],
        "Best of Mozart Violin Concertos": [
            {"url": "https://www.youtube.com/watch?v=kYRBWBuTsxY", "title": "Mozart - New Violin Concerto 03"},
            {"url": "https://www.youtube.com/watch?v=LU6m62Pxc7w", "title": "Mozart - New Violin Concerto 06"},
            {"url": "https://www.youtube.com/watch?v=W-r_bQxdvd4", "title": "Mozart - New Violin Concerto 07"},
            {"url": "https://www.youtube.com/watch?v=D3UeW2j6Klw", "title": "Mozart - New Violin Concerto 08"}
        ]
    }

# Function to get YouTube channel ID from settings
def get_channel_id():
    return "UCMCX1aTQvca5zYHGRYnmgXw"  # Correct channel ID for ClassicsAI

# Function to search ClassicsAI YouTube channel
def search_channel(youtube, query, max_results=10):
    if not youtube:
        return []
    
    try:
        # Get channel ID from settings
        channel_id = get_channel_id()
        
        search_response = youtube.search().list(
            q=query,
            channelId=channel_id,
            part="snippet",
            maxResults=max_results,
            type="video"
        ).execute()
        
        return search_response.get("items", [])
    except HttpError as e:
        st.error(f"An error occurred: {e}")
        return []

# Function to get channel videos
def get_channel_videos(youtube, max_results=10, page_token=None):
    if not youtube:
        return [], None

    channel_id = get_channel_id()

    try:
        # Fetch videos from the channel using the channel ID
        search_response = youtube.search().list(
            part="snippet",
            channelId=channel_id,
            maxResults=max_results,
            type="video",
            order="date",
            pageToken=page_token
        ).execute()

        items = search_response.get("items", [])
        next_page_token = search_response.get("nextPageToken")

        # Transform search results
        transformed_items = []
        for item in items:
            transformed_item = {
                "snippet": {
                    "resourceId": {"videoId": item["id"]["videoId"]},
                    "title": item["snippet"]["title"],
                    "thumbnails": item["snippet"]["thumbnails"],
                    "publishedAt": item["snippet"]["publishedAt"]
                }
            }
            transformed_items.append(transformed_item)

        return transformed_items, next_page_token

    except HttpError as e:
        st.error(f"An error occurred: {e}")
        return [], None

# Add a function to handle autoplay in the main app
def handle_autoplay():
    # Check if video has ended (set by JavaScript)
    if "video_ended_trigger" in st.session_state and st.session_state.video_ended_trigger:
        # Reset the trigger
        st.session_state.video_ended_trigger = False
        
        # Get the current playlist
        if "current_playlist" in st.session_state and "current_playlist_index" in st.session_state:
            playlist = st.session_state.current_playlist
            current_index = st.session_state.current_playlist_index
            
            # If there are more songs in the playlist, play the next one
            if current_index < len(playlist) - 1:
                st.session_state.current_playlist_index += 1
                next_video = playlist[st.session_state.current_playlist_index]
                st.session_state.current_video_id = extract_video_id(next_video["url"])
                st.session_state.current_video_title = next_video["title"]
                return True
    
    return False

# Main application
def main():
    # Initialize session state for playlists if not exists
    if "user_playlists" not in st.session_state:
        st.session_state.user_playlists = load_playlists()
    
    if "current_video_id" not in st.session_state:
        st.session_state.current_video_id = None
    
    if "current_video_title" not in st.session_state:
        st.session_state.current_video_title = None
    
    if "current_playlist" not in st.session_state:
        st.session_state.current_playlist = None
    
    if "current_playlist_index" not in st.session_state:
        st.session_state.current_playlist_index = -1
    
    # Initialize the video ended trigger
    if "video_ended_trigger" not in st.session_state:
        st.session_state.video_ended_trigger = False
    
    # Component to receive messages from JavaScript
    video_ended = st.empty()
    
    # Check if a message was received from JavaScript
    if video_ended.text_input("", value="", key="video_ended_message", label_visibility="collapsed") == "video_ended":
        st.session_state.video_ended_trigger = True
        # Clear the input
        st.session_state.video_ended_message = ""
    
    # Handle autoplay if needed
    if handle_autoplay():
        st.rerun()
    
    # Get authenticator
    authenticator = get_authenticator()
    if not authenticator:
        return
    
    # Authentication
    name, authentication_status, username = authenticator.login("Login", "main")
    
    if authentication_status == False:
        st.error("Username/password is incorrect")
        
        # Registration section
        st.subheader("Don't have an account?")
        
        # Toggle between login and registration
        if "show_register" not in st.session_state:
            st.session_state.show_register = False
            
        if st.button("Register a new account" if not st.session_state.show_register else "Back to login"):
            st.session_state.show_register = not st.session_state.show_register
            st.rerun()
            
        if st.session_state.show_register:
            with st.form("registration_form"):
                st.subheader("Create a New Account")
                
                reg_username = st.text_input("Username", key="reg_username")
                reg_email = st.text_input("Email", key="reg_email")
                reg_password = st.text_input("Password", type="password", key="reg_password")
                reg_password2 = st.text_input("Confirm Password", type="password", key="reg_password2")
                
                submit = st.form_submit_button("Register")
                
                if submit:
                    if not reg_username or not reg_email or not reg_password:
                        st.error("All fields are required")
                    elif not re.match(r"[^@]+@[^@]+\.[^@]+", reg_email):
                        st.error("Please enter a valid email address")
                    elif len(reg_password) < 6:
                        st.error("Password must be at least 6 characters long")
                    elif reg_password != reg_password2:
                        st.error("Passwords do not match")
                    else:
                        success, message = register_user(reg_username, reg_email, reg_password)
                        if success:
                            st.success(message)
                            st.info("You can now log in with your new account")
                            st.session_state.show_register = False
                            st.rerun()
                        else:
                            st.error(message)
        
    elif authentication_status == None:
        st.warning("Please enter your username and password")
        
        # Registration section
        st.subheader("Don't have an account?")
        
        # Toggle between login and registration
        if "show_register" not in st.session_state:
            st.session_state.show_register = False
            
        if st.button("Register a new account" if not st.session_state.show_register else "Back to login"):
            st.session_state.show_register = not st.session_state.show_register
            st.rerun()
            
        if st.session_state.show_register:
            with st.form("registration_form"):
                st.subheader("Create a New Account")
                
                reg_username = st.text_input("Username", key="reg_username")
                reg_email = st.text_input("Email", key="reg_email")
                reg_password = st.text_input("Password", type="password", key="reg_password")
                reg_password2 = st.text_input("Confirm Password", type="password", key="reg_password2")
                
                submit = st.form_submit_button("Register")
                
                if submit:
                    if not reg_username or not reg_email or not reg_password:
                        st.error("All fields are required")
                    elif not re.match(r"[^@]+@[^@]+\.[^@]+", reg_email):
                        st.error("Please enter a valid email address")
                    elif len(reg_password) < 6:
                        st.error("Password must be at least 6 characters long")
                    elif reg_password != reg_password2:
                        st.error("Passwords do not match")
                    else:
                        success, message = register_user(reg_username, reg_email, reg_password)
                        if success:
                            st.success(message)
                            st.info("You can now log in with your new account")
                            st.session_state.show_register = False
                            st.rerun()
                        else:
                            st.error(message)
        
    elif authentication_status:
        # Sidebar
        with st.sidebar:
            st.subheader(f"Welcome, {name}")
            authenticator.logout("Logout", "sidebar")
            
            st.subheader("Now Playing")
            if st.session_state.current_video_id and st.session_state.current_video_title:
                st.write(f"**{st.session_state.current_video_title}**")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("⏮ Previous"):
                        if st.session_state.current_playlist and st.session_state.current_playlist_index > 0:
                            st.session_state.current_playlist_index -= 1
                            next_video = st.session_state.current_playlist[st.session_state.current_playlist_index]
                            st.session_state.current_video_id = extract_video_id(next_video["url"])
                            st.session_state.current_video_title = next_video["title"]
                            st.rerun()
                
                with col2:
                    if st.button("⏹ Stop"):
                        st.session_state.current_video_id = None
                        st.session_state.current_video_title = None
                        st.rerun()
                
                with col3:
                    if st.button("⏭ Next"):
                        if (st.session_state.current_playlist and 
                            st.session_state.current_playlist_index < len(st.session_state.current_playlist) - 1):
                            st.session_state.current_playlist_index += 1
                            next_video = st.session_state.current_playlist[st.session_state.current_playlist_index]
                            st.session_state.current_video_id = extract_video_id(next_video["url"])
                            st.session_state.current_video_title = next_video["title"]
                            st.rerun()
            else:
                st.write("No track playing")
        
        # Main content
        create_decorative_header()
        
        # Video player
        if st.session_state.current_video_id:
            embed_youtube_video(st.session_state.current_video_id)
        
        # Tabs for different sections
        tab1, tab2, tab3, tab4 = st.tabs(["Featured Playlists", "My Playlists", "Channel Browser", "Search"])
        
        # Tab 1: Featured Playlists
        with tab1:
            st.header("Featured Playlists")
            
            featured_playlists = get_featured_playlists()
            
            for playlist_name, tracks in featured_playlists.items():
                with st.expander(playlist_name, expanded=False):
                    if st.button(f"Play All: {playlist_name}", key=f"play_all_{playlist_name}"):
                        st.session_state.current_playlist = tracks
                        st.session_state.current_playlist_index = 0
                        first_track = tracks[0]
                        st.session_state.current_video_id = extract_video_id(first_track["url"])
                        st.session_state.current_video_title = first_track["title"]
                        st.rerun()
                    
                    for i, track in enumerate(tracks):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"{i+1}. {track['title']}")
                        with col2:
                            if st.button("Play", key=f"play_{playlist_name}_{i}"):
                                video_id = extract_video_id(track["url"])
                                st.session_state.current_video_id = video_id
                                st.session_state.current_video_title = track["title"]
                                st.session_state.current_playlist = tracks
                                st.session_state.current_playlist_index = i
                                st.rerun()
        
        # Tab 2: My Playlists
        with tab2:
            st.header("My Playlists")
            
            # Create new playlist
            with st.expander("Create New Playlist", expanded=False):
                playlist_name = st.text_input("Playlist Name", key="new_playlist_name")
                if st.button("Create Playlist"):
                    if playlist_name and playlist_name not in st.session_state.user_playlists:
                        st.session_state.user_playlists[playlist_name] = []
                        save_playlists(st.session_state.user_playlists)
                        st.success(f"Playlist '{playlist_name}' created!")
                        st.rerun()
                    elif not playlist_name:
                        st.error("Please enter a playlist name")
                    else:
                        st.error(f"Playlist '{playlist_name}' already exists")
            
            # Add song to playlist
            with st.expander("Add Song to Playlist", expanded=False):
                if st.session_state.user_playlists:
                    playlist_names = list(st.session_state.user_playlists.keys())
                    selected_playlist = st.selectbox("Select Playlist", playlist_names, key="add_song_playlist")
                    
                    song_url = st.text_input("YouTube URL", key="add_song_url")
                    song_title = st.text_input("Song Title", key="add_song_title")
                    
                    if st.button("Add Song"):
                        if song_url and song_title:
                            video_id = extract_video_id(song_url)
                            if video_id:
                                st.session_state.user_playlists[selected_playlist].append({
                                    "url": song_url,
                                    "title": song_title
                                })
                                save_playlists(st.session_state.user_playlists)
                                st.success(f"Song added to '{selected_playlist}'!")
                                st.rerun()
                            else:
                                st.error("Invalid YouTube URL")
                        else:
                            st.error("Please enter both URL and title")
                else:
                    st.info("Create a playlist first")
            
            # Display user playlists
            if st.session_state.user_playlists:
                for playlist_name, tracks in st.session_state.user_playlists.items():
                    with st.expander(playlist_name, expanded=False):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.subheader(playlist_name)
                        with col2:
                            if st.button("Delete Playlist", key=f"delete_{playlist_name}"):
                                del st.session_state.user_playlists[playlist_name]
                                save_playlists(st.session_state.user_playlists)
                                st.success(f"Playlist '{playlist_name}' deleted!")
                                st.rerun()
                        
                        if tracks:
                            if st.button(f"Play All: {playlist_name}", key=f"play_all_user_{playlist_name}"):
                                st.session_state.current_playlist = tracks
                                st.session_state.current_playlist_index = 0
                                first_track = tracks[0]
                                video_id = extract_video_id(first_track["url"])
                                st.session_state.current_video_id = video_id
                                st.session_state.current_video_title = first_track["title"]
                                st.rerun()
                            
                            for i, track in enumerate(tracks):
                                col1, col2, col3 = st.columns([3, 1, 1])
                                with col1:
                                    st.write(f"{i+1}. {track['title']}")
                                with col2:
                                    if st.button("Play", key=f"play_user_{playlist_name}_{i}"):
                                        video_id = extract_video_id(track["url"])
                                        st.session_state.current_video_id = video_id
                                        st.session_state.current_video_title = track["title"]
                                        st.session_state.current_playlist = tracks
                                        st.session_state.current_playlist_index = i
                                        st.rerun()
                                with col3:
                                    if st.button("Remove", key=f"remove_{playlist_name}_{i}"):
                                        st.session_state.user_playlists[playlist_name].pop(i)
                                        save_playlists(st.session_state.user_playlists)
                                        st.rerun()
                        else:
                            st.info("This playlist is empty")
            else:
                st.info("You don't have any playlists yet")
        
        # Tab 3: Channel Browser
        with tab3:
            st.header("ClassicsAI Channel Browser")
            
            youtube = get_youtube_api()
            if youtube:
                # Initialize pagination
                if "channel_page_token" not in st.session_state:
                    st.session_state.channel_page_token = None

                # Get channel videos
                channel_videos, next_page_token = get_channel_videos(youtube, page_token=st.session_state.channel_page_token)

                if channel_videos:
                    for i, item in enumerate(channel_videos):
                        video = item["snippet"]
                        video_id = video["resourceId"]["videoId"]
                        title = video["title"]
                        thumbnail = video["thumbnails"]["medium"]["url"]
                        published_at = video["publishedAt"][:10]  # Just the date
                        
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            st.image(thumbnail, use_container_width=True)
                        with col2:
                            st.markdown(f"**{title}**")
                            st.write(f"Published: {published_at}")
                            
                            btn_col1, btn_col2, btn_col3 = st.columns(3)
                            with btn_col1:
                                if st.button("Play", key=f"play_channel_{i}"):
                                    st.session_state.current_video_id = video_id
                                    st.session_state.current_video_title = title
                                    st.rerun()
                            
                            with btn_col2:
                                # Add to playlist button
                                if st.session_state.user_playlists:
                                    if st.button("Add to Playlist", key=f"add_channel_{i}"):
                                        st.session_state.temp_video = {
                                            "url": f"https://www.youtube.com/watch?v={video_id}",
                                            "title": title
                                        }
                                        st.session_state.show_add_dialog = True
                                        st.rerun()
                        
                        st.markdown("---")
                    
                    # Pagination controls
                    if next_page_token:
                        if st.button("Load More", key="load_more_channel"):
                            st.session_state.channel_page_token = next_page_token
                            st.rerun()

                    # Dialog for adding to playlist
                    if "show_add_dialog" in st.session_state and st.session_state.show_add_dialog:
                        with st.form("add_to_playlist_form"):
                            st.subheader("Add to Playlist")
                            playlist_names = list(st.session_state.user_playlists.keys())
                            selected_playlist = st.selectbox("Select Playlist", playlist_names)
                            
                            submitted = st.form_submit_button("Add")
                            cancel = st.form_submit_button("Cancel")
                            
                            if submitted:
                                st.session_state.user_playlists[selected_playlist].append(st.session_state.temp_video)
                                save_playlists(st.session_state.user_playlists)
                                st.success(f"Added to '{selected_playlist}'!")
                                st.session_state.show_add_dialog = False
                                st.rerun()
                            
                            if cancel:
                                st.session_state.show_add_dialog = False
                                st.rerun()
                else:
                    st.info("No videos found in the channel")
            else:
                st.error("YouTube API not initialized. Please check your API key.")
        
        # Tab 4: Search
        with tab4:
            st.header("Search ClassicsAI Channel")
            
            youtube = get_youtube_api()
            if youtube:
                search_query = st.text_input("Search for videos", key="search_query")
                
                if st.button("Search") and search_query:
                    search_results = search_channel(youtube, search_query)
                    
                    if search_results:
                        st.subheader("Search Results")
                        
                        for i, item in enumerate(search_results):
                            video = item["snippet"]
                            video_id = item["id"]["videoId"]
                            title = video["title"]
                            description = video["description"]
                            thumbnail = video["thumbnails"]["medium"]["url"]
                            
                            col1, col2 = st.columns([1, 3])
                            with col1:
                                st.image(thumbnail, use_container_width=True)
                            with col2:
                                st.markdown(f"**{title}**")
                                st.write(description[:100] + "..." if len(description) > 100 else description)
                                
                                btn_col1, btn_col2 = st.columns(2)
                                with btn_col1:
                                    if st.button("Play", key=f"play_search_{i}"):
                                        st.session_state.current_video_id = video_id
                                        st.session_state.current_video_title = title
                                        st.rerun()
                                
                                with btn_col2:
                                    # Add to playlist button
                                    if st.session_state.user_playlists:
                                        if st.button("Add to Playlist", key=f"add_search_{i}"):
                                            st.session_state.temp_video = {
                                                "url": f"https://www.youtube.com/watch?v={video_id}",
                                                "title": title
                                            }
                                            st.session_state.show_add_dialog = True
                                            st.rerun()
                            
                            st.markdown("---")
                    else:
                        st.info("No results found")
            else:
                st.error("YouTube API not initialized. Please check your API key.")

if __name__ == "__main__":
    main() 
