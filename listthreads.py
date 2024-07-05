from openai import OpenAI

# Instantiate the client (API key is read from environment by default)
client = OpenAI()

# List all threads (you might need to paginate through results)
threads = client.beta.threads.list()

# This is a simple approach and may need refinement depending on the number of threads and messages
for thread in threads:
    # Retrieve messages for each thread
    messages = client.beta.threads.messages.list(
        thread_id=thread.id,
        order="desc"
    )

    # Filter user messages
    user_messages = [msg for msg in messages if msg.role == 'user']
    
    # Get the latest 10 questions
    last_10_questions = user_messages[:10]
    
    for question in last_10_questions:
        print(question.content['text']['value'])

    # Depending on your needs, you might break after finding the first few threads with user messages
