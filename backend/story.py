from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import random
from typing import Dict, List, Tuple
import re

class StoryGenerator:
    def __init__(self):
        self.tokenizer = None
        self.model = None
        self.device = None
        self.story_templates = {
            "adventure": "A journey filled with excitement and discovery",
            "romance": "A tale of connection and emotion",
            "mystery": "An intriguing puzzle waiting to be solved",
            "fantasy": "Magic and wonder in an imaginary world",
            "inspirational": "A story of growth and achievement"
        }
        
        self.mood_prompts = {
            "happy": "bright and cheerful with warm colors",
            "sad": "soft and melancholic with muted tones",
            "peaceful": "calm and serene with gentle transitions",
            "energetic": "dynamic and vibrant with movement",
            "mysterious": "dark and intriguing with hidden elements",
            "romantic": "warm and tender with soft focus",
            "dull": "subdued and quiet with low contrast",
            "hectic": "chaotic and busy with overlapping elements",
            "motivation": "inspiring with gradual brightness increase",
            "thoughtful": "contemplative with soft, reflective tones",
            "neutral": "balanced and atmospheric"
        }
    
    def _load_model(self):
        """Lazy load the model"""
        if self.tokenizer is None or self.model is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.tokenizer = AutoTokenizer.from_pretrained("gpt2-medium")
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            self.model = AutoModelForCausalLM.from_pretrained("gpt2-medium")
            self.model = self.model.to(self.device)
            self.model.eval()
    
    def generate_story(self, prompt: str, mood: str = "neutral") -> Dict:
        """Generate a simple story based on prompt and mood"""
        
        # Simple story templates
        story_templates = {
            "adventure": [
                f"Once upon a time, in a {mood} land far away...",
                f"The hero embarked on a {mood} journey...",
                f"An unexpected adventure began on a {mood} morning..."
            ],
            "romance": [
                f"Two hearts met under a {mood} sky...",
                f"A {mood} love story unfolded...",
                f"In the {mood} glow of twilight, they found each other..."
            ],
            "mystery": [
                f"A {mood} secret waited to be discovered...",
                f"The {mood} night held many secrets...",
                f"Something {mood} was about to happen..."
            ],
            "inspirational": [
                f"A {mood} journey of self-discovery began...",
                f"She found strength in the {mood} moments...",
                f"The {mood} path led to unexpected places..."
            ],
            "fantasy": [
                f"In a realm of {mood} magic...",
                f"The {mood} prophecy spoke of a hero...",
                f"Magic filled the {mood} air..."
            ],
            "default": [
                f"In a {mood} setting, our story begins...",
                f"The {mood} atmosphere set the stage...",
                f"A {mood} tale unfolded before our eyes..."
            ]
        }
        
        # Determine story type from prompt
        story_type = "default"
        prompt_lower = prompt.lower()
        
        if any(word in prompt_lower for word in ["adventure", "journey", "quest", "explore"]):
            story_type = "adventure"
        elif any(word in prompt_lower for word in ["love", "romance", "heart", "together"]):
            story_type = "romance"
        elif any(word in prompt_lower for word in ["mystery", "secret", "detective", "puzzle"]):
            story_type = "mystery"
        elif any(word in prompt_lower for word in ["inspire", "dream", "hope", "motivate"]):
            story_type = "inspirational"
        elif any(word in prompt_lower for word in ["magic", "dragon", "fantasy", "wizard"]):
            story_type = "fantasy"
        
        # Select template
        template = random.choice(story_templates.get(story_type, story_templates["default"]))
        
        # Generate 3 scenes based on prompt
        scenes = [
            f"{template} {prompt}",
            f"The {mood} journey continued as new challenges emerged.",
            f"In the end, the {mood} experience left everyone transformed."
        ]
        
        # Create title
        title_words = prompt.split()
        if len(title_words) > 3:
            title = " ".join(title_words[:3]) + "..."
        else:
            title = prompt
        title = title.capitalize()
        
        # Get mood description for image prompts
        mood_desc = self.mood_prompts.get(mood, "atmospheric")
        
        # Generate image prompts for each scene
        image_prompts = self._generate_image_prompts(scenes, mood_desc)
        
        return {
            "title": title,
            "scenes": scenes,
            "theme": story_type,
            "mood": mood,
            "mood_description": mood_desc,
            "image_prompts": image_prompts,
            "scene_count": len(scenes)
        }
    
    def _detect_story_type(self, prompt: str) -> str:
        """Detect the type of story from the prompt"""
        prompt_lower = prompt.lower()
        
        type_keywords = {
            "adventure": ["adventure", "journey", "quest", "explore", "discover"],
            "romance": ["love", "romance", "heart", "together", "couple"],
            "mystery": ["mystery", "secret", "detective", "puzzle", "solve"],
            "fantasy": ["magic", "dragon", "wizard", "fantasy", "mythical"],
            "inspirational": ["inspire", "dream", "hope", "achieve", "success"]
        }
        
        for story_type, keywords in type_keywords.items():
            if any(keyword in prompt_lower for keyword in keywords):
                return story_type
        
        return "adventure"  # Default
    
    def _parse_story(self, text: str, original_prompt: str, mood: str) -> Dict:
        """Parse the generated text into structured story"""
        lines = text.split('\n')
        
        title = "Your Story"
        scenes = []
        
        # Extract title
        for line in lines:
            if line.startswith("TITLE:"):
                title = line.replace("TITLE:", "").strip()
                break
        
        # Extract scenes
        current_scene = ""
        scene_num = 0
        
        for line in lines:
            if line.startswith("Scene 1:") or line.startswith("Scene 2:") or line.startswith("Scene 3:"):
                if current_scene:
                    scenes.append(current_scene.strip())
                current_scene = line.split(":", 1)[1].strip() if ":" in line else ""
                scene_num += 1
            elif scene_num > 0 and line.strip() and not line.startswith("Scene"):
                current_scene += " " + line.strip()
        
        # Add the last scene
        if current_scene:
            scenes.append(current_scene.strip())
        
        # Ensure we have 3 scenes
        while len(scenes) < 3:
            scenes.append(self._generate_fallback_scene(original_prompt, len(scenes) + 1, mood))
        
        # Truncate to 3 scenes
        scenes = scenes[:3]
        
        # Generate scene descriptions for image prompts
        mood_desc = self.mood_prompts.get(mood, "atmospheric")
        image_prompts = self._generate_image_prompts(scenes, mood_desc)
        
        return {
            "title": title,
            "scenes": scenes,
            "image_prompts": image_prompts,
            "theme": original_prompt,
            "mood": mood,
            "scene_count": len(scenes)
        }
    
    def _generate_fallback_scene(self, prompt: str, scene_num: int, mood: str) -> str:
        """Generate a fallback scene if parsing fails"""
        fallbacks = {
            1: f"In a {mood} setting, our story begins with {prompt}.",
            2: f"The journey continues as the {mood} atmosphere deepens.",
            3: f"In a {mood} conclusion, everything comes together beautifully."
        }
        return fallbacks.get(scene_num, f"A {mood} scene unfolds.")
    
    def _generate_image_prompts(self, scenes: List[str], mood_desc: str) -> List[str]:
        """Generate image prompts for each scene"""
        image_prompts = []
        
        for i, scene in enumerate(scenes):
            # Create a visual prompt from the scene text
            first_sentence = scene.split('.')[0] if '.' in scene else scene
            
            if i == 0:
                prompt = f"{first_sentence}, {mood_desc}, establishing shot, cinematic composition, detailed, atmospheric, digital art"
            elif i == 1:
                prompt = f"{first_sentence}, {mood_desc}, action scene, dramatic lighting, detailed, atmospheric, digital art"
            else:
                prompt = f"{first_sentence}, {mood_desc}, resolution, emotional payoff, detailed, atmospheric, digital art"
            
            image_prompts.append(prompt)
        
        return image_prompts

# Global instance
_story_generator = StoryGenerator()

def generate_story(prompt: str, mood: str = "neutral") -> Dict:
    """Generate a story with the given prompt and mood"""
    return _story_generator.generate_story(prompt, mood)

# For backward compatibility, also provide a version that works with 1 argument
def generate_story_simple(prompt: str) -> Dict:
    """Generate a story with default mood"""
    return _story_generator.generate_story(prompt, "neutral")