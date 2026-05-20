# DEPRECATED: This file is superseded by video_tool/analyzer.py, which uses
# the anthropic SDK with claude-sonnet-4-6 and vision support.
import os
import requests

def get_claude_response(prompt):
    """
    Sends a prompt to Claude (Anthropic API) and gets the response.

    Parameters:
        prompt (str): The text prompt to send to Claude.

    Returns:
        str: The response from Claude.
    """
    # Load API key from environment variables
    anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')

    if not anthropic_api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set in environment variables.")

    # Define the API endpoint
    api_url = "https://api.anthropic.com/v1/complete"

    # Define the request payload
    headers = {
        "x-api-key": anthropic_api_key,
        "Content-Type": "application/json"
    }

    payload = {
        "prompt": prompt,
        "model": "claude-v1",  # Replace with the correct model version if needed
        "max_tokens_to_sample": 300
    }

    # Send the request
    response = requests.post(api_url, headers=headers, json=payload)

    if response.status_code == 200:
        return response.json().get("completion", "No completion found.")
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")

if __name__ == "__main__":
    # Example usage of the Claude interaction function
    try:
        user_prompt = "Write a short poem about the stars."
        print("Sending prompt to Claude:", user_prompt)
        result = get_claude_response(user_prompt)
        print("Response from Claude:", result)
    except Exception as e:
        print("An error occurred:", str(e))