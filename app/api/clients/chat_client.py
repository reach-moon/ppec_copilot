import json
import uuid
import requests
import time
from typing import Optional, Callable


class ChatClient:
    """
    A client for interacting with the PPEC Copilot Chat API.
    """

    def __init__(self, base_url: str, session_id: Optional[str] = None):
        """
        Initialize the ChatClient.

        Args:
            base_url: The base URL of the API (e.g., http://localhost:8000)
            session_id: Optional session ID. If not provided, a new one will be generated.
        """
        self.base_url = base_url.rstrip('/')
        self.session_id = session_id or str(uuid.uuid4())
        self.plan_update_callback: Optional[Callable] = None
        self.final_response_callback: Optional[Callable] = None
        self.step_update_callback: Optional[Callable] = None
        self.error_callback: Optional[Callable] = None

    def set_plan_update_callback(self, callback: Callable[[dict], None]):
        """
        Set a callback function to handle plan update events.

        Args:
            callback: A function that takes a dict (parsed plan) as argument
        """
        self.plan_update_callback = callback

    def set_final_response_callback(self, callback: Callable[[dict], None]):
        """
        Set a callback function to handle final response events.

        Args:
            callback: A function that takes a dict (final response) as argument
        """
        self.final_response_callback = callback

    def set_step_update_callback(self, callback: Callable[[dict], None]):
        """
        Set a callback function to handle step update events.

        Args:
            callback: A function that takes a dict (step update) as argument
        """
        self.step_update_callback = callback

    def set_error_callback(self, callback: Callable[[dict], None]):
        """
        Set a callback function to handle error events.

        Args:
            callback: A function that takes a dict (error) as argument
        """
        self.error_callback = callback

    def send_message(self, message: str, turn_id: Optional[str] = None) -> None:
        """
        Send a message to the chat API and process the streaming response.

        Args:
            message: The user's message to send
        """
        url = f"{self.base_url}/api/v1/chat"
        payload = {
            "session_id": self.session_id,
            "message": message
        }
        if turn_id:
            payload["turn_id"] = turn_id

        # Add streaming headers
        headers = {
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache"
        }

        with requests.post(url, json=payload, headers=headers, stream=True) as response:
            response.raise_for_status()
            
            buffer = ""
            for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
                buffer += chunk
                
                # Process complete lines
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()
                    
                    # Skip empty lines
                    if not line:
                        continue
                    
                    # Process Server-Sent Events
                    if line.startswith('event:'):
                        # Event type line - we can use this for better routing if needed
                        event_type = line[6:].strip()
                        # We'll still parse data from the data line
                        
                    elif line.startswith('data:'):
                        data_str = line[5:].strip()  # Skip 'data:' prefix
                        
                        if not data_str:
                            continue
                            
                        try:
                            data = json.loads(data_str)
                            
                            # Handle different event types based on structure
                            if 'summary' in data and 'turn_id' in data:
                                # Final response event
                                if self.final_response_callback:
                                    self.final_response_callback(data)
                            elif 'goal' in data and 'steps' in data:
                                # Plan update event
                                if self.plan_update_callback:
                                    self.plan_update_callback(data)
                            elif 'status' in data and 'turn_id' in data:
                                # Step update event
                                if self.step_update_callback:
                                    self.step_update_callback(data)
                            elif 'error' in data:
                                # Error event
                                if self.error_callback:
                                    self.error_callback(data)
                        except json.JSONDecodeError:
                            print(f"Failed to decode JSON: {data_str}")

    def send_message_sync(self, message: str, poll_interval: float = 0.1, turn_id: Optional[str] = None) -> dict:
        """
        Send a message and return only the final response.
        
        Args:
            message: The user's message to send
            poll_interval: Time to wait between polling for chunks
            
        Returns:
            The final response dictionary
        """
        url = f"{self.base_url}/api/v1/chat"
        payload = {
            "session_id": self.session_id,
            "message": message
        }
        if turn_id:
            payload["turn_id"] = turn_id

        response_data = {}
        
        with requests.post(url, json=payload, stream=True) as response:
            response.raise_for_status()
            
            buffer = ""
            for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
                buffer += chunk
                
                # Process complete lines
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()
                    
                    # Skip empty lines
                    if not line:
                        continue
                    
                    # Process Server-Sent Events
                    if line.startswith('data:'):
                        data_str = line[5:].strip()  # Skip 'data:' prefix
                        
                        if not data_str:
                            continue
                            
                        try:
                            data = json.loads(data_str)
                            
                            # Capture final response
                            if 'summary' in data and 'turn_id' in data:
                                response_data = data
                        except json.JSONDecodeError:
                            print(f"Failed to decode JSON: {data_str}")
                
                # Small delay to prevent busy waiting
                time.sleep(poll_interval)
        
        return response_data


# Example usage
if __name__ == "__main__":
    # Create a client
    client = ChatClient("http://localhost:8000", "test-session-123")
    
    # Define callbacks
    def on_plan_update(plan_data):
        print("Plan Update:")
        print(f"Goal: {plan_data['goal']}")
        for step in plan_data['steps']:
            print(f"  Step {step['step_id']}: {step['instruction']} [{step['status']}]")

    def on_step_update(step_data):
        print("Step Update:")
        print(f"Turn ID: {step_data['turn_id']}")
        print(f"Status: {step_data['status']}")

    def on_final_response(response_data):
        print("Final Response:")
        print(f"Turn ID: {response_data['turn_id']}")
        print(f"Summary: {response_data['summary']}")

    def on_error(error_data):
        print("Error:")
        print(f"Error: {error_data['error']}")

    # Set callbacks
    client.set_plan_update_callback(on_plan_update)
    client.set_step_update_callback(on_step_update)
    client.set_final_response_callback(on_final_response)
    client.set_error_callback(on_error)
    
    # Send a message
    client.send_message("Hello, how can you help me today?")