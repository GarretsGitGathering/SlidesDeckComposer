import os
import time
import json
from langchain import hub
from langchain.output_parsers.openai_tools import PydanticToolsParser
from langchain.prompts import PromptTemplate
from langchain_community.vectorstores import Chroma
from langchain_core.messages import BaseMessage, FunctionMessage
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnablePassthrough
from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_openai import ChatOpenAI

from slidesOps import get_slides
from firebase_options import get_presentation_ids, update_document

def summarize_slide(slides):
        # Define the prompt template
    prompt = PromptTemplate(
        template="""
        Your task is to summarize the following slide from received from the google slides api. Please summarize the slide, making sure to mention the content and purpose of the slide.
        \n\n
        <Slide Content>{slide}</Slide Content>
        \n\n
        Please only respond with your summary of the slide, making sure to mention the content and purpose of the slide.
        """,
        input_variables=["slide"]
    )

    # Initialize the LLM
    llm = ChatOpenAI(model_name="gpt-3.5-turbo-16k", temperature=0)

    # Chain setup
    rag_chain = prompt | llm | StrOutputParser()

    summarized_slides_json = []

    # Run the categorization process
    for slide in slides:

        summary = rag_chain.invoke({"slide": slide})
        summarized_slides_json.append({"slide": slide,"summary": summary})

        objectID = slide.get("objectId", None)
        print("SUMMARIZING SLIDE" + str(objectID))

    print("SUMMERIZATION COMPLETE")
    return summarized_slides_json


def categorize_slides(summarized_slides):
    # Define the prompt template
    prompt = PromptTemplate(
        template="""
        Your task is to categorize the following slide summary into a category that best matches some categories. Please pay the most attention to the text content of each slide, an example being some text saying "Agenda" would likely be in the agenda category.
        \n\n
        <Slide Summary>{slide_summary}</Slide Summary>
        \n\n
        Please only respond with one of the following categories spelled exactly the same:
        \n
            Title Slide\n
            Introduction\n
            Agenda\n
            Background/Context\n
            Main Content Slides\n
            Data/Statistics\n
            Case Studies/Examples\n
            Analysis/Findings\n
            Conclusion\n
            Recommendations/Next Steps\n
            Q&A\n
            Thank You\n
        """,
        input_variables=["slide_summary"]
    )

    # Initialize the LLM
    llm = ChatOpenAI(model_name="gpt-3.5-turbo-16k", temperature=0)

    # Chain setup
    rag_chain = prompt | llm | StrOutputParser()

    categorized_slides_json = []

    # Run the categorization process
    for summarized_slide in summarized_slides:

        slide_data = summarized_slide.get("slide", "{}")  # Default to an empty JSON object if "slide" key is missing
        slide_data = json.dumps(slide_data) # dump the json data to a string
        slide = json.loads(slide_data)  # Load the stringified slide data as JSON

        # Access the objectId from the slide
        objectID = slide.get("objectId", None)
        print("objectID: " + str(objectID))

        category = rag_chain.invoke({"slide_summary": summarized_slide["summary"]})
        categorized_slides_json.append({"slide": slide_data, 
                                        "summary": summarized_slide["summary"], 
                                        "category": category})
        print("CATEGORIZING SLIDE: " + str(category))

    print("CATEGORIZATION COMPLETE")
    return categorized_slides_json
    
def tag_slides(categorized_slides):
    prompt = PromptTemplate(
        template="""
        Your task is to tag the following slide summary with keywords based on its content. Consider the main points and purpose of the slide for tagging.
        \n\n
        <Slide Summary>{slide_summary}</Slide Summary>
        \n\n
        Please respond with a list of tags, separated by commas.
        """,
        input_variables=["slide_summary"]
    )

    llm = ChatOpenAI(model_name="gpt-3.5-turbo-16k", temperature=0)
    rag_chain = prompt | llm | StrOutputParser()
    tagged_slides_json = []

    for categorized_slide in categorized_slides:
        tags = rag_chain.invoke({"slide_summary": categorized_slide["summary"]})
        tagged_slides_json.append({
            "slide": categorized_slide["slide"],
            "summary": categorized_slide["summary"],
            "category": categorized_slide["category"],
            "tags": tags
        })
        print("TAGGING SLIDE: " + str(tags))

    print("TAGGING COMPLETE")
    return tagged_slides_json


def send_slides_to_Firebase(tagged_slides, presentation_id):
    for tagged_slide in tagged_slides:
        category = tagged_slide["category"]
        summary = tagged_slide["summary"]
        tags = tagged_slide["tags"]
        slide_data = tagged_slide.get("slide", "{}")
        slide = json.loads(slide_data) if isinstance(slide_data, str) else slide_data
        objectId = slide.get("objectId", None)
        
        # Construct a unique document ID
        document_id = f"slide-{objectId}-{int(time.time())}"
        print("objectID: " + str(objectId))

        # Update each field individually
        update_document("categorized_slides", document_id, "category", category)
        update_document("categorized_slides", document_id, "summary", summary)
        update_document("categorized_slides", document_id, "slide", str(slide))
        update_document("categorized_slides", document_id, "tags", tags)
        update_document("categorized_slides", document_id, "presentation_id", presentation_id)
        update_document("categorized_slides", document_id, "objectId", objectId, field_path=True)

    print("SLIDES UPDATED IN FIREBASE")

def write_slides_to_file(slides, filename):
    with open(filename, 'w') as file:
        for slide in slides:
            file.write(f"{slide}\n\n")  # Add extra newline for better readability

    print("WRITTEN SLIDE FORMATS TO FILE")



def perform_categorization_with_ids(presentation_ids):
    # Step 1: get slides
    presentations = [get_slides(presentation_id) for presentation_id in presentation_ids]
    print("got slides for the presentations")

    # Step 2: Summarize, categorize, and tag slides
    summarized_presentations = [summarize_slide(presentation) for presentation in presentations]
    categorized_presentations = [categorize_slides(summarized_presentation) for summarized_presentation in summarized_presentations]
    tagged_presentations = [tag_slides(categorized_presentation) for categorized_presentation in categorized_presentations]

    # Step 3: Send slides to Firebase
    for presentation_id, tagged_presentation in zip(presentation_ids, tagged_presentations):
        send_slides_to_Firebase(tagged_presentation, presentation_id)


def perform_categorization_with_type(type):
    # Step 1: Get presentation IDs and slides
    
    presentation_ids = get_presentation_ids(type)
    print(f"got {type} presentation ids")
    
    presentations = [get_slides(presentation_id) for presentation_id in presentation_ids]
    print("got slides for the presentations")

    # Step 2: Summarize, categorize, and tag slides
    summarized_presentations = [summarize_slide(presentation) for presentation in presentations]
    categorized_presentations = [categorize_slides(summarized_presentation) for summarized_presentation in summarized_presentations]
    tagged_presentations = [tag_slides(categorized_presentation) for categorized_presentation in categorized_presentations]

    # Step 3: Send slides to Firebase
    for presentation_id, tagged_presentation in zip(presentation_ids, tagged_presentations):
        send_slides_to_Firebase(tagged_presentation, presentation_id)


if __name__ == "__main__":
    perform_categorization_with_type("formal")






    # # Organize and categorize the slides
    # organized_slides = organize_slides(categorized_presentations)

    # # Create the format from the organized_slides
    # format = create_format(organized_slides)

    # # Write to a file
    # write_slides_to_file(format, "generated_format.txt")

    # for slide in format:
    #     print(slide)
    #     print("\n\n")
