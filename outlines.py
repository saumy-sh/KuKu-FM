import os
import json
import re
from dotenv import load_dotenv
from openai import OpenAI
from json_parse import safe_json_parse

# Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- Outline Generation Functions ---
def generate_outlines(
    total_episodes, 
    initial_characters=None, 
    trope=None,
    tone="Comedic", 
    style="Third Person", 
    regional_setting=None
):
    """Generate episode outlines for the story"""
    
    if initial_characters:
        character_descriptions = "\n".join(
            f"- {char['name']} ({char['gender']}): {char['traits']}" for char in initial_characters
            if char['name'].strip()  # Only include characters with names
        )
        character_note = f"""Characters in this story:\n{character_descriptions}. These characters should appear in the storyline.\n"""
    else:
        character_note = ""
    
    regional_setting_note = (
        f"The story is set in: **{regional_setting}**.\n" if regional_setting else ""
    )
    
    system_prompt = f"""
    You are a master storyteller creating a narrative outline for a {total_episodes}-episode story.
    The story follows the genre: **{tone}**, in **{style}** style.
    The central story trope is: **{trope if trope else 'your choice'}**.
    
    Rules:
    - Create a coherent, flowing story arc across all episodes
    - Each episode outline should be approximately 100 words
    - Ensure character continuity and logical plot progression
    - Make each episode build on the previous ones with rising action
    - Include conflicts, character development, and dramatic moments
    - Create a satisfying conclusion in the final episode
    {character_note}
    {regional_setting_note}
    
    Return a JSON object where each key is the episode number (as a string) and 
    each value is the outline text for that episode.
    
    Example format:
    {{
        "1": "Episode 1 outline text...",
        "2": "Episode 2 outline text...",
        "3": "Episode 3 outline text..."
    }}
    """
    
    user_prompt = f"""
    Generate outlines for {total_episodes} episodes that form a coherent narrative arc.
    Make sure each outline is clear, focused, and contains enough story detail to guide full episode creation later.
    """
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-0125",
        messages=[
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()}
        ],
        temperature=0.8
    )
    
    result = response.choices[0].message.content
    
    # Extract JSON from response (in case there's extra text)
    json_match = re.search(r'\{.*\}', result, re.DOTALL)
    if json_match:
        result = json_match.group(0)
    
    try:
        outlines = safe_json_parse(result)
        return outlines
    except Exception as e:
        print(f"Failed to parse outlines: {e}")
        # Fallback: create a structured format manually
        fallback_outlines = {}
        for ep in range(1, total_episodes + 1):
            fallback_outlines[str(ep)] = f"Outline for episode {ep} could not be generated. Please try again."
        return fallback_outlines
    
def generate_story_outline(title=None, no_of_episodes=1, trope=None, tone="Comedic", style="Third Person", initial_characters=None, regional_setting=None):
    """Create outline for a story and save it to disk"""
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
    
    with open(os.path.join(story_folder, "info.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2)
    
    # Generate outlines for all episodes
    outlines = generate_outlines(
        total_episodes=no_of_episodes,
        initial_characters=initial_characters,
        trope=trope,
        tone=tone,
        style=style,
        regional_setting=regional_setting
    )
    
    # Save outlines to disk
    with open(os.path.join(story_folder, "outlines.json"), "w", encoding="utf-8") as f:
        json.dump(outlines, f, indent=2)
    
    return outlines    

def improve_outline(story_title=None, episode_num=1, feedback=None):
    """Improve an episode outline based on user feedback"""
    story_root = "story"
    story_folder = os.path.join(story_root, story_title)
    
    # Load story info and outlines
    with open(os.path.join(story_folder, "info.json"), "r", encoding="utf-8") as f:
        info = json.load(f)
    
    with open(os.path.join(story_folder, "outlines.json"), "r", encoding="utf-8") as f:
        outlines = json.load(f)
    
    # Get previous episode outlines for context
    previous_outlines = {}
    for ep in range(1, episode_num + 1):
        previous_outlines[str(ep)] = outlines[str(ep)]

    system_prompt = f"""
    You are a narrative consultant improving a story outline for episode {episode_num} of a {info['total_episodes']}-episode story.
    The story follows the genre: **{info['tone']}**, in **{info['style']}** style.
    The central story trope is: **{info['trope']}**.
    
    Your task is to improve the outline for episode {episode_num} based on user feedback, while maintaining consistency with previous episodes.
    
    Rules:
    - Keep the outline to approximately 100 words
    - Incorporate the user's feedback meaningfully 
    - Maintain consistent characters, settings, and plot elements from previous episodes
    - Improve narrative quality, tension, and character development
    - Return ONLY the improved outline text with no additional commentary
    """
    
    user_prompt = f"""
    Previous episode outlines:
    {json.dumps(previous_outlines, indent=2)}
    
    Current outline for Episode {episode_num}:
    {outlines[str(episode_num)]}
    
    User feedback:
    {feedback}
    
    Please provide an improved outline that addresses this feedback while maintaining story coherence.
    """
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-0125",
        messages=[
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()}
        ],
        temperature=0.7
    )
    
    improved_outline = response.choices[0].message.content.strip()
    
    # Update the outline
    outlines[str(episode_num)] = improved_outline
    
    # Save updated outlines
    with open(os.path.join(story_folder, "outlines.json"), "w", encoding="utf-8") as f:
        json.dump(outlines, f, indent=2)
    
    return improved_outline

def flow_maintainer(story_title=None, modified_episode=1):
    """Maintain story flow for subsequent episodes after a change"""
    story_root = "story"
    story_folder = os.path.join(story_root, story_title)
    
    # Load story info and outlines
    with open(os.path.join(story_folder, "info.json"), "r", encoding="utf-8") as f:
        info = json.load(f)
    
    with open(os.path.join(story_folder, "outlines.json"), "r", encoding="utf-8") as f:
        outlines = json.load(f)
    
    total_episodes = info['total_episodes']
    
    # Nothing to do if this is the last episode
    if modified_episode >= total_episodes:
        return outlines
    
    # Process each subsequent episode to maintain flow
    for ep in range(modified_episode + 1, total_episodes + 1):
        # Get all previous outlines for context
        previous_outlines = {}
        for prev_ep in range(1, ep):
            previous_outlines[str(prev_ep)] = outlines[str(prev_ep)]
        
        system_prompt = f"""
        You are a narrative continuity expert maintaining story flow across episodes.
        The story follows the genre: **{info['tone']}**, in **{info['style']}** style.
        The central story trope is: **{info['trope']}**.
        
        Your task is to review and potentially update episode {ep}'s outline to maintain consistency with the previous episodes,
        especially since episode {modified_episode} has been modified.
        
        Rules:
        - Keep the outline to approximately 100 words
        - Ensure logical continuity with all previous episodes
        - Update character arcs, plot points, and references to match modified earlier content
        - Preserve the original essence of this episode if possible
        - Return ONLY the updated outline text with no additional commentary
        """
        
        user_prompt = f"""
        Previous episode outlines (including modifications):
        {json.dumps(previous_outlines, indent=2)}
        
        Current outline for Episode {ep}:
        {outlines[str(ep)]}
        
        Please update this outline if needed to maintain story flow with previous episodes.
        If the outline is already consistent, you can leave it unchanged.
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": user_prompt.strip()}
            ],
            temperature=0.6
        )
        
        updated_outline = response.choices[0].message.content.strip()
        
        # Update the outline
        outlines[str(ep)] = updated_outline
    
    # Save all updated outlines
    with open(os.path.join(story_folder, "outlines.json"), "w", encoding="utf-8") as f:
        json.dump(outlines, f, indent=2)
    
    return outlines