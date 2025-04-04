from google import genai
from google.generativeai import types

def get_health_tips(food):
    """
    Generates a health tip for the identified food using the Gemini API.
    """
    # Initialize the GenerativeModel using genai.Client with vertexai=True
    client = genai.Client(project="momvisionai-1", location="us-central1", vertexai=True)
    model = client.generative_model(model_name="gemini-2.0-flash-001")

    prompt = f"Provide a short health tip for pregnant women about eating {food}."

    response = model.generate_content(
        contents=[prompt]
    )

    print(f"Gemini API response: {response.text}") # For debugging
    return response.text

# Example usage (for testing):
if __name__ == "__main__":
    food_item = "spinach"
    health_tip = get_health_tips(food_item)
    print(f"\nHealth tip for {food_item}: {health_tip}")