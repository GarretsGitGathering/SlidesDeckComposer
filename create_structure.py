import os
import json
from langchain import hub
from langchain.output_parsers.openai_tools import PydanticToolsParser
from langchain.prompts import PromptTemplate
from langchain_community.vectorstores import Chroma
from langchain_core.messages import BaseMessage, FunctionMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.runnables import RunnablePassthrough
from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from slidesOps import create_slide
from slidesOps import get_slides
from firebase_options import get_presentation_ids

slide_json_string = """"""

def separate_string_by_newlines(string):
    lines_array = string.split('\n\n')
    return lines_array
    
def write_string_to_file(file_path, input_string):
    with open(file_path, 'w') as file:
        file.write(input_string)
    print("String has been written to the file successfully.")

def create_structure(topic):
 # Prompt
  prompt = PromptTemplate(
        template="""You are a presenter assigned the task of creating a format for a slides presentation on a topic. \n
        
        Here is the topic:\n
        
        <topic>
        {topic}
        </topic>
       
        Here is a general slides format to follow:
        
        
            Title Slide:
                Title of the presentation
                Subtitle (if needed)
                Your name or the presenter's name
                Date
            raised by the audience
            \n
            Introduction:
                Brief overview of what the presentation is about
                Objectives or goals of the presentation
            raised by the audience
            \n
            Agenda:
                Outline of the topics or sections that will be covered
          raised by the audience
            \n
            Background/Context:
                Provide necessary background information or context for the audience to understand the topic
            raised by the audience
            \n
            Main Content Slides:
                Break down the main topics or sections of your presentation
                Use bullet points, images, graphs, or diagrams to support your points
                Keep text concise and use visuals to enhance understanding
            raised by the audience
            \n
            Data/Statistics:
                Present any relevant data or statistics to support your points
                Use graphs, charts, or tables to visualize the data
            raised by the audience
            \n
            Case Studies/Examples:
                Include real-life examples or case studies to illustrate your points
                Show how the concepts discussed are applied in practice
            raised by the audience
            \n
            Analysis/Findings:
                Analyze the data or information presented
                Discuss any findings or insights
           raised by the audience
            \n 
            Conclusion:
                Summarize the key points of the presentation
                Restate the main objectives or takeaways
            raised by the audience
            \n
            Recommendations/Next Steps:
                Provide recommendations based on the findings
                Outline any action steps or next steps to be taken
            raised by the audience
            \n
            Q&A:
                Invite the audience to ask questions
                Address any queries or concerns raised by the audience
            \n
            Thank You:
                Thank the audience for their time and attention
                Provide contact information for further inquiries or follow-up discussions
        
       
       only respond with the format you have created.
        """,
        input_variables=["topic"],
    )

  # LLM
  llm = ChatOpenAI(model_name="gpt-3.5-turbo-16k", temperature=0)

  # Post-processing
  def format_docs(docs):
      return "\n\n".join(doc.page_content for doc in docs)

  # Chain
  rag_chain = prompt | llm | StrOutputParser()

  # Run
  generation = rag_chain.invoke({"topic": topic})
  return generation
 
 
def generate_slides(format, generated_format_slides):
    # Prompt
    prompt = PromptTemplate(
            template="""You are a google slides designer assigned the task designing one slide based on the information you have been given. \n
    
            Here is the information you have been given: {slide} \n

            Here is an example of the use of the google slides API to generate a slide:

            <example>
            {example_slide}
            </example>
        
            please respond with your slide in json format according to the google slides api documentation to create all components of the slide.
            Make sure all objectID values are unique and the json data is inside of brackets [].
            
            Here are all of the objectIDs that have already been used in the project:
            
            {objectIDs}
            """,
            input_variables=["slide", "example_slide"],
        )

    # LLM
    llm = ChatOpenAI(model_name="gpt-3.5-turbo-16k", temperature=0)

    # Chain
    rag_chain = prompt | llm | StrOutputParser()

    slides = []
    objectID_array = []

    # TODO: include the generated slide format array items into this function

  # Run
    for slide in format:
        generation = rag_chain.invoke({"slide": slide, "example_slide": slide_json_string, "objectIDs": objectID_array})
        json_items = json.loads(generation)
        for item in json_items:  # Iterate over the list
            if "objectId" in item:  # Check if "objectId" exists in the item
                objectID_array.append(item["objectId"])  # Access "objectId" from the current dictionary item
            else:
                # Check if there is an item inside the current item that contains an "objectId"
                for sub_item in item.values():
                    if isinstance(sub_item, dict) and "objectId" in sub_item:
                        objectID_array.append(sub_item["objectId"])  # Access "objectId" from the sub-item
        slides.append(generation)

    return slides
  
 
if __name__ == "__main__":
    output = create_structure("how to tie your shoe")
  
    items = separate_string_by_newlines(output)
    for item in items:
        print(item)
        print("------------")
    
    json_items = generate_slides(items)
  
    fileNum = 0
  
    for item in json_items:
        fileNum+=1
        file = "slides/" + str(fileNum) + ".json"
        write_string_to_file(file, item)
        print("\n\n")

        # Call the function to add a new slide
        create_slide("1qXt_4Kllxp9oB9BNtNjJj182y22wUZtp8tzLqxCaRUg", file)
