from dotenv import load_dotenv
import os
# Load environment variables
# load_dotenv()
# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# summary_prompt ="Hi how are you doing?  " 
                

# response = client.chat.completions.create(
#     model="gpt-4.1-2025-04-14",
#     messages=[
#         {"role": "system", "content": "You're a helpful assistant."},
#         {"role": "user", "content": summary_prompt}
#     ],
#     temperature=0.7
# )
# response = OpenAI.ChatCompletion.create(
#     model="gpt-3.5-turbo",
#     messages=[{"role": "user", "content": "Hello"}]
# )

# print(response.headers)

# print(response.choices[0].message.content.strip())
from openai import OpenAI

# Ask the user to enter their OpenAI API key
api_key = input("Enter your OpenAI API key: ")

# Initialize the OpenAI client with the provided key
client = OpenAI(api_key=api_key)

# Make a request to the Chat API
completion = client.chat.completions.create(
    model="gpt-3.5-turbo-0125",
    messages=[
        {
            "role": "user",
            "content": "Write a one-sentence bedtime story about a unicorn."
        }
    ]
)

# Print the response
print(completion.choices[0].message.content)

