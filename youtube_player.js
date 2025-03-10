// Listen for messages from the YouTube iframe
window.addEventListener('message', function(event) {
    // Check if the message is from our YouTube player
    if (event.data.type === 'streamlit:videoEnded') {
        // Add the video_ended parameter to the URL
        const url = new URL(window.location.href);
        url.searchParams.set('video_ended', event.data.videoId);
        window.history.pushState({}, '', url);
        
        // Force Streamlit to rerun
        window.parent.postMessage({type: "streamlit:componentRerun"}, "*");
    }
}); 
