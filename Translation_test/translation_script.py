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
    try:
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        # Attempt to fix unescaped backslashes
        fixed = re.sub(r'(?<!\\)\\(?![\\nrt"])', r'\\\\', response_text)
        try:
            return json.loads(fixed)
        except Exception as e2:
            print("Failed JSON:", fixed[:500])
            raise e2  # Re-raise if still failing

# --- OpenAI Summarization ---
def summarize_with_openai(text, previous_summary=None):
    if previous_summary:
        summary_prompt = f"""
You are an expert story summarizer. Continue building on the previous episode's summary in a natural and seamless way.
Merge the important events and emotional highlights from the current story text with the previous summary to form one continuous narrative.

Previous Summary:
{previous_summary}

Current Episode Text:
{text[:3000]}  # Truncated to avoid token overuse

Return a single, flowing summary that reads like one continuous abstract.
"""
    else:
        summary_prompt = f"""
You are an expert story summarizer. Provide a well-written abstract summary of the following story text.
Do not just extract sentences—summarize like a human would, preserving key events and emotions.

Current Episode Text:
{text[:3000]}  # Truncated to avoid token overuse

Return a rich summary that captures the essence of this episode.
"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a highly skilled narrative summarizer."},
            {"role": "user", "content": summary_prompt}
        ],
        temperature=0.7
    )

    return response.choices[0].message.content.strip()


# --- Translation Function ---
def translate_text(text, target_language):
    """
    Translate text to the target language using OpenAI's API
    
    Args:
        text (str): Text to translate
        target_language (str): Target language code or name (e.g., "Spanish", "French", "de", "zh-CN")
        
    Returns:
        str: Translated text
    """
    translation_prompt = f"""
Translate the following text into {target_language}. Maintain the original meaning, tone, and style as much as possible.
Preserve any special formatting, paragraph breaks, and punctuation.

Text to translate:
{text}

Provide only the translated text without any explanations or notes.
"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a professional translator with expertise in literary translation."},
            {"role": "user", "content": translation_prompt}
        ],
        temperature=0.3  # Lower temperature for more accurate translations
    )

    return response.choices[0].message.content.strip()


# --- Translate Episode Function ---
def translate_episode(episode_data, target_language):
    """
    Translate an episode's content to the target language
    
    Args:
        episode_data (dict): Episode data with title, body, etc.
        target_language (str): Target language name or code
        
    Returns:
        dict: Episode data with translated content
    """
    # Create a deep copy to avoid modifying the original
    translated_episode = episode_data.copy()
    
    # Translate title
    translated_episode["title"] = translate_text(episode_data["title"], target_language)
    
    # Translate body
    translated_episode["body"] = translate_text(episode_data["body"], target_language)
    
    # Translate ended_at
    if "ended_at" in episode_data and episode_data["ended_at"]:
        translated_episode["ended_at"] = translate_text(episode_data["ended_at"], target_language)
    
    # Add translation metadata
    translated_episode["translation"] = {
        "original_language": "English",
        "target_language": target_language,
        "translated_at": "AUTO-GENERATED"  # In a real app, use a timestamp here
    }
    
    return translated_episode


# deprecated right now
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
    tone="Comedic", trope=None, style="Third Person", required_characters=None,
    ended_at=None, regional_setting=None
):
    if required_characters:
        character_descriptions = "\n".join(
            f"- {char['name']} ({char['gender']}): {', '.join(char['traits'])}" for char in required_characters
        )
        character_note = f"""Characters in this story:\n{character_descriptions}. These characters **must appear** in this episode.\n"""
    else:
        character_note = ""

    # required_character_note = (
    # f"The following characters **must appear** in this episode: {', '.join(required_characters)}.\n"
    # if required_characters else ""
    # )

    ending_note = (
        "This is the final episode. Provide a satisfying and conclusive ending that resolves all major plotlines, character arcs, and conflicts.\n"
        if episode_number == total_episodes else "End the episode with a suspenseful or emotional cliffhanger to encourage continued interest.\n"
    )

    regional_setting_note = (
        f"The story is set in: **{regional_setting}**.\n" if regional_setting else ""
    )

    system_prompt = f"""
    You are a master storyteller creating episode {episode_number} of a {total_episodes}-episode long-form narrative.
    The story follows the genre: **{tone}**, in **{style}** style.
    The central story trope is: **{trope if trope else 'your choice'}**.
    Your task is to ensure deep narrative consistency, emotional weight, and evolving character dynamics.

    Rules:
    - The episode **must pick up exactly where the previous episode left off**, continuing the scene or event if applicable.
    - **Do NOT resurrect dead characters** from earlier episodes unless there's a well-written and justified twist.
    - Ensure previously killed characters remain absent unless their return is critical and logically explained.
    - Respect and evolve existing character relationships, behaviors, and the tone established so far.
    - Use vivid descriptions, rich dialogues, and evolving conflict.
    - Use only characters that were active previously or new ones introduced meaningfully.
    {character_note}
    {regional_setting_note}
    {ending_note}

    Additional Requirements:
    - At the end of the episode, extract the final one or two lines of the story and include it in a new field called "ended_at".
    - These lines should be exactly as written in the story and will be used to help the next episode start from the same point.
    - Ensure "ended_at" does not contain any commentary or summarization — just raw story lines from the episode's ending.

    Return ONLY a JSON object in the following STRICT format. No markdown, no text, no commentary, no triple backticks.
    Escape newlines using \\n inside the "body" and "ended_at" fields.

    JSON format:
    {{
    "title": "A short, catchy episode title WITHOUT the word 'Episode'",
    "body": "The actual episode content here. Use \\n for newlines.",
    "killed_characters": ["List of characters who died in this episode, if any"],
    "current_characters": ["All currently alive characters at the end of this episode"],
    "ended_at": "Last 1-2 lines of the story content. Use \\n for newlines."
    }}
    """


    user_prompt = f"""
    Episode Number: {episode_number}
    Previous Episode Summary: {summary_context if summary_context else 'No context available'}
    Characters Alive So Far: {previous_characters if previous_characters else 'N/A'}
    Story Ended Previously At: {ended_at if ended_at else 'N/A'}

    Write a connected, coherent episode of around 600–800 words, directly continuing the previous one.
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




# --- Story creation with multiple episodes functionality ---
def create_story(title=None, no_of_episodes=1, trope=None, tone="Comedic", style="Third Person", initial_characters=None, regional_setting=None, target_language=None):
    story_root = "story"
    story_folder = os.path.join(story_root, title)
    os.makedirs(story_folder, exist_ok=True)

    info = {
        'total_episodes': no_of_episodes,
        'title': title,
        'initial_characters': list(initial_characters),
        'trope': trope,
        'style': style,
        'tone': tone,
        'regional_setting': regional_setting
    }

    # Add target language to info if translation is requested
    if target_language:
        info['target_language'] = target_language

    with open(os.path.join(story_folder, "info.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2)

    total_summary = ""
    last_ended_at = None

    # Generate first episode with required characters
    story = generate_episode(
        episode_number=1,
        total_episodes=no_of_episodes,
        trope=trope,
        tone=tone,
        style=style,
        required_characters=list(initial_characters),
        ended_at=last_ended_at,
        regional_setting=regional_setting
    )
    total_summary = summarize_with_openai(story['body'])
    story["summary_till_now"] = total_summary
    last_ended_at = story.get("ended_at", None)

    # Save original episode
    with open(os.path.join(story_folder, "1.json"), "w", encoding="utf-8") as f:
        json.dump(story, f, indent=2)

    # Translate if requested
    if target_language:
        translated_story = translate_episode(story, target_language)
        translated_folder = os.path.join(story_folder, target_language)
        os.makedirs(translated_folder, exist_ok=True)
        
        with open(os.path.join(translated_folder, "1.json"), "w", encoding="utf-8") as f:
            json.dump(translated_story, f, indent=2)

    # Loop for remaining episodes
    for episode in range(2, no_of_episodes + 1):
        story = generate_episode(
            episode_number=episode,
            total_episodes=no_of_episodes,
            summary_context=total_summary,
            previous_characters=story["current_characters"],
            tone=tone,
            trope=trope,
            style=style,
            ended_at=last_ended_at,
            regional_setting=regional_setting
        )
        total_summary += "\n" + summarize_with_openai(story['body'])
        story["summary_till_now"] = total_summary
        last_ended_at = story.get("ended_at", None)

        # Save original episode
        with open(os.path.join(story_folder, f"{episode}.json"), "w", encoding="utf-8") as f:
            json.dump(story, f, indent=2)
            
        # Translate if requested
        if target_language:
            translated_story = translate_episode(story, target_language)
            with open(os.path.join(translated_folder, f"{episode}.json"), "w", encoding="utf-8") as f:
                json.dump(translated_story, f, indent=2)

    return story_folder


# --- Translate existing story ---
def translate_existing_story(story_folder, target_language):
    """
    Translate an existing story to the target language
    
    Args:
        story_folder (str): Path to the story folder
        target_language (str): Target language for translation
        
    Returns:
        str: Path to the folder containing the translated story
    """
    # Create folder for translations
    translated_folder = os.path.join(story_folder, target_language)
    os.makedirs(translated_folder, exist_ok=True)
    
    # Read story info
    with open(os.path.join(story_folder, "info.json"), "r", encoding="utf-8") as f:
        info = json.load(f)
    
    # Update info with translation details
    translated_info = info.copy()
    translated_info["target_language"] = target_language
    translated_info["translated_from"] = "English"
    
    # Save translated info
    with open(os.path.join(translated_folder, "info.json"), "w", encoding="utf-8") as f:
        json.dump(translated_info, f, indent=2)
    
    # Get episode count
    total_episodes = info.get("total_episodes", 0)
    
    # Translate each episode
    for episode in range(1, total_episodes + 1):
        episode_path = os.path.join(story_folder, f"{episode}.json")
        
        # Check if episode file exists
        if not os.path.exists(episode_path):
            print(f"Warning: Episode {episode} file not found. Skipping.")
            continue
            
        # Read episode data
        with open(episode_path, "r", encoding="utf-8") as f:
            episode_data = json.load(f)
        
        # Translate the episode
        translated_episode = translate_episode(episode_data, target_language)
        
        # Save translated episode
        with open(os.path.join(translated_folder, f"{episode}.json"), "w", encoding="utf-8") as f:
            json.dump(translated_episode, f, indent=2)
            
        print(f"Translated episode {episode} to {target_language}")
    
    return translated_folder