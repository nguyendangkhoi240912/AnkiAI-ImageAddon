"""
Example: Using Imagen 4 Ultra with Gemini Image Description
This demonstrates how to use the Imagen integration in your code.
"""

from AnkiAI_ImageAddon.modules.api_handler import AIImageProvider

# Example 1: Initialize with Imagen support
def example_1_basic_initialization():
    """Basic initialization with Imagen enabled"""
    provider = AIImageProvider(
        # AI providers for keyword generation
        gemini_key="sk-...",
        groq_key="gsk-...",
        
        # Image evaluators (optional)
        gemini_eval_api_key_1="sk-...",
        
        # Imagen 4 Ultra
        imagen_enabled=True,
        imagen_api_key="your-imagen-api-key",
        
        # 3 Gemini APIs for image description
        gemini_image_description_api_key="sk-...",
        gemini_image_description_api_key_backup_1="sk-...",
        gemini_image_description_api_key_backup_2="sk-...",
        
        # Provider config
        provider_config={},
        enable_smart_selection=True,
        enable_ai_evaluation=True,
    )
    
    return provider


# Example 2: Generate image with Imagen
def example_2_generate_with_imagen():
    """Generate image using Imagen pipeline"""
    provider = example_1_basic_initialization()
    
    vocabulary = "serendipity"
    definition = "the occurrence of events by chance in a happy or beneficial way"
    examples = "Finding that book was pure serendipity."
    
    try:
        # Generate with Imagen
        images, provider_name, metadata = provider.generate_image_with_imagen(
            vocabulary=vocabulary,
            definition=definition,
            examples=examples,
            width=1024,
            height=1024,
            style="photorealistic"
        )
        
        if images:
            print(f"✓ Generated {len(images)} image(s) using {provider_name}")
            print(f"  Image description: {metadata['description'][:100]}...")
            
            # Save to file
            with open(f"{vocabulary}_generated.png", "wb") as f:
                f.write(images[0])
        else:
            print("✗ No images generated")
    
    except Exception as e:
        print(f"✗ Error: {e}")


# Example 3: Smart image selection (search vs generate)
def example_3_smart_selection():
    """Choose between search-based and AI-generated images"""
    provider = example_1_basic_initialization()
    
    vocabulary = "ephemeral"
    definition = "lasting for a very short time"
    examples = "The beauty of cherry blossoms is ephemeral."
    
    # Prefer generated images if available
    url_or_path, source = provider.generate_image_smart(
        vocabulary=vocabulary,
        definition=definition,
        examples=examples,
        prefer_generated=True,  # Try Imagen first
        width=1024,
        height=1024,
        style="photorealistic"
    )
    
    print(f"Image source: {source}")
    print(f"Image: {url_or_path}")


# Example 4: Check Imagen availability
def example_4_check_availability():
    """Check if Imagen is available"""
    provider = example_1_basic_initialization()
    
    if provider.is_imagen_available():
        print("✓ Imagen is available")
        stats = provider.get_imagen_stats()
        print(f"  Generation stats: {stats}")
    else:
        print("✗ Imagen is not available")


# Example 5: Traditional search-based image
def example_5_search_based():
    """Use traditional search-based image selection"""
    provider = example_1_basic_initialization()
    
    vocabulary = "resilience"
    definition = "ability to recover from difficulties"
    examples = ""
    
    # Get image URL from Pexels, Unsplash, etc.
    url = provider.get_image_url(vocabulary, definition, examples)
    print(f"Found image: {url}")


if __name__ == "__main__":
    print("Imagen 4 Ultra Integration Examples")
    print("="*50)
    
    print("\n1. Basic Initialization")
    print("-"*50)
    print("provider = AIImageProvider(..., imagen_enabled=True, ...)")
    
    print("\n2. Generate with Imagen (AI-generated images)")
    print("-"*50)
    print("images, provider_name, metadata = provider.generate_image_with_imagen(...)")
    
    print("\n3. Smart Selection (automatic search vs generate)")
    print("-"*50)
    print("url, source = provider.generate_image_smart(..., prefer_generated=True)")
    
    print("\n4. Check Imagen Status")
    print("-"*50)
    print("if provider.is_imagen_available():")
    print("    stats = provider.get_imagen_stats()")
    
    print("\n5. Traditional Search (Pexels, Unsplash, etc.)")
    print("-"*50)
    print("url = provider.get_image_url(...)")
    
    print("\n" + "="*50)
    print("For full examples, uncomment and run example_*() functions above")
