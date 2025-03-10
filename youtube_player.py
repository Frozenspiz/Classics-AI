import streamlit as st
import streamlit.components.v1 as components
import os
import json

# Define the custom component for YouTube player
def youtube_player(video_id, key=None):
    # Create a unique key for this instance if not provided
    if key is None:
        key = f"youtube_player_{video_id}"
    
    # Path to the HTML file
    component_path = os.path.join(os.path.dirname(__file__), "youtube_player.html")
    
    # If the HTML file doesn't exist, create it
    if not os.path.exists(component_path):
        with open(component_path, "w") as f:
            f.write("""
<!DOCTYPE html>
<html>
<head>
    <style>
        .player-container {
            position: relative;
            padding-bottom: 56.25%;
            height: 0;
            overflow: hidden;
            max-width: 100%;
            background-color: #EAE6D9;
            border: 2px solid #D4AF37;
            border-radius: 8px;
        }
        .player-container iframe {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
        }
    </style>
</head>
<body>
    <div class="player-container">
        <div id="player"></div>
    </div>

    <script>
        // Load the YouTube IFrame API
        var tag = document.createElement('script');
        tag.src = "https://www.youtube.com/iframe_api";
        var firstScriptTag = document.getElementsByTagName('script')[0];
        firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

        // Create YouTube player when API is ready
        var player;
        function onYouTubeIframeAPIReady() {
            player = new YT.Player('player', {
                height: '100%',
                width: '100%',
                videoId: getVideoId(),
                playerVars: {
                    'playsinline': 1,
                    'autoplay': 1,
                    'modestbranding': 1
                },
                events: {
                    'onStateChange': onPlayerStateChange
                }
            });
        }

        // Get video ID from URL parameters
        function getVideoId() {
            const urlParams = new URLSearchParams(window.location.search);
            return urlParams.get('videoId');
        }

        // Handle player state changes
        function onPlayerStateChange(event) {
            // State 0 means the video has ended
            if (event.data === 0) {
                // Send message to parent (Streamlit)
                window.parent.postMessage({
                    type: 'streamlit:videoEnded',
                    videoId: getVideoId()
                }, '*');
            }
        }
    </script>
</body>
</html>
            """)
    
    # Use the component
    return components.iframe(
        src=f"youtube_player.html?videoId={video_id}",
        height=400,
        scrolling=False,
        key=key
    )

# Function to check if a video has ended
def check_video_ended():
    # Get query parameters
    query_params = st.experimental_get_query_params()
    
    # Check if video_ended parameter exists
    if 'video_ended' in query_params:
        video_id = query_params.get('video_ended', [''])[0]
        
        # Clear the parameter
        params = st.experimental_get_query_params()
        if 'video_ended' in params:
            del params['video_ended']
            st.experimental_set_query_params(**params)
        
        return True, video_id
    
    return False, None 
