import os
import json
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from langchain.prompts import PromptTemplate
from langchain.output_parsers.openai_tools import PydanticToolsParser
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from slidesOps import get_slides
from firebase_options import get_presentation_ids, update_document
from compile_presentation import choose_best_slide

# Path to your service account key file
SERVICE_ACCOUNT_FILE = 'slides_AI/slidesdatabase-c12eb-firebase-adminsdk-id40o-48ad49b096.json'

# Scopes required by Google Slides API
SCOPES = ['https://www.googleapis.com/auth/presentations', 'https://www.googleapis.com/auth/drive']

def authenticate_google_api():
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('slides', 'v1', credentials=credentials)
    return service

def create_presentation(service, title):
    # Create the presentation
    presentation = service.presentations().create(body={"title": title}).execute()
    presentation_id = presentation['presentationId']
    print(f'Created presentation with ID: {presentation_id}')

    # Get the first slide's objectId
    first_slide_id = presentation.get('slides', [{}])[0].get('objectId')
    if first_slide_id:
        print(f"Deleting first slide with ID: {first_slide_id}")
        try:
            # Prepare request to delete the slide
            delete_request = [
                {
                    "deleteObject": {
                        "objectId": first_slide_id
                    }
                }
            ]
            # Execute the batch update to delete the first slide
            service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={"requests": delete_request}
            ).execute()
            print(f"Deleted first slide with ID: {first_slide_id}")
        except Exception as e:
            print(f"Error deleting first slide: {e}")
    else:
        print("No first slide found to delete.")

    return presentation_id


def add_slide_to_presentation(service, new_presentation_id, source_presentation_id, slide):
    """Copy a slide from the source presentation to the new presentation."""
    requests = [
        {
            "duplicateObject": {
                "objectId": slide["objectId"],
                "objectIds": {
                    slide["objectId"]: "copied_" + slide["objectId"]
                }
            }
        }
    ]

    # Execute the duplication request
    response = service.presentations().batchUpdate(
        presentationId=source_presentation_id,
        body={"requests": requests}
    ).execute()

    copied_slide_id = response['replies'][0]['duplicateObject']['objectId']

    # Move the duplicated slide to the new presentation
    requests = [
        {
            "createSlide": {
                "objectId": copied_slide_id,
                "insertionIndex": 1,
                "slideLayoutReference": {
                    "predefinedLayout": "TITLE_AND_BODY"
                }
            }
        }
    ]

    response = service.presentations().batchUpdate(
        presentationId=new_presentation_id,
        body={"requests": requests}
    ).execute()

    return response

if __name__ == "__main__":
    # Initialize Firebase
    # Authenticate with Google Slides API
    service = authenticate_google_api()

    # Example client description and intention
    client_description = "A computer science student who probably drinks way too much caffeine. "
    client_intention = "I'm looking to buy energy drinks... of the watermelon variety..."

    categories = [
        "Title Slide", "Introduction", "Agenda", "Background/Context", "Main Content Slides",
        "Data/Statistics", "Case Studies/Examples", "Analysis/Findings", "Conclusion",
        "Recommendations/Next Steps", "Q&A", "Thank You"
    ]

    custom_presentation = []

    for category in categories:
        slides = get_slides_by_category_and_tags("categorized_slides", category, client_description)
        if slides:
            best_slide_objectId = choose_best_slide(slides, category, client_intention)
            best_slide = next((slide for slide in slides if slide["objectId"] == best_slide_objectId), None)
            if best_slide:
                custom_presentation.append(best_slide)

    # Create a new presentation
    presentation_title = "Custom Presentation for Client"
    presentation_id = create_presentation(service, presentation_title)

    # Add selected slides to the presentation
    for slide in custom_presentation:
        add_slide_to_presentation(service, presentation_id, slide)

    print("Custom presentation created and slides added successfully.")
