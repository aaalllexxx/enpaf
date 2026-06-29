"""
ENPAF Android — Deep Links
Build AndroidManifest <intent-filter> blocks for custom URL schemes and App Links.
"""

from xml.sax.saxutils import quoteattr

# UI/value -> AndroidManifest <data> attribute name
_PATH_ATTR = {
    "path": "android:path",
    "exact": "android:path",
    "prefix": "android:pathPrefix",
    "pathPrefix": "android:pathPrefix",
    "pattern": "android:pathPattern",
    "pathPattern": "android:pathPattern",
}


def normalize_deeplink(dl: dict) -> dict:
    """Return a cleaned deep-link dict with stripped string fields."""
    return {
        "label": str(dl.get("label", "")).strip(),
        "scheme": str(dl.get("scheme", "")).strip(),
        "host": str(dl.get("host", "")).strip(),
        "path": str(dl.get("path", "")).strip(),
        "pathType": (str(dl.get("pathType", "path")).strip() or "path"),
        "autoVerify": bool(dl.get("autoVerify", False)),
    }


def get_deeplink_xml(deeplinks: list, indent: str = "            ") -> str:
    """Generate one <intent-filter> per deep link for the launcher activity.

    Args:
        deeplinks: list of deep-link dicts (scheme is required; host/path optional)
        indent: leading whitespace for each top-level element

    Returns:
        Empty string when there is nothing to add, otherwise a leading newline
        followed by the indented intent-filter blocks (ready to splice into the
        <activity> element).
    """
    blocks = []
    for raw in deeplinks or []:
        dl = normalize_deeplink(raw)
        if not dl["scheme"]:
            continue  # a <data> element requires at least a scheme

        attrs = [f'android:scheme={quoteattr(dl["scheme"])}']
        if dl["host"]:
            attrs.append(f'android:host={quoteattr(dl["host"])}')
        if dl["path"]:
            attr_name = _PATH_ATTR.get(dl["pathType"], "android:path")
            value = dl["path"]
            if attr_name in ("android:path", "android:pathPrefix") and not value.startswith("/"):
                value = "/" + value
            attrs.append(f'{attr_name}={quoteattr(value)}')

        verify = ' android:autoVerify="true"' if dl["autoVerify"] else ""
        blocks.append(
            f'{indent}<intent-filter{verify}>\n'
            f'{indent}    <action android:name="android.intent.action.VIEW" />\n'
            f'{indent}    <category android:name="android.intent.category.DEFAULT" />\n'
            f'{indent}    <category android:name="android.intent.category.BROWSABLE" />\n'
            f'{indent}    <data {" ".join(attrs)} />\n'
            f'{indent}</intent-filter>'
        )

    return ("\n" + "\n".join(blocks)) if blocks else ""
