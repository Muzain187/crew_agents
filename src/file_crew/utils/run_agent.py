import json
import logging,json,chromadb
import google.generativeai as genai
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_google_genai import ChatGoogleGenerativeAI
from file_crew.utils.agents.data_agent_bot.process import process_request

# --- Setup Logging ---
logging.basicConfig(
    filename="agent_chat.log",
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# --- Setup Gemini API ---
genai.configure(api_key="AIzaSyBolwbznjaVGHeB6bl_fwzWUvlK6KvgWqU")

# --- Chat memory and session ---
chat_memory = InMemoryChatMessageHistory()
session_id = "ashraf-session"
memory_store = {}

# --- Gemini LLM for chat ---
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash-002",
    temperature=0.5,
    google_api_key="AIzaSyBolwbznjaVGHeB6bl_fwzWUvlK6KvgWqU"
)

# --- Prompt with history ---
def build_prompt_with_history(question: str) -> str:
    history_text = ""
    for msg in chat_memory.messages:
        role = "User" if msg.type == "human" else "Assistant"
        history_text += f"{role}: {msg.content}\n"
    logging.debug(f"Built Prompt:\n{history_text}User: {question}\nAssistant:")
    return f"You are a helpful assistant. Here's the chat history:\n{history_text}User: {question}\nAssistant:"

# --- Classifier ---
def classify_input(user_input):
    prompt = (
        "You are a classifier. Return 'Agent1' for general questions like "
        "'what is AI', and 'Agent2' for structured API/task commands. "
        "Return only 'Agent1' or 'Agent2'.\n"
        f"Input: {user_input}"
    )
    logging.debug(f"Classifier Prompt:\n{prompt}")
    model = genai.GenerativeModel("gemini-1.5-flash-002")
    response = model.generate_content(prompt)
    classification = response.text.strip()
    logging.info(f"Classification Result: {classification}")
    return classification

# --- Follow-up resolution ---
def resolve_follow_up(user_input, memory):
    if not memory:
        logging.debug("No memory, returning input unchanged.")
        return user_input
    context = "\n".join(f"{k}: {v}" for k, v in memory.items())
    # prompt = (
    #     "Resolve follow-up user input based on the memory below.\n\n"
    #     f"Memory:\n{context}\n\n"
    #     f"Input: {user_input}\nResolved:"
    # )
    prompt = (
        "You are an assistant that rewrites follow-up user commands using the log memory provided.\n"  
        "Resolve any vague references like 'above source' or 'that field' using the most recently used or created values in memory.\n"  
        "In this case, if 'above source' appears, replace it with the latest sourceName, reconname or sourceDesc value from logs.\n"  
        "Return only the fully self-contained resolved command — no explanations, just the rewritten statement.\n\n"  
        f"Memory:\n{context}\n\n"    f"User Input: {user_input}\n\n"  
        f"Resolved Command:")
    logging.debug(f"Follow-up Prompt:\n{prompt}")
    model = genai.GenerativeModel("gemini-1.5-flash-002")
    response = model.generate_content(prompt)
    resolved = response.text.strip()
    logging.info(f"Resolved Input: {resolved}")
    return resolved

# --- Initialize Dataset in Vector DB ---
DATASET_COLLECTION_NAME = "command_dataset"
dataset_examples = [
    {
        "question": "create source s1",
        "description": "entity- source payload should be created successfully"
    },
    {
        "question": "create fields f1, f2 for the above source",
        "description": "entity- source_field_settings,source-configuration should be present with source name S1"
    },
    {
        "question": "create recon R1 and source s2",
        "description": "entity- recon & source payload should be created successfully"
    },
    {
        "question": "create fields f1, f2 for the above source",
        "description": "entity- source_settings_configure, source-configuration payload should be created with source name s2"
    },
    {
        "question": "create sides s1,s2 for the above recon",
        "description": "entity - recon_side_configure payload should be created with recon name R1"
    },
    {
        "question": "create recon fields t1, t2 for the previous recon",
        "description": "entity- recon_field_configure payload should be created with recon name R1"
    },
    {
        "question": "map above source to above recon",
        "description": "entity - recon_source_selected and recon_source_fields_mapping payload should be mapped  with recon name R1 and source name s2"
    },
    {
        "question": "create recon R1 of type custom recon",
        "description": "entity-Recon payload should be created successfully"
    },
    {
        "question": "create sides s1,s2 for the above recon",
        "description": "entity - recon_side_configure payload should be created with recon name R1"
    },
    {
        "question": "create recon fields t1, t2 for the previous recon",
        "description": "entity- recon_field_configure payload should be created with recon name R1"
    },
    {
        "question": "create recon r2, source s4,s5",
        "description": "entity-Recon & source payload should be created successfully"
    },
    {
        "question": "create sides s1,s2 for the above recon",
        "description": "entity - recon_side_configure payload should be created with recon name r2"
    },
    {
        "question": "create recon fields t1, t2 for the previous recon",
        "description": "entity- recon_field_configure payload should be created with recon name r2"
    },
    {
        "question": "create fields h1,h2 for the previous source",
        "description": "entity-source_field_settings,source-configuration should be present with source name S4"
    },
    {
        "question": "map above source to above recon",
        "description": "entity - recon_source_selected and recon_source_fields_mapping payload should be mapped  with recon name r2 and source name s4,s5"
    }
]

# --- Gemini Embedding Function ---
class GeminiEmbeddingFunction:
    def __init__(self, model_name="models/embedding-001"):
        self.model_name = model_name

    # NOTE: Parameter name must be 'input' to conform with ChromaDB's interface.
    def __call__(self, input):
        if isinstance(input, str):
            input = [input]
        embeddings = []
        for text in input:
            logging.debug(f"Generating Embedding for: {text}")
            response = genai.embed_content(
                model=self.model_name,
                content=text,
                task_type="retrieval_document"
            )
            embeddings.append(response["embedding"])
        logging.info(f"Generated {len(embeddings)} embeddings.")
        return embeddings

embedding_fn = GeminiEmbeddingFunction()

# --- Setup Main and Dataset ChromaDB Collections ---
chroma_client = chromadb.Client()

# Main collection for memory store.
memory_collection = chroma_client.get_or_create_collection(
    name="memory_store",
    embedding_function=embedding_fn
)
logging.info("Memory store ChromaDB collection initialized.")

# Collection for command dataset examples.
dataset_collection = chroma_client.get_or_create_collection(
    name=DATASET_COLLECTION_NAME,
    embedding_function=embedding_fn
)
logging.info("Command dataset ChromaDB collection initialized.")

# Check if dataset_collection is empty before adding examples.
try:
    if dataset_collection.count() == 0:
        logging.info("Populating command dataset collection with examples.")
        for example in dataset_examples:
            doc_id = f"{example['question']}_{example['description']}"
            document_text = f"Question: {example['question']}\nDescription: {example['description']}"
            dataset_collection.add(
                documents=[document_text],
                metadatas=[{"question": example['question'], "description": example['description']}],
                ids=[doc_id]
            )
except Exception as e:
    logging.warning("Could not use count(), trying alternative query method.")
    try:
        results = dataset_collection.query(query_texts=[" "], n_results=1)
        doc_count = sum(len(lst) for lst in results.get("documents", []))
    except Exception as e:
        logging.error("Error querying dataset collection: %s", e)
        doc_count = 0

    if doc_count == 0:
        logging.info("Populating command dataset collection with examples (alternative check).")
        for example in dataset_examples:
            doc_id = f"{example['question']}_{example['description']}"
            document_text = f"Question: {example['question']}\nDescription: {example['description']}"
            dataset_collection.add(
                documents=[document_text],
                metadatas=[{"question": example['question'], "description": example['description']}],
                ids=[doc_id]
            )

# --- Function to Query the Dataset Collection ---
def query_dataset_examples(query_text, n_results=1):
    logging.debug(f"Querying dataset collection for examples with: {query_text}")
    results = dataset_collection.query(query_texts=[query_text], n_results=n_results)
    examples = []
    if results.get("documents"):
        for doc_list in results["documents"]:
            for doc in doc_list:
                examples.append(doc)
    logging.debug(f"Retrieved examples: {examples}")
    return examples

# --- Interpret Command Using the LLM's Understanding of the Dataset Examples ---
def interpret_command_with_examples(user_input: str) -> str:
    # Retrieve relevant examples from the dataset.
    retrieved_examples = query_dataset_examples(user_input)
    
    # Instruct the LLM to first analyze these examples to understand the underlying logic.
    # Rather than just appending them as prompts, we ask it to consider the pattern.
    prompt = f"""
You are a skilled assistant who has learned the logic behind entity creation commands from a set of examples.
The following examples illustrate how various commands map to standardized entity creation descriptions:

Examples (for analysis only):
"""
    for ex in retrieved_examples:
        # Each example is provided for analysis; do not output verbatim
        prompt += f"- {ex}\n"
    
    prompt += f"""

Based on the logic found in these examples, analyze the command below and generate a standardized description.
Do not simply copy an example; rather, deduce the underlying rules:
Command: {user_input}
Standardized Description:"""

    logging.debug(f"Interpretation Prompt:\n{prompt}")
    model = genai.GenerativeModel("gemini-1.5-flash-002")
    response = model.generate_content(prompt)
    interpretation = response.text.strip()
    logging.info(f"Interpreted Command: {interpretation}")
    return interpretation

# --- Entity extraction ---
def extract_entities_or_memory_items(text: str) -> dict:
    prompt = (
        "Extract key-value pairs from the following message. "
        "Only return a Python dictionary.\n\n"
        f"Message:\n\"\"\"{text}\"\"\""
    )
    logging.debug(f"Entity Extraction Prompt:\n{prompt}")
    model = genai.GenerativeModel("gemini-1.5-flash-002")
    response = model.generate_content(prompt)
    try:
        content = response.text.strip()
        logging.debug(f"Raw Entity Response: {content}")
        return eval(content) if "{" in content else {}
    except Exception as e:
        logging.error(f"Entity Extraction Failed: {e}")
        return {}

# --- Merge memory ---
def merge_memory_store(memory_store, new_data):
    logging.debug(f"Merging New Data: {new_data}")
    for key, value in new_data.items():
        if isinstance(value, dict):
            if key in memory_store and isinstance(memory_store[key], dict):
                merge_memory_store(memory_store[key], value)
            else:
                memory_store[key] = value
        elif isinstance(value, list):
            if key in memory_store and isinstance(memory_store[key], list):
                memory_store[key].extend(value)
            else:
                memory_store[key] = value
        else:
            memory_store[key] = value
    logging.info(f"Updated Memory Store: {memory_store}")

def store_in_vector_db(key, value):
    doc_id = f"{key}:{str(value)}"
    logging.info(f"Storing to vector DB - ID: {doc_id}")
    memory_collection.add(
        documents=[f"{key} = {value}"],
        metadatas=[{"source": "agent2"}],
        ids=[doc_id]
    )

def query_vector_db(query):
    logging.debug(f"Querying vector DB with: {query}")
    results = memory_collection.query(query_texts=[query], n_results=1)
    logging.debug(f"Query Results: {results}")
    return results["documents"][0][0] if results["documents"] else None

def summarize_result(result: dict) -> str:
    try:
        model = genai.GenerativeModel("gemini-1.5-flash-002")
        prompt = f"""
You are an assistant that summarizes structured API results into readable sentences.

Summarize the following JSON response into a natural language sentence that clearly describes the action:


{json.dumps(result, indent=2)}

Note: do not include the method and url

Summary:
"""
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"⚠️ Could not summarize result: {e}"

# --- Main Chat Loop ---
while True:
    user_input = input("\nUser: ")

    if user_input.lower() in ["exit", "quit"]:
        logging.info("User exited the session.")
        print("Exiting...")
        break

    classification = classify_input(user_input)

    if classification == "Agent1":
        try:
            chat_memory.add_user_message(user_input)
            prompt = build_prompt_with_history(user_input)
            response = llm.invoke(prompt)
            answer = response.content if hasattr(response, "content") else response
            chat_memory.add_ai_message(answer)
            logging.info(f"Agent1 Answer: {answer}")
            print("Agent1:", answer)
        except Exception as e:
            logging.error(f"Agent1 Error: {e}")
            print("⚠️ Agent1 Error:", e)

    elif classification == "Agent2":
        try:
            resolved_input = resolve_follow_up(user_input, memory_store)
            # print("----------->resolved input:",resolved_input)
            logging.info(f"Resolved Input -> {resolved_input}")

            # interpreted_description = interpret_command_with_examples(resolved_input)
            # logging.info(f"Interpreted Description -> {interpreted_description}")

            # result = agent2.main(interpreted_description)
            result = process_request(resolved_input)
            merge_memory_store(memory_store, result)

            for entity in result.get("entities", []):
                key = entity.get("entity", "unknown")
                store_in_vector_db(key, entity)

            chat_memory.add_user_message(user_input)
            chat_memory.add_ai_message(json.dumps(result))
            logging.info(f"Agent2 Result: {result}")
            logging.info(f"Agent2:{summarize_result(result)}")
            print("Agent2:", summarize_result(result))

        except Exception as e:
            logging.error(f"Agent2 Error: {e}")
            print("⚠️ Agent2 Error:", e)

    else:
        logging.warning("Could not classify input properly.")
        print("🤖 Could not classify the input properly.")
