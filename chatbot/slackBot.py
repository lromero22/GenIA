import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import time
from openai import OpenAI
import io
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from pydrive2.files import FileNotUploadedError
import pandas as pd
import datetime










#FUNCIONES OPENIA
# Enter your Assistant ID here.
ASSISTANT_ID = "asst_qU03iXmDHN79ANifZovHTo3W"
VECTOR_STORE_ID = "vs_Fw06pA9nuJtIZ1nK3tKCtDMU"
# Make sure your API key is set as an environment variable.
client = OpenAI(api_key="sk-proj-jEZa3bMCBGekWKv2KfmAT3BlbkFJCRfkTjTp1ZirMX2b2SHz")




#FUNCIONES SLACK



# Initializes your app with your bot token and socket mode handler
app = App(token="xoxb-7109688004375-7147049314240-iL3rWvccAxOYftLhjGbgXeC7")

@app.event("app_mention")
def handle_app_mention_events(message,say, logger):
    print(message)
    
    
        # Create a thread with a message.
    thread = client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": message['text'],
            }
        ]
    )

    # Submit the thread to the assistant (as a new run).
    run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=ASSISTANT_ID)
    print(f"👉 Run Created: {run.id}")

    # Wait for run to complete.
    while run.status != "completed":
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        print(f"🏃 Run Status: {run.status}")
        time.sleep(1)
    else:
        print(f"🏁 Run Completed!")

    # Get the latest message from the thread.
    message_response = client.beta.threads.messages.list(thread_id=thread.id)
    messages = message_response.data

    # Print the latest message.
    latest_message = messages[0]
    print(f"💬 Response: {latest_message.content[0].text.value}")
        
    
    output = latest_message.content[0].text.value 
    say(output)


#Message handler for Slack
@app.message(".*")
def message_handler(message, say, logger):
    print(message)
    
    
        # Create a thread with a message.
    thread = client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": message['text'],
            }
        ]
    )

    # Submit the thread to the assistant (as a new run).
    run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=ASSISTANT_ID)
    print(f"👉 Run Created: {run.id}")

    # Wait for run to complete.
    while run.status != "completed":
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        print(f"🏃 Run Status: {run.status}")
        time.sleep(1)
    else:
        print(f"🏁 Run Completed!")

    # Get the latest message from the thread.
    message_response = client.beta.threads.messages.list(thread_id=thread.id)
    messages = message_response.data

    # Print the latest message.
    latest_message = messages[0]
    print(f"💬 Response: {latest_message.content[0].text.value}")
        
    
    output = latest_message.content[0].text.value 
    say(output)









# Start your app
if __name__ == "__main__":
    SocketModeHandler(app,"xapp-1-A0737LESZ5M-7109704660871-936c96402da64bec314c0a7efa2f4ff430ba97e608ba6e7ce4fe945575c58623").start()
