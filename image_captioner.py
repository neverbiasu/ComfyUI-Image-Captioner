import os
import torch
import dashscope

from http import HTTPStatus
import torchvision.transforms as transforms

def post_process_prompt(raw_prompt):
    tags = [tag.strip().lower() for tag in raw_prompt.split(',') if tag.strip()]
    tags = ['_'.join(tag.split()) for tag in tags]
    seen = set()
    unique_tags = [tag for tag in tags if not (tag in seen or seen.add(tag))]
    final_tags = unique_tags[:70]
    return ', '.join(final_tags)

class ImageCaptioner:
    def __init__(self):
        pass
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "api": ("STRING",{"multiline": True, "default": ""}),
                "user_prompt": ("STRING", {"multiline": True, "default": "As an AI image tagging expert, please provide precise tags for these images to enhance CLIP model's understanding of the content. Employ succinct keywords or phrases, steering clear of elaborate sentences and extraneous conjunctions. Prioritize the tags by relevance. Your tags should capture key elements such as the main subject, setting, artistic style, composition, image quality, color tone, filter, and camera specifications, and any other tags crucial for the image. When tagging photos of people, include specific details like gender, nationality, attire, actions, pose, expressions, accessories, makeup, composition type, age, etc. For other image categories, apply appropriate and common descriptive tags as well. Recognize and tag any celebrities, well-known landmark or IPs if clearly featured in the image. Your tags should be accurate, non-duplicative, and within a 20-75 word count range. These tags will use for image re-creation, so the closer the resemblance to the original image, the better the tag quality. Tags should be comma-separated. Exceptional tagging will be rewarded with $10 per image.", })
            }
        }
    
    RETURN_TYPES = ("STRING",)
    FUNCTION = "generate_image_captions"
    OUTPUT_NODE = True

    CATEGORY = "image"

    def generate_image_captions(self, image, api, user_prompt):
        assert isinstance(image, torch.Tensor), "Image must be a numpy array."
        assert isinstance(api, str), "API key must be a string."
        assert isinstance(user_prompt, str), "User prompt must be a string."

        dashscope.api_key = api
        image = image.squeeze(0)
        image = image.permute(2, 0, 1)
        image = transforms.ToPILImage()(image)

        image.save("image.png") 
        image_url = "image.png"
        
        messages = [
            {
                "role": "system",
                "content": "As an AI image tagging expert, please provide precise tags for these images to enhance CLIP model's understanding of the content. Employ succinct keywords or phrases, steering clear of elaborate sentences and extraneous conjunctions. Prioritize the tags by relevance. Your tags should capture key elements such as the main subject, setting, artistic style, composition, image quality, color tone, filter, and camera specifications, and any other tags crucial for the image. When tagging photos of people, include specific details like gender, nationality, attire, actions, pose, expressions, accessories, makeup, composition type, age, etc. For other image categories, apply appropriate and common descriptive tags as well. Recognize and tag any celebrities, well-known landmark or IPs if clearly featured in the image. Your tags should be accurate, non-duplicative, and within a 20-75 word count range. These tags will use for image re-creation, so the closer the resemblance to the original image, the better the tag quality. Tags should be comma-separated. Exceptional tagging will be rewarded with $10 per image."
            },
            {
                "role": "user",
                "content": [
                    {"image": f"{image_url}"},
                    {"text": f"{user_prompt}"}
                ]
            }
        ]

        response = dashscope.MultiModalConversation.call(
            model="qwen-vl-plus",
            messages=messages
        )

        os.remove(image_url)

        if response.status_code == HTTPStatus.OK:
            raw_prompt = response.output.choices[0].message.content[0]["text"]
            if isinstance(raw_prompt, list):
                # Convert each item in the list to a string
                raw_prompt = ', '.join(str(item) for item in raw_prompt)
            processed_prompt = post_process_prompt(raw_prompt)
            return (processed_prompt,)
        else:
            print(f"Error: {response.code} - {response.message}")
            return ("Error generating captions.",)
