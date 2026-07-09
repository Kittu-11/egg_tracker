"""
Small helper to open an ngrok tunnel to port 5000 and print the public URL.
Run this after installing pyngrok (`pip install pyngrok`).
"""
import time

try:
    from pyngrok import ngrok
except Exception:
    print("pyngrok not installed. Install with: pip install pyngrok")
    raise

if __name__ == "__main__":
    print("Opening ngrok tunnel to http://127.0.0.1:5000 ...")
    tunnel = ngrok.connect(5000, "http")
    print("Public URL:", tunnel.public_url)
    print("Press Ctrl+C to exit and close the tunnel.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down tunnel...")
        ngrok.disconnect(tunnel.public_url)
