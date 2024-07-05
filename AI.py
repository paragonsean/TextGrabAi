class YourClass:
    def __init__(self, client, assistant_id):
        self.client = client
        self.assistant_id = assistant_id

    def upload_file(self, file_path, purpose):
        # Upload a file
        with open(file_path, 'rb') as file_data:
            file = self.client.files.create(
                file=file_data,
                purpose=purpose
            )
        return file.id

    def get_assistant_response(self, question, file_id=None):
        # Create a Thread
        thread = self.client.beta.threads.create()

        # Message creation with optional file
        message_data = {
            "thread_id": thread.id,
            "role": "user",
            "content": question
        }
        if file_id:
            message_data["file_ids"] = [file_id]

        # Add a Message to the Thread
        self.client.beta.threads.messages.create(**message_data)

        # Run the Assistant
        run = self.client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=self.assistant_id
        )

        # Check the status of the Run and retrieve the response
        while run.status != "completed":
            time.sleep(1)  # Wait for a short period before checking again
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )

        # Retrieve the Messages added by the Assistant to the Thread
        messages = self.client.beta.threads.messages.list(
            thread_id=thread.id
        )

        # Extract and return the response text
        for message in messages:
            for text_or_image in message.content:
                if text_or_image.type == 'text':
                    return text_or_image.text.value