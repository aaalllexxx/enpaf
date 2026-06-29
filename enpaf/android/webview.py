"""
ENPAF Android — WebView Configuration
Settings for the Android WebView component.
"""

# WebView settings applied in MainActivity.java
WEBVIEW_SETTINGS = {
    "javascript_enabled": True,
    "dom_storage_enabled": True,
    "allow_file_access": True,
    "allow_content_access": True,
    "database_enabled": True,
    "media_playback_requires_user_gesture": False,
    "built_in_zoom_controls": False,
    "display_zoom_controls": False,
    "load_with_overview_mode": True,
    "use_wide_view_port": True,
    "cache_mode": "LOAD_DEFAULT",
    "mixed_content_mode": "MIXED_CONTENT_ALWAYS_ALLOW",
}


def get_webview_init_code() -> str:
    """Generate Java code for WebView initialization."""
    return """
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setDatabaseEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setBuiltInZoomControls(false);
        settings.setDisplayZoomControls(false);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        
        webView.setWebViewClient(new WebViewClient());
        webView.setWebChromeClient(new WebChromeClient());
    """
