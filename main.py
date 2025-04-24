import streamlit as st
import os
import json
from outlines import generate_story_outline, improve_outline, flow_maintainer
from story_generator import finalize_story

# App title
st.set_page_config(page_title="AI Storyteller", layout="wide")
st.title("📖 AI Storyteller")
 
# Path where stories are saved
STORY_DIR = "story"
 
# Create the story directory if it doesn't exist
os.makedirs(STORY_DIR, exist_ok=True)
 
# Session state setup
if 'create_mode' not in st.session_state:
    st.session_state.create_mode = False
if 'outline_mode' not in st.session_state:
    st.session_state.outline_mode = False
if 'selected_story' not in st.session_state:
    st.session_state.selected_story = None
if 'deleted_stories' not in st.session_state:
    st.session_state.deleted_stories = set()
 
# Sidebar: Story titles + Create Story button
st.sidebar.title("📚 Stories")
 
# Track deleted stories in session
if 'deleted_stories' not in st.session_state:
    st.session_state.deleted_stories = set()
 
# Read all story folders
if os.path.exists(STORY_DIR):
    all_stories = [d for d in os.listdir(STORY_DIR) if os.path.isdir(os.path.join(STORY_DIR, d))]
    stories = [s for s in all_stories if s not in st.session_state.deleted_stories]
    stories.sort()
else:
    stories = []
 
if st.sidebar.button("➕ Create Story", key="sidebar_create_btn"):
    st.session_state.create_mode = True
    st.session_state.outline_mode = False
    st.session_state.selected_story = None
 
for story in stories:
    col1, col2 = st.sidebar.columns([4, 1])  # 4:1 ratio
 
    # In the sidebar button click handler, change this section:
    if col1.button(story, key=f"story_btn_{story}"):
        st.session_state.selected_story = story
        st.session_state.create_mode = False
        
        # Check if this story has outlines.json (needs outline mode) or episode files (needs episode view)
        story_path = os.path.join(STORY_DIR, story)
        
        # Check if episode files exist first
        episode_files_exist = any(file.endswith(".json") and file != "info.json" and file != "outlines.json" for file in os.listdir(story_path))
        
        if episode_files_exist:
            # If there are episode files, always show the episodes view
            st.session_state.outline_mode = False
        elif os.path.exists(os.path.join(story_path, "outlines.json")):
            # Only if there are no episode files but there are outlines, go to outline mode
            st.session_state.outline_mode = True
        
        st.rerun()
 
    if col2.button("🗑️", key=f"delete_{story}"):
        st.session_state.deleted_stories.add(story)
        if st.session_state.selected_story == story:
            st.session_state.selected_story = None
        st.rerun()
 
# --- create character traits
# Initialize character list in session state
if 'character_list' not in st.session_state:
    st.session_state.character_list = [{"name": "", "gender": "Other", "traits": ""}]
 
# Function to render character form
def render_character_form():
    st.markdown("### 👥 Initial Characters")
    updated_list = []
 
    for i, character in enumerate(st.session_state.character_list):
        cols = st.columns([2, 2, 4, 1])  # name, gender, traits, delete
        with cols[0]:
            name = st.text_input("Name", value=character["name"], key=f"name_{i}")
        with cols[1]:
            gender = st.selectbox("Gender", ["Male", "Female", "Other"], index=["Male", "Female", "Other"].index(character["gender"]), key=f"gender_{i}")
        with cols[2]:
            traits = st.text_input("Characteristics", value=character["traits"], key=f"traits_{i}")
        with cols[3]:
            if st.button("🗑️", key=f"delete_{i}_button"):
                st.session_state.character_list.pop(i)
                st.rerun()
 
        updated_list.append({"name": name, "gender": gender, "traits": traits})
 
    st.session_state.character_list = updated_list
 
    if st.button("➕ Add Character", key="add_character"):
        st.session_state.character_list.append({"name": "", "gender": "Other", "traits": ""})
        st.rerun()
 
# --- Create story section ---
if st.session_state.create_mode:
    st.header("✍️ Create a New Story")
    render_character_form()
 
    with st.form("create_story_form"):
        title = st.text_input("Story Title")
        no_of_episodes = st.number_input("Number of Episodes", min_value=1, max_value=20, value=2)
        trope = st.text_area("Trope", "a house where jerry tries to kill the house master but tom protects the master.")
        regional_setting = st.text_input("Regional Setting", "a small village in Uttar Pradesh")
        tone = st.selectbox("Tone", [
            "Comedic", "Dramatic", "Suspenseful", "Fantasy", "Romantic", "Dark",
            "Inspirational", "Sci-Fi", "Mystery"
        ])        
        style = st.selectbox("Style", [
            "Third Person", "First Person", "Second Person", "Omniscient",
            "Script Format", "Diary Entry"
        ])
        
        submitted = st.form_submit_button("Generate Outline")
 
        if submitted:
            st.write("⏳ Generating outlines... please wait.")
            generate_story_outline(
                title=title,
                no_of_episodes=no_of_episodes,
                initial_characters=st.session_state.character_list,
                trope=trope,
                tone=tone,
                style=style,
                regional_setting=regional_setting
            )
            st.success(f"Outlines for '{title}' created successfully!")
            st.session_state["selected_story"] = title
            st.session_state["create_mode"] = False
            st.session_state["outline_mode"] = True
            st.rerun()

# --- Show outlines mode ---
if st.session_state.outline_mode:
    story_title = st.session_state.selected_story
    story_path = os.path.join(STORY_DIR, story_title)
    st.session_state.outline_mode = True
    
    try:
        with open(os.path.join(story_path, "info.json")) as f:
            story_info = json.load(f)
        with open(os.path.join(story_path, "outlines.json")) as f:
            outlines = json.load(f)
    except Exception as e:
        st.error(f"Could not load outlines for '{story_title}': {e}")
    else:
        total_episodes = story_info.get("total_episodes", 0)
        
        # Create episode selection dropdown
        episode_options = [f"Episode {ep_num}" for ep_num in range(1, total_episodes + 1)]
        selected_episode = st.selectbox(
            "Select Episode to Review",
            episode_options,
            key="outline_select_episode"
        )
        
        episode_num = int(selected_episode.replace("Episode ", ""))
        
        # Display the outline for the selected episode
        st.markdown(f"## 🏷️ Story: *{story_title}*")
        st.subheader(f"📝 Outline for {selected_episode}")
        
        if str(episode_num) in outlines:
            st.markdown(outlines[str(episode_num)])
            
            # Add feedback form for the outline
            with st.form(f"feedback_form_{episode_num}"):
                feedback = st.text_area("Feedback for this outline:", 
                                        placeholder="I'd like more focus on the conflict...", 
                                        key=f"feedback_{episode_num}")
                
                improve_submitted = st.form_submit_button("Improve Outline")
                
                if improve_submitted and feedback:
                    
                    st.write("⏳ Improving outline based on feedback...")
                    
                    # Update the current episode's outline based on feedback
                    improve_outline(
                        story_title=story_title,
                        episode_num=episode_num,
                        feedback=feedback
                    )
                    
                    # Maintain flow for subsequent episodes
                    flow_maintainer(
                        story_title=story_title,
                        modified_episode=episode_num
                    )
                    
                    st.success(f"Outline for Episode {episode_num} improved and story flow maintained!")
                    st.rerun()
        else:
            st.warning(f"No outline found for Episode {episode_num}")
        # Add a finalize button at the bottom
        if st.button("✅ Finalize Story", key="finalize_story"):
            
            with st.spinner("⏳ Generating full story from outlines... this might take a few minutes."):
                finalize_story(story_title)
            
            st.success(f"Story '{story_title}' has been finalized!")
            
            # Maintain the selected story while turning off outline mode
            st.session_state.outline_mode = False
            # The story is still selected, so it will show in the episodes view
            st.rerun()

# --- Show selected story episodes (when not in outline mode) ---
elif st.session_state.selected_story:
    story_title = st.session_state.selected_story
    story_path = os.path.join(STORY_DIR, story_title)
 
    try:
        with open(os.path.join(story_path, "info.json")) as f:
            story_info = json.load(f)
    except Exception as e:
        st.error(f"Could not load story info for '{story_title}'")
    else:
        total_episodes = story_info.get("total_episodes", 0)
        episode_titles = []
 
        for ep_num in range(1, total_episodes + 1):
            try:
                with open(os.path.join(story_path, f"{ep_num}.json")) as f:
                    episode_data = json.load(f)
                    ep_title = episode_data.get("title", f"Episode {ep_num}")
                    episode_titles.append((ep_title, ep_num))
            except Exception as e:
                episode_titles.append((f"Episode {ep_num} (error)", ep_num))
 
        selected_title = st.selectbox(
            "Select Episode",
            [f"Episode {ep_num}: {title}" for title, ep_num in episode_titles],
            key=f"select_{story_title}"
        )
 
        episode_num = int(selected_title.split(":")[0].replace("Episode ", "").strip())
        episode_file = os.path.join(story_path, f"{episode_num}.json")
 
        if os.path.exists(episode_file):
            with open(episode_file) as f:
                data = json.load(f)
 
            st.markdown(f"## 🏷️ Story: *{story_title}*")
            st.subheader(f"📘 {data['title']}")
            st.write(data["body"].replace("\\n", "\n"))

            with st.expander("📝 Summary Till Now"):
                st.write(data.get("summary_till_now", "No summary available."))
 
elif not st.session_state.create_mode and not st.session_state.outline_mode:
    st.info("No story selected. Choose a story from the sidebar or create a new one.")