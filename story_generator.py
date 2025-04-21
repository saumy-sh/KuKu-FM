#story_generator.py
import os
import json
import spacy
from dotenv import load_dotenv
from openai import OpenAI
from json_parse import safe_json_parse
 
# Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Load spaCy model
nlp = spacy.load("en_core_web_sm")
  
# --- OpenAI Summarization ---
def summarize_with_openai(text, previous_summary=None):
    if previous_summary:
        summary_prompt = f"""
You are an expert story summarizer. Continue building on the previous episode's summary in a natural and seamless way.
Merge the important events and emotional highlights from the current story text with the previous summary to form one continuous narrative.
 
Previous Summary:
{previous_summary}
 
Current Episode Text:
{text}  # Truncated to avoid token overuse
 
Return a single, flowing summary that reads like one continuous abstract. The summary shouldn't be long.
"""
    else:
        summary_prompt = f"""
You are an expert story summarizer. Provide a well-written abstract summary of the following story text.
Do not just extract sentences—summarize like a human would, preserving key events and emotions.
 
Current Episode Text:
{text}  # Truncated to avoid token overuse
 
Return a rich summary that captures the essence of this episode. The summary should not be long.
"""
 
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-0125",
        messages=[
            {"role": "system", "content": "You are a highly skilled narrative summarizer."},
            {"role": "user", "content": summary_prompt}
        ],
        temperature=0.7
    )
 
    return response.choices[0].message.content.strip()

# --- Episode generation using OpenAI ---
def generate_episode(
    episode_number, total_episodes, summary_context=None, previous_characters=None,
    tone="Comedic", trope=None, style="Third Person", required_characters=None,
    ended_at=None, regional_setting=None, episode_outline=None
):
    if required_characters:
        character_descriptions = "\n".join(
            f"- {char['name']} ({char['gender']}): {', '.join(char['traits'])}" for char in required_characters
        )
        character_note = f"""Characters in this story:\n{character_descriptions}. These characters **must appear** in this episode.\n"""
    else:
        character_note = ""
 
    ending_note = (
        "This is the final episode. Provide a satisfying and conclusive ending that resolves all major plotlines, character arcs, and conflicts.\n"
        if episode_number == total_episodes else "End the episode with a suspenseful or emotional cliffhanger to encourage continued interest.\n"
    )
 
    regional_setting_note = (
        f"The story is set in: **{regional_setting}**.\n" if regional_setting else ""
    )
    
    outline_note = (
        f"Follow this outline for the episode:\n{episode_outline}\n" if episode_outline else ""
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
    {outline_note}
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
        model="gpt-3.5-turbo-0125",
        messages=[
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()}
        ],
        temperature=0.9
    )
 
    result = response.choices[0].message.content
    return safe_json_parse(result)

def finalize_story(story_title):
    """Generate full story episodes based on the finalized outlines"""
    story_root = "story"
    story_folder = os.path.join(story_root, story_title)
    
    # Load story info and outlines
    with open(os.path.join(story_folder, "info.json"), "r", encoding="utf-8") as f:
        info = json.load(f)
    
    with open(os.path.join(story_folder, "outlines.json"), "r", encoding="utf-8") as f:
        outlines = json.load(f)
    
    total_episodes = info['total_episodes']
    initial_characters = info['initial_characters']
    trope = info['trope']
    tone = info['tone']
    style = info['style']
    regional_setting = info['regional_setting']
    
    total_summary = ""
    last_ended_at = None
    
    # Generate first episode with required characters
    story = generate_episode(
        episode_number=1,
        total_episodes=total_episodes,
        trope=trope,
        tone=tone,
        style=style,
        required_characters=list(initial_characters),
        ended_at=last_ended_at,
        regional_setting=regional_setting,
        episode_outline=outlines['1']
    )
    total_summary = summarize_with_openai(story['body'])
    story["summary_till_now"] = total_summary
    last_ended_at = story.get("ended_at", None)
    
    with open(os.path.join(story_folder, "1.json"), "w", encoding="utf-8") as f:
        json.dump(story, f, indent=2)
    
    if total_episodes == 1:
        return
    
    # Loop for remaining episodes
    for episode in range(2, total_episodes + 1):
        story = generate_episode(
            episode_number=episode,
            total_episodes=total_episodes,
            summary_context=total_summary,
            previous_characters=story["current_characters"],
            tone=tone,
            trope=trope,
            style=style,
            ended_at=last_ended_at,
            regional_setting=regional_setting,
            episode_outline=outlines[str(episode)]
        )
        total_summary = summarize_with_openai(story['body'], total_summary)
        story["summary_till_now"] = total_summary
        last_ended_at = story.get("ended_at", None)
        
        with open(os.path.join(story_folder, f"{episode}.json"), "w", encoding="utf-8") as f:
            json.dump(story, f, indent=2)
            
            