from flask import Flask, request, jsonify
from flask_cors import CORS
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import os
from werkzeug.middleware.proxy_fix import ProxyFix

from categorize_slides import perform_categorization_with_ids, perform_categorization_with_type
from merge_presentations import create_presentation_from_database

SCOPES = ["https://www.googleapis.com/auth/presentations"]
REDIRECT_URI = "https://luke-ai-slides-deck-project-z089.onrender.com/oauth2callback"  # Update to your actual frontend or backend redirect URI

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "https://luke-ai-slides-deck-project-1.onrender.com"}}, supports_credentials=True)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  

UPLOAD_FOLDER = os.getcwd()
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Global flow object to initialize OAuth 2.0
flow = Flow.from_client_secrets_file(
    "credentials.json",
    scopes=SCOPES,
    redirect_uri=REDIRECT_URI
)

def save_credentials(creds):
    with open("token.json", "w") as token:
        token.write(creds.to_json())
        
        
@app.route("/")
def home():
    return "Google Slides Generation AI"

@app.route("/refresh_token", methods=["GET"])
def refresh_token():
    creds = None

    # Check if the token.json file exists
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if creds and creds.valid:
        return jsonify({"status": "valid", "message": "Token is still valid."})

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            save_credentials(creds)
            return jsonify({"status": "refreshed", "message": "Token successfully refreshed."})
        except Exception as e:
            return jsonify({"status": "failed", "message": f"Failed to refresh token: {str(e)}"})

    # If the token is invalid, redirect to the login URL
    auth_url, state = flow.authorization_url(prompt="consent")
    return jsonify({"status": "login_required", "auth_url": auth_url})

@app.route("/upload_credentials", methods=["POST"])
def upload_credentials():
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if file and file.filename.endswith(".json"):
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], "credentials.json")
        file.save(file_path)
        
        flow = Flow.from_client_secrets_file(   # update the flow for the Google Slides Project
            "credentials.json",
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        
        
        
        return jsonify({"message": "File uploaded and saved as credentials.json"}), 200
    
    try:
        os.remove('token.json')
    except Exception as e:
        print(f"Token didn't exist: {e}")

    return jsonify({"error": "Invalid file format. Please upload a JSON file."}), 400

@app.route("/oauth2callback", methods=["GET"])
def oauth2callback():
    """Handles the callback from Google OAuth."""
    try:
        flow.fetch_token(authorization_response=request.url)
        creds = flow.credentials
        save_credentials(creds)
        return jsonify({"status": "success", "message": "Token successfully saved."})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error during login: {str(e)}"})

@app.route("/generate_presentation", methods=["POST"])
def generate_presentation():
    data = request.get_json()

    # Extract client input, title, layout ID, background color, background image URL, and theme template ID
    client_intent = data.get("client_intent")
    title = data.get("title", "Generated Presentation")
    layout_id = data.get("layout_id")  # Layout ID for slide structure
    background_color = data.get("background_color")  # Hex color code (e.g., '#FF5733')
    background_image_url = data.get("background_image_url")  # Image URL for background
    #theme_template_id = data.get("theme_template_id")  # Template presentation ID for theme

    if not client_intent or not title:
        return jsonify({"error": "Client intent and title are required"}), 400

    if not layout_id:
        return jsonify({"error": "Layout ID is required to apply the theme"}), 400

    # Validate background options
    if background_color and background_image_url:
        return jsonify({"error": "Only one of background_color or background_image_url should be provided."}), 400

    # if theme_template_id and (background_color or background_image_url):
    #     return jsonify({"error": "Cannot apply a theme template along with background color or image."}), 400

    try:
        # Call the function to create presentation and pass all options
        presentation_id = create_presentation_from_database(
            client_intent, 
            title, 
            layout_id, 
            background_color=background_color, 
            background_image_url=background_image_url 
            #theme_template_id=theme_template_id
        )
        
        return jsonify({
            "message": "Presentation generated successfully.",
            "presentation_id": presentation_id
        }), 200

    except Exception as e:
        print(f"Error generating presentation: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/categorize_presentations", methods=["POST"])
def categorize_presentations():
    data = request.get_json()

    # Extract presentation IDs
    presentation_ids = data.get("presentation_ids")
    if not presentation_ids or not isinstance(presentation_ids, list):
        return jsonify({"error": "A list of presentation IDs is required"}), 400

    try:
        # Perform categorization with the provided presentation IDs
        perform_categorization_with_ids(presentation_ids)

        return jsonify({
            "message": "Categorization and tagging completed successfully.",
            "presentation_ids": presentation_ids
        }), 200

    except Exception as e:
        print(f"Error categorizing presentations: {e}")
        return jsonify({"error": str(e)}), 500
    
@app.route("/categorize_presentations_by_type", methods=["POST"])
def categorize_by_type():
    data = request.get_json()

    # Extract type
    categorization_type = data.get("type")
    if not categorization_type:
        return jsonify({"error": "Categorization type is required"}), 400

    try:
        # Perform categorization with the provided type
        perform_categorization_with_type(categorization_type)

        return jsonify({
            "message": f"Categorization and tagging for type '{categorization_type}' completed successfully."
        }), 200

    except Exception as e:
        print(f"Error categorizing by type: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)