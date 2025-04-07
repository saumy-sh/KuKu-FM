import os
import json
import re
import spacy
from dotenv import load_dotenv
from openai import OpenAI
from transformers import T5Tokenizer, T5ForConditionalGeneration

# Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

# Load T5 summarizer
t5_tokenizer = T5Tokenizer.from_pretrained("t5-small")
t5_model = T5ForConditionalGeneration.from_pretrained("t5-small")

# --- Function to extract characters ---
def extract_characters(text, existing_characters=None, killed_characters=None):
    if existing_characters is None:
        existing_characters = set()
    if killed_characters is None:
        killed_characters = set()

    # Normalize existing and killed characters to lowercase
    existing_characters = set(name.lower() for name in existing_characters)
    killed_characters = set(name.lower() for name in killed_characters)

    doc = nlp(text)

    # Extract PERSON entities and normalize to lowercase
    new_characters = set(ent.text.strip().lower() for ent in doc.ents if ent.label_ == "PERSON")

    updated_list = (existing_characters | new_characters) - killed_characters
    return updated_list


# --- Safe JSON Parsing ---
def safe_json_parse(response_text):
    response_text = response_text.strip().strip("`")
    response_text = re.sub(r'(?<!\\)\n', '\\n', response_text)
    response_text = response_text.replace("“", "\"").replace("”", "\"")
    try:
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        print("⚠️ Failed to parse GPT response into JSON.")
        print("Returned text was:\n", response_text)
        raise e

# --- OpenAI Summarization ---
def summarize_with_openai(text):
    summary_prompt = f"""
You are an expert story summarizer. Provide a well-written abstract summary of the following story text. 
Do not just extract sentences—summarize like a human would, preserving key events and emotions.

Text:
{text[:3000]}  # Limit input to avoid long token usage
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": summary_prompt.strip()}],
        temperature=0.7,
        max_tokens=300,
    )
    return response.choices[0].message.content.strip()



# --- T5 Summarization ---
def summarize_with_t5(text, max_length=150):
    # Use a prompt that signals extractive behavior
    input_text = (
        "give me an abstractive summary of this story."
        + text.strip().replace("\n", " ")
    )
    
    inputs = t5_tokenizer.encode(input_text, return_tensors="pt", max_length=512, truncation=True)
    
    summary_ids = t5_model.generate(
        inputs,
        max_length=max_length,
        min_length=60,
        length_penalty=1.0,   # Lower value encourages longer output
        num_beams=4,
        early_stopping=True,
        no_repeat_ngram_size=3  # Reduce repetitive output
    )
    
    return t5_tokenizer.decode(summary_ids[0], skip_special_tokens=True)


# --- Episode generation using OpenAI ---
def generate_episode(
    episode_number, total_episodes, summary_context=None, previous_characters=None,
    tone="Comedic", trope=None, style="Third Person", required_characters=None
):
    required_character_note = (
        f"The following characters **must appear** in this episode: {', '.join(required_characters)}.\n"
        if required_characters else ""
    )

    system_prompt = f"""
You are an expert storyteller. The story's trope is {trope if trope else "whatever you like"}.
Create episode {episode_number} out of {total_episodes} of a long-form story.
The story genre is {tone}. It follows {style} style.
Maintain consistency with previous summaries and character arcs.
Include rich dialogue, setting, and plot advancement.
{required_character_note}
If characters are mentioned previously, ensure they are used unless they are dead.
Introduce new characters only when necessary. Remove characters that were killed.
Also in title only return the title you have given without episode number.

Return the output in STRICT VALID JSON format without any markdown formatting or triple backticks.
Escape all newlines inside the "body" field using \\n.

JSON format:
{{
  "title": "...",
  "body": "...",
  "killed_characters": ["..."],
  "current_characters": ["..."]
}}

Always try to end the episode with a cliffhanger if possible.
"""

    user_prompt = f"""
Episode Number: {episode_number}
Previous Summary: {summary_context if summary_context else "no context"}
Characters So Far: {previous_characters if previous_characters else 'N/A'}

Write an episode of around 500–800 words. Maintain narrative consistency.
Update the current_characters field by removing killed_characters and including any new ones introduced in this episode.
"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()}
        ],
        temperature=0.9,
        max_tokens=1800,
    )

    result = response.choices[0].message.content
    return safe_json_parse(result)



      

# --- Parameters ---
no_of_episodes = 2
title = "A Rat and a Cat"
initial_characters = set(["jerry", "tom"])
trope = "a house where jerry tries to kill the house master but tom protects the master."
tone = "Comedic"
style = "Third Person"
total_summary = ""

# --- Story creation with multiple episodes functionality ---

def create_story(title=None, no_of_episodes=1, trope=None, tone="Comedic", style="Third Person", initial_characters=None):
    story_root = "story"
    story_folder = os.path.join(story_root, title)
    os.makedirs(story_folder, exist_ok=True)

    info = {
        'total_episodes': no_of_episodes,
        'title': title,
        'initial_characters': list(initial_characters),
        'trope': trope,
        'style': style,
        'tone': tone
    }

    with open(os.path.join(story_folder, "info.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2)

    total_summary = ""

    # Generate first episode with required characters
    story = generate_episode(
        1, 
        no_of_episodes,
        trope=trope,
        tone=tone,
        style=style,
        required_characters=list(initial_characters)
    )
    total_summary += summarize_with_openai(story['body'])
    story["summary_till_now"] = total_summary
    with open(os.path.join(story_folder, "1.json"), "w", encoding="utf-8") as f:
        json.dump(story, f, indent=2)

    # Loop for remaining episodes
    for episode in range(2, no_of_episodes + 1):
        story = generate_episode(
            episode,
            no_of_episodes,
            summary_context=total_summary,
            previous_characters=story["current_characters"],
            tone=tone,
            trope=trope,
            style=style
        )
        total_summary += "\n" + summarize_with_openai(story['body'])
        story["summary_till_now"] = total_summary

        with open(os.path.join(story_folder, f"{episode}.json"), "w", encoding="utf-8") as f:
            json.dump(story, f, indent=2)
