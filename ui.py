import streamlit as st
import os
import json
import shutil

# App title
st.set_page_config(page_title="AI Storyteller", layout="wide")
st.title("📖 AI Storyteller")

# Path where stories are saved
STORY_DIR = "story"

# Session state setup
if 'create_mode' not in st.session_state:
    st.session_state.create_mode = False
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
all_stories = [d for d in os.listdir(STORY_DIR) if os.path.isdir(os.path.join(STORY_DIR, d))]
stories = [s for s in all_stories if s not in st.session_state.deleted_stories]
stories.sort()

if st.sidebar.button("➕ Create Story", key="sidebar_create_btn"):
    st.session_state.create_mode = True
    st.session_state.selected_story = None

for story in stories:
    col1, col2 = st.sidebar.columns([4, 1])  # 4:1 ratio

    if col1.button(story, key=f"story_btn_{story}"):
        st.session_state.selected_story = story
        st.session_state.create_mode = False

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
        # initial_characters = st.text_input("Initial Characters (comma separated)", "jerry, tom")
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
        submitted = st.form_submit_button("Generate Story")

        if submitted:
            from story_generator import create_story

            st.write("⏳ Generating story... this might take few minutes.")
            create_story(
                title=title,
                no_of_episodes=no_of_episodes,
                initial_characters=st.session_state.character_list,
                trope=trope,
                tone=tone,
                style=style,
                regional_setting=regional_setting
            )
            st.success(f"Story '{title}' created successfully!")
            st.session_state["selected_story"] = title
            st.session_state["create_mode"] = False
            st.rerun()

# --- Show selected story episodes ---
if st.session_state.selected_story:
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

            with st.expander("💀 Killed Characters"):
                st.write(", ".join(data.get("killed_characters", [])) or "None")

            with st.expander("🎭 Current Characters"):
                st.write(", ".join(data.get("current_characters", [])) or "None")

            with st.expander("📝 Summary Till Now"):
                st.write(data.get("summary_till_now", "No summary available."))

elif not st.session_state.create_mode:
    st.info("No story selected. Choose a story from the sidebar or create a new one.")
