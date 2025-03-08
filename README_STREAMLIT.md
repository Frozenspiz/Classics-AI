# ClassicsAI Music Player - Streamlit Edition

A web-based music player for AI-generated classical music from YouTube, built with Streamlit. This application allows users to browse, search, and create playlists from the ClassicsAI YouTube channel.

## Features

- **User Authentication**: Secure login system for users
- **YouTube Video Embedding**: Watch videos directly within the app
- **Playlist Management**: Create, edit, and save custom playlists
- **Channel Integration**: Browse and search videos from the ClassicsAI YouTube channel
- **Featured Playlists**: Curated collections of the best AI-generated classical music
- **Classical Theme**: Elegant design inspired by classical-era aesthetics

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- A Google API key with YouTube Data API v3 enabled

### Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/classicsai-music-player.git
   cd classicsai-music-player
   ```

2. Install the required dependencies:
   ```
   pip install -r streamlit_requirements.txt
   ```

3. Set up your YouTube API key:
   - Create a project in the [Google Cloud Console](https://console.cloud.google.com/)
   - Enable the YouTube Data API v3
   - Create an API key
   - Set the API key as an environment variable:
     ```
     # On Windows
     set YOUTUBE_API_KEY=your_api_key_here
     
     # On macOS/Linux
     export YOUTUBE_API_KEY=your_api_key_here
     ```
   - Alternatively, replace `YOUR_API_KEY` in the `streamlit_app.py` file with your actual API key

4. Update the YouTube channel ID:
   - Replace `UCyQGLLqZwKLIkFNBAVnM9Gg` in the `streamlit_app.py` file with your actual YouTube channel ID

### User Management

1. The default admin account is:
   - Username: `admin`
   - Password: `admin123`

2. To create new user accounts:
   - Run the password generator tool:
     ```
     streamlit run generate_password.py
     ```
   - Follow the instructions to create a new user and add them to the config file

### Running the Application

1. Start the Streamlit app:
   ```
   streamlit run streamlit_app.py
   ```

2. Open your browser and navigate to the URL shown in the terminal (typically http://localhost:8501)

## Deploying to Streamlit Cloud

1. Create a Streamlit Cloud account at [streamlit.io](https://streamlit.io/)

2. Connect your GitHub repository to Streamlit Cloud

3. Set up the required secrets in the Streamlit Cloud dashboard:
   - Add `YOUTUBE_API_KEY` with your API key value

4. Deploy the app and share the URL with your friends and subscribers

## Usage

1. **Login**: Enter your username and password to access the app

2. **Browse Featured Playlists**: Explore curated collections of AI-generated classical music

3. **Create Custom Playlists**: 
   - Click "Create New Playlist" in the My Playlists tab
   - Add songs from search results or the channel browser

4. **Search for Videos**:
   - Use the Search tab to find specific videos
   - Play videos directly or add them to your playlists

5. **Browse Channel**:
   - Explore all videos from the ClassicsAI channel
   - Sort by upload date and view video details

## Customization

- **Theme Colors**: Modify the color variables in the `apply_classical_theme()` function
- **Featured Playlists**: Update the `get_featured_playlists()` function to change the curated playlists
- **Channel ID**: Replace the channel ID in the code with your own YouTube channel ID

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with [Streamlit](https://streamlit.io/)
- Uses the [YouTube Data API v3](https://developers.google.com/youtube/v3)
- Authentication powered by [Streamlit-Authenticator](https://github.com/mkhorasani/Streamlit-Authenticator) 