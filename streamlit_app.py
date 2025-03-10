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

# Set page configuration - must be the first Streamlit command
st.set_page_config(
    page_title="ClassicsAI Music Player",
    page_icon="🎵",
    layout="wide"
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
    # Create a unique iframe ID to target with JavaScript
    iframe_id = f"youtube_player_{video_id}"
    
    # Calculate current video duration for auto-advance (add 5 seconds buffer)
    video_duration = get_video_duration(video_id)
    
    # Format for embed with autoplay functionality
    embed_html = f"""
    <div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 10px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);">
        <iframe 
            id="{iframe_id}" 
            src="https://www.youtube.com/embed/{video_id}?autoplay=1&enablejsapi=1" 
            style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none; border-radius: 10px;" 
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
            allowfullscreen>
        </iframe>
    </div>
    
    <script>
        // Set up video duration tracking for auto-advance
        setTimeout(function() {{
            // Create and click a hidden button after video duration
            var autoAdvanceButton = document.createElement('button');
            autoAdvanceButton.style.display = 'none';
            autoAdvanceButton.id = 'auto_advance_button';
            autoAdvanceButton.innerText = 'Next';
            document.body.appendChild(autoAdvanceButton);
            
            // Set timeout to click button after video finishes
            setTimeout(function() {{
                document.getElementById('auto_advance_button').click();
            }}, {video_duration * 1000});
        }}, 1000);
    </script>
    """
    
    return embed_html

def get_video_duration(video_id):
    """Get video duration in seconds, or return default if API fails."""
    try:
        youtube = get_youtube_api()
        if not youtube:
            return 300  # Default 5 minutes
            
        # Get video details including duration
        response = youtube.videos().list(
            part="contentDetails",
            id=video_id
        ).execute()
        
        if not response.get('items'):
            return 300  # Default if video not found
            
        # Parse duration from ISO 8601 format (PT#M#S)
        duration_str = response['items'][0]['contentDetails']['duration']
        
        # Extract minutes and seconds
        minutes = 0
        seconds = 0
        
        # Find minutes
        minutes_match = re.search(r'(\d+)M', duration_str)
        if minutes_match:
            minutes = int(minutes_match.group(1))
            
        # Find seconds
        seconds_match = re.search(r'(\d+)S', duration_str)
        if seconds_match:
            seconds = int(seconds_match.group(1))
            
        # Calculate total seconds and add a buffer
        total_seconds = (minutes * 60) + seconds + 2
        
        return total_seconds
    except Exception as e:
        # If any error occurs, return a default duration
        return 300  # Default 5 minutes

# Function to check for auto-play signal from JavaScript
def check_for_autoplay():
    # Inject JavaScript to check sessionStorage for auto-play signal
    check_js = """
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const autoPlayData = sessionStorage.getItem('autoPlayNextTrack');
            if (autoPlayData) {
                const data = JSON.parse(autoPlayData);
                if (data.isVideoEnded) {
                    // Clear the data to prevent repeated auto-plays
                    sessionStorage.removeItem('autoPlayNextTrack');
                    
                    // Use a hidden button click to trigger the next track
                    setTimeout(function() {
                        document.getElementById('autoplay_trigger_button').click();
                    }, 100);
                }
            }
        });
    </script>
    """
    st.markdown(check_js, unsafe_allow_html=True)
    
    # Hidden button to trigger the next track
    if st.button("AutoplayTrigger", key="autoplay_trigger_button", help="This button is automatically clicked to trigger autoplay", args=None):
        if st.session_state.current_playlist and st.session_state.current_track_index < len(st.session_state.current_playlist) - 1:
            st.session_state.current_track_index += 1
            next_track = st.session_state.current_playlist[st.session_state.current_track_index]
            video_id = extract_video_id(next_track["url"])
            st.session_state.current_video_id = video_id
            st.session_state.current_video_title = next_track["title"]
            st.rerun()

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
        
    if "current_track_index" not in st.session_state:
        st.session_state.current_track_index = 0
        
    if "show_add_dialog" not in st.session_state:
        st.session_state.show_add_dialog = False
        
    if "auto_advance" not in st.session_state:
        st.session_state.auto_advance = False
    
    # Apply classical theme styling
    apply_classical_theme()
    
    # Get authenticator
    authenticator = get_authenticator()
    if not authenticator:
        return
    
    # Authentication
    name, authentication_status, username = authenticator.login("Login", "main")
    
    # Authenticated section
    if authentication_status:
        # Welcome message
        st.success(f"Welcome, {name}!")
        
        # Logout button
        authenticator.logout("Logout", "main")
        
        # Create decorative header
        create_decorative_header()
        
        # Video player container
        player_container = st.empty()
        
        # Auto-advance hidden button for the timer mechanism
        if st.button("Auto Advance", key="auto_advance_button", help="This button is automatically clicked to advance to the next track", on_click=lambda: advance_to_next_track()):
            # This will be triggered by JavaScript setTimeout
            pass
        
        # If a video is currently playing, display it
        if st.session_state.current_video_id:
            with player_container.container():
                st.header(f"Now Playing: {st.session_state.current_video_title}")
                st.markdown(embed_youtube_video(st.session_state.current_video_id), unsafe_allow_html=True)
                
                # If there's a playlist, show next/previous buttons
                if st.session_state.current_playlist:
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("⏮️ Previous") and st.session_state.current_track_index > 0:
                            st.session_state.current_track_index -= 1
                            prev_track = st.session_state.current_playlist[st.session_state.current_track_index]
                            video_id = extract_video_id(prev_track["url"])
                            st.session_state.current_video_id = video_id
                            st.session_state.current_video_title = prev_track["title"]
                            st.rerun()
                    with col2:
                        if st.button("Next ⏭️") and st.session_state.current_track_index < len(st.session_state.current_playlist) - 1:
                            advance_to_next_track()
        
        # Tabs
        tab1, tab2, tab3, tab4 = st.tabs(["Featured Playlists", "My Playlists", "ClassicsAI Channel", "Search"])
        
        # Tab 1: Featured Playlists
        with tab1:
            st.header("Featured Playlists")
            
            featured_playlists = get_featured_playlists()
            
            for playlist_name, tracks in featured_playlists.items():
                with st.expander(playlist_name):
                    if tracks:
                        if st.button(f"Play All: {playlist_name}", key=f"play_all_{playlist_name}"):
                            st.session_state.current_playlist = tracks
                            st.session_state.current_track_index = 0
                            first_track = tracks[0]
                            video_id = extract_video_id(first_track["url"])
                            st.session_state.current_video_id = video_id
                            st.session_state.current_video_title = first_track["title"]
                            st.rerun()
                        
                        if st.button(f"Add to My Playlists: {playlist_name}", key=f"add_playlist_{playlist_name}"):
                            # Create a new playlist with a unique name
                            count = 1
                            new_name = f"{playlist_name}"
                            while new_name in st.session_state.user_playlists:
                                new_name = f"{playlist_name} ({count})"
                                count += 1
                            
                            st.session_state.user_playlists[new_name] = tracks.copy()
                            save_playlists(st.session_state.user_playlists)
                            st.success(f"Added '{new_name}' to your playlists!")
                            st.rerun()
                        
                        for i, track in enumerate(tracks):
                            col1, col2, col3 = st.columns([3, 1, 1])
                            with col1:
                                st.write(f"{i+1}. {track['title']}")
                            with col2:
                                if st.button("Play", key=f"play_{playlist_name}_{i}"):
                                    video_id = extract_video_id(track["url"])
                                    st.session_state.current_video_id = video_id
                                    st.session_state.current_video_title = track["title"]
                                    st.session_state.current_playlist = tracks
                                    st.session_state.current_track_index = i
                                    st.rerun()
                            with col3:
                                if st.button("Add to My Playlists", key=f"add_track_{playlist_name}_{i}"):
                                    if not st.session_state.user_playlists:
                                        # Create a new playlist if none exists
                                        st.session_state.user_playlists["My Favorites"] = [track]
                                        save_playlists(st.session_state.user_playlists)
                                        st.success(f"Added to new 'My Favorites' playlist!")
                                    else:
                                        # Show dialog to select a playlist
                                        st.session_state.temp_video = track
                                        st.session_state.show_add_dialog = True
                                    st.rerun()
                    else:
                        st.info("This playlist is empty")
            
            # Dialog for adding to playlist
            if "show_add_dialog" in st.session_state and st.session_state.show_add_dialog:
                with st.form("add_to_playlist_form"):
                    st.subheader("Add to Playlist")
                    
                    # Option to create a new playlist
                    create_new = st.checkbox("Create a new playlist")
                    
                    if create_new:
                        new_playlist_name = st.text_input("New Playlist Name")
                    else:
                        playlist_names = list(st.session_state.user_playlists.keys())
                        selected_playlist = st.selectbox("Select Playlist", playlist_names)
                    
                    submitted = st.form_submit_button("Add")
                    cancel = st.form_submit_button("Cancel")
                    
                    if submitted:
                        if create_new and new_playlist_name:
                            st.session_state.user_playlists[new_playlist_name] = [st.session_state.temp_video]
                            st.success(f"Created new playlist '{new_playlist_name}' and added track!")
                        elif not create_new:
                            st.session_state.user_playlists[selected_playlist].append(st.session_state.temp_video)
                            st.success(f"Added to '{selected_playlist}'!")
                        
                        save_playlists(st.session_state.user_playlists)
                        st.session_state.show_add_dialog = False
                        st.rerun()
                    
                    if cancel:
                        st.session_state.show_add_dialog = False
                        st.rerun()
        
        # Tab 2: My Playlists
        with tab2:
            st.header("My Playlists")
            
            # Create a new playlist form
            with st.expander("Create a New Playlist"):
                with st.form("create_playlist_form"):
                    new_playlist_name = st.text_input("Playlist Name")
                    submit_new = st.form_submit_button("Create")
                    
                    if submit_new and new_playlist_name:
                        if new_playlist_name in st.session_state.user_playlists:
                            st.error("A playlist with this name already exists!")
                        else:
                            st.session_state.user_playlists[new_playlist_name] = []
                            save_playlists(st.session_state.user_playlists)
                            st.success(f"Created playlist '{new_playlist_name}'!")
                            st.rerun()
            
            # Display user playlists
            if st.session_state.user_playlists:
                for playlist_name, tracks in st.session_state.user_playlists.items():
                    with st.expander(playlist_name):
                        # Delete playlist button
                        if st.button("Delete Playlist", key=f"delete_{playlist_name}"):
                            del st.session_state.user_playlists[playlist_name]
                            save_playlists(st.session_state.user_playlists)
                            st.success(f"Deleted '{playlist_name}'!")
                            st.rerun()
                        
                        if tracks:
                            if st.button(f"Play All: {playlist_name}", key=f"play_all_user_{playlist_name}"):
                                st.session_state.current_playlist = tracks
                                st.session_state.current_track_index = 0
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
                                        st.session_state.current_track_index = i
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
                                # Add to playlist button - always show and create a playlist if none exists
                                if st.button("Add to Playlist", key=f"add_channel_{i}"):
                                    if not st.session_state.user_playlists:
                                        # Create default playlist if user has none
                                        st.session_state.user_playlists["My Favorites"] = [{
                                            "url": f"https://www.youtube.com/watch?v={video_id}",
                                            "title": title
                                        }]
                                        save_playlists(st.session_state.user_playlists)
                                        st.success(f"Added to new 'My Favorites' playlist!")
                                        st.rerun()
                                    else:
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
                            
                            # Option to create a new playlist
                            create_new = st.checkbox("Create a new playlist")
                            
                            if create_new:
                                new_playlist_name = st.text_input("New Playlist Name")
                            else:
                                playlist_names = list(st.session_state.user_playlists.keys())
                                selected_playlist = st.selectbox("Select Playlist", playlist_names)
                            
                            submitted = st.form_submit_button("Add")
                            cancel = st.form_submit_button("Cancel")
                            
                            if submitted:
                                if create_new and new_playlist_name:
                                    st.session_state.user_playlists[new_playlist_name] = [st.session_state.temp_video]
                                    st.success(f"Created new playlist '{new_playlist_name}' and added track!")
                                elif not create_new:
                                    st.session_state.user_playlists[selected_playlist].append(st.session_state.temp_video)
                                    st.success(f"Added to '{selected_playlist}'!")
                                
                                save_playlists(st.session_state.user_playlists)
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
                                    # Add to playlist button - always show and create a playlist if none exists
                                    if st.button("Add to Playlist", key=f"add_search_{i}"):
                                        if not st.session_state.user_playlists:
                                            # Create default playlist if user has none
                                            st.session_state.user_playlists["My Favorites"] = [{
                                                "url": f"https://www.youtube.com/watch?v={video_id}",
                                                "title": title
                                            }]
                                            save_playlists(st.session_state.user_playlists)
                                            st.success(f"Added to new 'My Favorites' playlist!")
                                            st.rerun()
                                        else:
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

def advance_to_next_track():
    """Helper function to advance to the next track in the playlist"""
    if (st.session_state.current_playlist and 
            st.session_state.current_track_index < len(st.session_state.current_playlist) - 1):
        st.session_state.current_track_index += 1
        next_track = st.session_state.current_playlist[st.session_state.current_track_index]
        video_id = extract_video_id(next_track["url"])
        st.session_state.current_video_id = video_id
        st.session_state.current_video_title = next_track["title"]
        st.rerun()

if __name__ == "__main__":
    main() 
