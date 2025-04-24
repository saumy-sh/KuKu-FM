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
    You are a master storyteller and screenwriter, skilled in narrative arcs and episodic storytelling. Your task is to craft detailed outlines for episodes of a story. These outlines will serve as blueprints for writing full episodes later.

    ### Guidelines:
    - The story must span a **clear and engaging arc** across all episodes.
    - Each episodes outline should:
        - Be **~200 words** max
        - Begin with a **natural continuation** from the previous episode
        - Include **conflicts, stakes**, and **key turning points**
        - Show **character evolution** and emotional development
        - End with a compelling **cliffhanger**, emotional shift, or resolution to keep momentum
    - Plot progression must be **logical and cause-effect driven**
    - Gradually build intensity, with a **major climax** in the penultimate or final episode
    - Ensure a **satisfying conclusion** in the last episode that ties up major arcs
    - Maintain consistent **tone, voice, and setting**
    - Be imaginative, but grounded within the logic and style of the world
    - Each outline should clearly present the progression of the plot and character arcs .

    ### Output Format:
    Return a **JSON object** where:
    - Each key is the episode number (as a string)
    - Each value is the **episode outline** (max 200 words)

    ### Example:
    {{
    "1": "Episode 1 outline text...",
    "2": "Episode 2 outline text...",
    "3": "Episode 3 outline text..."
    }}
    """
    
    user_prompt = f"""
    Generate structured outlines for a {total_episodes}-episode story .

    ### Story Information:
    - **Genre**: {tone}
    - **Style**: {style}
    - **Trope**: {trope if trope else 'Choose an appropriate one'}

    {character_note}
    {regional_setting_note}
    
    Please:
    - Maintain narrative continuity from episode to episode
    - Provide sufficient plot and emotional development per episode
    - Introduce and escalate conflict
    - Guide characters through internal and external growth
    - Build toward a climax and satisfying resolution
    - Keep outlines focused, imaginative, and clear
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
    for ep in range(1, episode_num):
        previous_outlines[str(ep)] = outlines[str(ep)]

    system_prompt = f"""
    You are a professional narrative editor and script consultant.

    Your task is to revise the episode's outline of a serialized story based on user feedback. The story has a defined genre, style, and trope, and you must preserve coherence with the previous episodes and overall story arc.

    ### Your Responsibilities:
    - Revise the episode outline to **incorporate user feedback** meaningfully and creatively
    - Ensure consistency with:
        - **Previous episode outlines** (character arcs, events, tone)
        - The story’s **genre**, **style**, and **central trope**
    - Maintain or enhance:
        - Narrative flow
        - Character development
        - Emotional impact or dramatic tension
    - Keep the outline to approximately **100 words**
    - Ensure the episode transitions logically from the previous one

    Only return the improved outline **as a single paragraph of text**. Do not include any explanation or metadata.
    """
    
    user_prompt = f"""
    You are revising **Episode {episode_num}** in a story with the following details:

    ### Story Overview:
    - **Total Episodes**: {info['total_episodes']}
    - **Genre**: {info['tone']}
    - **Style**: {info['style']}
    - **Central Trope**: {info['trope']}

    ### Previous Episode Outlines:
    {json.dumps(previous_outlines, indent=2)}

    ### Original Outline for Episode {episode_num}:
    "{outlines[str(episode_num)]}"

    ### User Feedback:
    "{feedback}"

    Please return an improved version of the episode outline that addresses the feedback while staying faithful to the story so far.
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
        You are a narrative continuity specialist tasked with maintaining consistent story flow across episodes in a multi-part series.

        The story follows the genre: **{info['tone']}**, in **{info['style']}** style.
        The central story trope is: **{info['trope']}**.

        Your job is to revise (only if necessary) the outline for Episode {ep} so that it flows logically from all previous episodes, especially Episode {modified_episode}, which has been recently updated based on user feedback.

        Guidelines:
        - Do NOT rewrite unless continuity, character development, or logic has been broken.
        - If changes are needed, preserve the soul, theme, tone, and purpose of the original outline.
        - Keep the new outline to approximately 100 words.
        - Ensure consistent character motivations, plot logic, and relationship dynamics.
        - Reflect any major events or consequences from the modified episode in the current one.
        - Maintain emotional and narrative pacing.
        - Return **only the updated outline text** with no explanation or commentary.
        """

        
        user_prompt = f"""
        The total number of episodes in the story is {info['total_episodes']}.

        Below are all the previous outlines up to Episode {ep}, including modifications made by the user to Episode {modified_episode}:
        {json.dumps(previous_outlines, indent=2)}

        Current outline for Episode {ep}:
        "{outlines[str(ep)]}"

        Please revise this outline **only if necessary** to ensure smooth narrative flow, consistency in character arcs and events, and logical progression from previous episodes.

        If the current outline already aligns well with prior content, you may return it unchanged.
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
