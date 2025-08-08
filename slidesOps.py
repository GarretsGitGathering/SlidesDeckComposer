import os.path
import json
import time
import uuid

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/presentations"]


# initialize the slides service
def initialize_slides_service():
  creds = None
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())

  service = build("slides", "v1", credentials=creds)
  return service

def get_slides(presentation_id):
    # Build the Google Slides service
    service = initialize_slides_service()

    # Call the Google Slides API to retrieve all slides from the presentation
    presentation = service.presentations().get(presentationId=presentation_id).execute()

    # Initialize an empty array to store slide contents
    slides_content = []

    # Iterate over each slide in the presentation
    for slide in presentation['slides']:
        slide_content = ""
        slides_content.append(slide)
        # Iterate over each element (text, shapes, etc.) in the slide
        # for element in slide['pageElements']:
        #     #if "textRUN" in element:
        #     slides_content.append(element)
        #     # Append the slide_content to the slides_content array
        #     #slides_content.append(element)

    # Print the array of slide contents
    return slides_content

def create_slide(presentation_id, file_name):
  try:
    service = initialize_slides_service() # build the slides service connection

    #print(request)

    # Load JSON data from file
    with open(file_name) as json_file:
        request_format = json.load(json_file)

    # Execute the request.
    body = {"requests": request_format}
    response = (service.presentations().batchUpdate(presentationId=presentation_id, body=body).execute())

    create_slide_response = response.get("replies")[0].get("createSlide")
    print(f"Created slide with ID:{(create_slide_response.get('objectId'))}")


  except HttpError as error:
    print(f"An error occurred: {error}")
    print("Slides not created")
    return error

  #return response
  
def generate_unique_object_id(base_id):
    """Generate a unique object ID using a base ID."""
    return f"{base_id}_{uuid.uuid4().hex[:8]}"

def copy_slide(source_presentation_id, slide_object_id, destination_presentation_id):
    try:
        service = initialize_slides_service()  # Initialize the Slides API service

        # Get the source presentation data
        source_presentation = service.presentations().get(
            presentationId=source_presentation_id
        ).execute()

        # Find the source slide
        source_slide = None
        for slide in source_presentation["slides"]:
            if slide["objectId"] == slide_object_id:
                print("\nFOUND SLIDE\n")
                source_slide = slide
                break

        if source_slide is None:
            print(f"Slide {slide_object_id} not found in source presentation.")
            return {"status": "error", "message": "Slide not found"}

        # Extract slide elements
        slide_elements = source_slide.get("pageElements", [])
        print(f"Found {len(slide_elements)} elements in source slide.")

        # Create a new slide in the destination presentation
        new_slide_id = generate_unique_object_id("new_slide")
        create_slide_request = [
            {"createSlide": {"objectId": new_slide_id}}
        ]
        create_response = service.presentations().batchUpdate(
            presentationId=destination_presentation_id,
            body={"requests": create_slide_request}
        ).execute()

        print(f"Created new slide with ID: {new_slide_id}")

        # Get the ID of the new slide
        new_slide_id = create_response["replies"][0]["createSlide"]["objectId"]

        # Prepare requests to replicate elements on the new slide
        requests = []

        for element in slide_elements:
            element_id = element["objectId"]
            try:
                # Handle shape elements
                if "shape" in element:
                    shape = element["shape"]
                    text_content = shape.get("text", {}).get("textElements", [])
                    shape_type = shape.get("shapeType", "TEXT_BOX")

                    # Create the shape
                    requests.append(
                        {
                            "createShape": {
                                "objectId": f"copied_{element_id}",
                                "shapeType": shape_type,
                                "elementProperties": {
                                    "pageObjectId": new_slide_id,
                                    "size": element.get("size", {}),
                                    "transform": element.get("transform", {}),
                                },
                            }
                        }
                    )

                    # Add text to the shape
                    for text_element in text_content:
                        if "textRun" in text_element:
                            requests.append(
                                {
                                    "insertText": {
                                        "objectId": f"copied_{element_id}",
                                        "text": text_element["textRun"]["content"],
                                    }
                                }
                            )

                # Handle image elements
                elif "image" in element:
                    image_url = element["image"].get("contentUrl", "")
                    if image_url:
                        # Create the image
                        requests.append(
                            {
                                "createImage": {
                                    "url": image_url,
                                    "elementProperties": {
                                        "pageObjectId": new_slide_id,
                                        "size": element.get("size", {}),
                                        "transform": element.get("transform", {}),
                                    },
                                }
                            }
                        )

                # Handle other elements (e.g., titles, placeholders)
                else:
                    print(f"Adding placeholder or unknown element: {element_id}")
                    requests.append(
                        {
                            "createShape": {
                                "objectId": f"copied_{element_id}",
                                "shapeType": "TEXT_BOX",  # Default to TEXT_BOX for placeholders
                                "elementProperties": {
                                    "pageObjectId": new_slide_id,
                                    "size": element.get("size", {}),
                                    "transform": element.get("transform", {}),
                                },
                            }
                        }
                    )
            except Exception as element_error:
                print(f"Error copying element {element_id}: {element_error}")
                continue  # Skip this element and proceed with the rest

        # Execute the batch update to add all elements to the new slide
        if requests:
            try:
                batch_response = service.presentations().batchUpdate(
                    presentationId=destination_presentation_id,
                    body={"requests": requests}
                ).execute()
                print(f"Batch update response: {batch_response}")
            except Exception as batch_error:
                print(f"Error executing batch update for elements: {batch_error}")
                return {"status": "partial_success", "message": "Slide copied partially due to errors"}

        print(f"Successfully copied content from slide {slide_object_id} to new slide {new_slide_id}")
        return {"status": "success", "new_slide_id": new_slide_id}

    except Exception as e:
        print(f"Error copying slide: {e}")
        return {"status": "error", "message": str(e)}
    

def create_presentation(service, title):
    presentation = service.presentations().create(body={"title": title}).execute()
    presentation_id = presentation['presentationId']
    first_slide_id = presentation.get('slides', [{}])[0].get('objectId')
    print(f'Created presentation with ID: {presentation_id}')
    print(f'First slide ID: {first_slide_id if first_slide_id else "No first slide"}')
    return presentation_id, first_slide_id


def delete_first_slide(service, presentation_id, first_slide_id):
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


def apply_theme_to_slide(presentation_id, slide_id, layout_id):
    try:
        service = initialize_slides_service()  # Initialize the Slides API service

        # Batch update request to apply the theme layout
        requests = [
            {
                "updateSlideProperties": {
                    "slideObjectId": slide_id,
                    "slideProperties": {
                        "layoutObjectId": layout_id
                    },
                    "fields": "layoutObjectId"
                }
            }
        ]

        # Execute the batch update
        response = service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={"requests": requests}
        ).execute()

        print(f"Theme layout with ID '{layout_id}' applied to slide '{slide_id}'.")
        return {"status": "success", "layout_id": layout_id, "slide_id": slide_id}

    except HttpError as error:
        print(f"An error occurred: {error}")
        return {"status": "error", "message": str(error)}
    
    
def set_slide_background_color(presentation_id, slide_id, color_hex):
    # Convert hex color to RGB values
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip("#")
        return {
            "red": int(hex_color[0:2], 16) / 255.0,
            "green": int(hex_color[2:4], 16) / 255.0,
            "blue": int(hex_color[4:6], 16) / 255.0,
        }

    service = initialize_slides_service()

    requests = [
        {
            "updatePageProperties": {
                "objectId": slide_id,
                "pageProperties": {
                    "pageBackgroundFill": {
                        "solidFill": {
                            "color": {
                                "rgbColor": hex_to_rgb(color_hex)
                            }
                        }
                    }
                },
                "fields": "pageBackgroundFill"
            }
        }
    ]

    response = service.presentations().batchUpdate(
        presentationId=presentation_id,
        body={"requests": requests}
    ).execute()

    print(f"Background color set to {color_hex} for slide {slide_id}")


def set_slide_background_image(presentation_id, slide_id, image_url):
    service = initialize_slides_service()

    requests = [
        {
            "updatePageProperties": {
                "objectId": slide_id,
                "pageProperties": {
                    "pageBackgroundFill": {
                        "stretchedPictureFill": {
                            "contentUrl": image_url
                        }
                    }
                },
                "fields": "pageBackgroundFill"
            }
        }
    ]

    response = service.presentations().batchUpdate(
        presentationId=presentation_id,
        body={"requests": requests}
    ).execute()

    print(f"Background image set for slide {slide_id}")


def apply_theme_from_template(presentation_id, template_presentation_id):
    """
    Apply a theme from a template presentation to all slides in a new presentation.

    Args:
        presentation_id (str): ID of the target presentation to apply the theme.
        template_presentation_id (str): ID of the template presentation containing the desired theme.

    Returns:
        dict: Status of the theme application.
    """
    try:
        service = initialize_slides_service()

        # Get the template presentation details
        template_presentation = service.presentations().get(
            presentationId=template_presentation_id
        ).execute()

        # Get layouts from the template presentation
        layouts = template_presentation.get("layouts", [])
        if not layouts:
            return {"status": "error", "message": "No layouts found in template presentation"}

        # Use the first layout as the default layout for the slides
        default_layout_id = layouts[0]["objectId"]

        # Get the slides of the new presentation
        presentation = service.presentations().get(presentationId=presentation_id).execute()
        slides = presentation.get("slides", [])

        requests = []

        for slide in slides:
            # Apply the layout to each slide using the layoutObjectId
            requests.append(
                {
                    "updateSlideProperties": {
                        "objectId": slide["objectId"],
                        "slideProperties": {
                            "layoutObjectId": default_layout_id
                        },
                        "fields": "layoutObjectId"
                    }
                }
            )

        # Execute the batch update to apply the theme layout
        response = service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={"requests": requests}
        ).execute()

        print(f"Applied theme layout from template {template_presentation_id} to presentation {presentation_id}")
        return {"status": "success", "message": f"Theme applied from {template_presentation_id}"}

    except Exception as e:
        print(f"Error applying theme: {e}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
  # Put the presentation_id, Page_id of slides whose list needs
  # to be submitted.

  #create_slide("1qXt_4Kllxp9oB9BNtNjJj182y22wUZtp8tzLqxCaRUg", 'slides/1.json')
  copy_slide("1K9H8tQ3DUniiyJVqry-LlT1US2sU8u9cpftWk35j-Jg", "g28b01858972_0_0", "1qXt_4Kllxp9oB9BNtNjJj182y22wUZtp8tzLqxCaRUg")
