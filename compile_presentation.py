from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
import json
import tiktoken  # Ensure this library is installed

# Token limit constants
MODEL_TOKEN_LIMIT = 16384  # Total token limit for gpt-3.5-turbo-16k
SAFE_MARGIN = 500          # Reserved tokens for the prompt and response

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

def choose_best_slide(slides, category, client_intention):
    # Define the prompt template
    prompt_template = """
        You are a presentation expert. Given the client's intention, choose the best slide from the list of slides provided for a specific category.
        
        Client Intention: {client_intention}
        Slide Category: {category}
        Slides: {slides}
        
        Please respond with the objectId of the best slide from the list.
    """

    # Initialize the LLM
    llm = ChatOpenAI(model_name="gpt-3.5-turbo-16k", temperature=0)

    # Calculate available tokens for slides
    prompt_static = prompt_template.format(
        client_intention=client_intention,
        category=category,
        slides=""
    )
    static_tokens = len(tokenizer.encode(prompt_static))
    available_tokens = MODEL_TOKEN_LIMIT - static_tokens - SAFE_MARGIN

    # Truncate slides data
    slides_data = json.dumps(slides, indent=2)  # Prettified JSON to improve AI comprehension
    truncated_slides_data = truncate_text(slides_data, available_tokens)

    # Format the prompt
    prompt = prompt_template.format(
        client_intention=client_intention,
        category=category,
        slides=truncated_slides_data
    )

    # Run the AI model to choose the best slide
    best_slide = llm(prompt).strip()  # Assuming the model returns the objectId of the best slide
    
    return best_slide


def write_slides_to_file(slides, file_path):
    with open(file_path, 'w') as file:
        json.dump(slides, file, indent=4)
    print("Slides have been written to the file successfully.")
