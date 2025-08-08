import os
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

def generic_prompt(question):
 # Prompt
  prompt = PromptTemplate(
        template="""You are a grader assessing whether a statement is a question. \n
 
        Here is the user question: {question} \n
       
        Give a binary score 'yes', 'partially', or 'no' score to indicate whether the document is relevant to the question.""",
        input_variables=["question"],
    )

  # LLM
  llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)

  # Post-processing
  def format_docs(docs):
      return "\n\n".join(doc.page_content for doc in docs)

  # Chain
  rag_chain = prompt | llm | StrOutputParser()

  # Run
  generation = rag_chain.invoke({"question": question})
  return generation
  
 
if __name__ == "__main__":
  output = generic_prompt("where are my pants")
  print(output)
  
  output2 = generic_prompt("i dont likr cheese")
  print(output2)
