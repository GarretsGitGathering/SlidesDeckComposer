from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
import json
import os
import time
import tiktoken

from firebase_options import get_slides_by_category
from create_structure import create_structure, separate_string_by_newlines
from slidesOps import copy_slide, initialize_slides_service, create_presentation, delete_first_slide, apply_theme_to_slide, set_slide_background_color, set_slide_background_image, apply_theme_from_template

# Token limit constants
MODEL_TOKEN_LIMIT = 16384  # Total token limit for gpt-3.5-turbo-16k
SAFE_MARGIN = 500          # Reserved tokens for the prompt and respon

# Tokenizer for token counting
tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo-16k")

def truncate_text(text, max_tokens):
    """Truncate the input text to fit within the specified token limit."""
    tokens = tokenizer.encode(text)
    if len(tokens) > max_tokens:
        truncated_text = tokenizer.decode(tokens[:max_tokens])
        print(f"Text truncated to {max_tokens} tokens.")
        return truncated_text
    return text

def choose_best_slide(slide_options, slide_goal, category, client_intent):
    # Define the prompt
    prompt = PromptTemplate(
        template="""
        You are a presentation expert. Given the client's intention, the slide goal, and category, choose the best slide out of the slide options.
        Client Intention: {client_intention}
        Slide Category: {category}
        Slide Goal: {slide_goal}
        
        Here are the slide options:
        <slide_options>
            {slide_options}        
        </slide_options>
        Please respond with the objectId and presentation_id of the slide that fits the best into the new presentation.
                                
        Your response should be in JSON and have this data: 
        {{
            "presentation_id": "*presentation_id of best fitting*", 
            "objectId": "*objectId of best fitting*"
        }}
        
        Please only respond with JSON, as we will be parsing your entire response.
        """,
        input_variables=["client_intention", "category", "slide_goal", "slide_options"]
    )

    # Initialize the LLM
    llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)

    # Chain setup
    rag_chain = prompt | llm | StrOutputParser()

    # Serialize slides to JSON format
    try:
        slides_data = json.dumps(slide_options, indent=2)
    except Exception as e:
        print(f"Error serializing slides to JSON: {e}")
        return None

    # Calculate token budget for truncation
    tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
    max_tokens = 4096 - 500  # Reserve 500 tokens for prompt and response

    # Truncate slides data using provided function
    truncated_slides = truncate_text(slides_data, max_tokens)
    print("Serialized and Truncated Slides JSON:", truncated_slides)

    # Invoke the chain
    try:
        best_slide_id = rag_chain.invoke({
            "client_intention": client_intent,
            "category": category,
            "slide_goal": slide_goal,
            "slide_options": truncated_slides
        })
        return best_slide_id.strip()
    except Exception as e:
        print(f"Error in slide selection: {e}")
        return None

def create_presentation_from_database(client_intent, title, layout_id, background_color=None, background_image_url=None):
    structure = create_structure(client_intent)  # Create the structure
    components = separate_string_by_newlines(structure)  # Break down by components

    service = initialize_slides_service()
    new_presentation_id, first_slide_id = create_presentation(service, title)
            
    # now delete the first slide
    delete_first_slide(service, new_presentation_id, first_slide_id)

    # Iterate through each slide intention
    for component in components:
        category = component.split("\n")[0].strip(":").strip()  # Remove colons and whitespace
        print(f"Finding slide of category: {category}")

        relevant_slides = get_slides_by_category("categorized_slides", category)  # Get slides of category from Firestore

        # Format the slide data to pass only summary, presentation_id, and object_id
        formatted_slides = []
        for slide in relevant_slides:
            slide_summary = slide.get("summary", "No summary available")
            presentation_id = slide.get("presentation_id", "Unknown presentation")
            object_id = slide.get("objectId", "Unknown slide ID")

            # Create a string representation of the slide data
            slide_string = f"Slide Summary: {slide_summary}\nPresentation ID: {presentation_id}\nSlide ID: {object_id}"
            formatted_slides.append(slide_string)

        # Find the best fitting slide using the formatted slide data
        best_fitting_slide = choose_best_slide(formatted_slides, component, category, client_intent)

        best_fitting_slide_data = json.loads(best_fitting_slide)  # Load JSON data from the response
        presentation_id = best_fitting_slide_data["presentation_id"]  # Parse the presentation ID
        slide_id = best_fitting_slide_data["objectId"]  # Parse the object ID

        # Copy the slides over to the new presentation
        response = copy_slide(presentation_id, slide_id, new_presentation_id)
        time.sleep(2)

        if response.get("status") == "success":
            new_slide_id = response["new_slide_id"]
            print(f"Successfully added slide {slide_id} from {presentation_id} to new presentation {new_presentation_id}")

            # Only apply individual background settings if no theme template is applied
            #if not theme_template_id:
            if background_color:
                set_slide_background_color(new_presentation_id, new_slide_id, background_color)
                print(f"Background color {background_color} applied to slide {new_slide_id}")
            elif background_image_url:
                set_slide_background_image(new_presentation_id, new_slide_id, background_image_url)
                print(f"Background image {background_image_url} applied to slide {new_slide_id}")

            # Apply the theme layout to the new slide
            apply_theme_to_slide(new_presentation_id, new_slide_id, layout_id)
            print(f"Theme applied to slide {new_slide_id}\n")
        else:
            print(f"Failed to copy slide {slide_id} to new presentation {new_presentation_id}")

    return new_presentation_id


def main():
    # Mock test inputs for presentation creation
    client_intent = """
    Introduction:
    Discuss the goals and purpose of the meeting.

    Marketing Strategy:
    Explain the Q1 marketing goals and key objectives.

    Financial Overview:
    Present the revenue and expense breakdown for the last quarter.
    """
    title = "Q1 Business Strategy Presentation"
    layout_id = "TITLE_AND_BODY"  # Example layout ID; replace if needed
    background_color = "#F5B7B1"  # Optional background color (hex code)
    background_image_url = None  # Optional background image URL
    theme_template_id = "1WgBSf5zVG3oO0n-3B_l9zZC41T2LfuSl0iTwEaE2uT8"  # Example theme presentation ID

    try:
        # Call the function and print results
        print("Starting presentation creation...")
        presentation_id = create_presentation_from_database(
            client_intent=client_intent,
            title=title,
            layout_id=layout_id,
            background_color=background_color,
            background_image_url=background_image_url
            #theme_template_id=theme_template_id
        )
        print(f"Presentation created successfully with ID: {presentation_id}")

    except Exception as e:
        print(f"An error occurred during presentation creation: {e}")


if __name__ == "__main__":
    main()
