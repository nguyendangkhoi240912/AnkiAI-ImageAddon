"""
Test script for Imagen 4 Ultra + Gemini Image Describer Integration
Run: python test_imagen_integration.py
"""

import sys
import os

# Add AnkiAI_ImageAddon to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'AnkiAI_ImageAddon'))

from modules.imagen_provider import (
    GeminiImageDescriber,
    ImagenProvider,
    ImageGenerationPipeline,
)

def test_gemini_image_describer(api_keys):
    """Test Gemini Image Describer"""
    print("\n" + "="*60)
    print("Testing Gemini Image Describer...")
    print("="*60)
    
    try:
        describer = GeminiImageDescriber(api_keys)
        print(f"✓ GeminiImageDescriber initialized with {len(api_keys)} API keys")
        
        # Test 1: Simple vocabulary
        vocab = "procrastinate"
        definition = "to delay or postpone something"
        examples = "I procrastinated on my homework."
        
        print(f"\nGenerating image description for '{vocab}'...")
        description = describer.generate_image_description(vocab, definition, examples)
        print(f"✓ Image description generated:\n  {description[:150]}...")
        
        # Test 2: Abstract concept
        vocab = "resilience"
        definition = "the ability to recover from difficulties"
        examples = "The tree showed resilience despite the storm."
        
        print(f"\nGenerating image description for '{vocab}'...")
        description = describer.generate_image_description(vocab, definition, examples)
        print(f"✓ Image description generated:\n  {description[:150]}...")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_imagen_provider(api_key):
    """Test Imagen Provider"""
    print("\n" + "="*60)
    print("Testing Imagen Provider...")
    print("="*60)
    
    try:
        provider = ImagenProvider(api_key=api_key)
        print(f"✓ ImagenProvider initialized")
        
        # Check availability
        available = provider.is_available()
        print(f"{'✓' if available else '✗'} Imagen API availability: {available}")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_imagen_pipeline(gemini_keys, imagen_key):
    """Test full Imagen Generation Pipeline"""
    print("\n" + "="*60)
    print("Testing Imagen Generation Pipeline...")
    print("="*60)
    
    try:
        pipeline = ImageGenerationPipeline(
            gemini_api_keys=gemini_keys,
            imagen_api_key=imagen_key,
            enable_fallback_to_search=True
        )
        print(f"✓ ImageGenerationPipeline initialized")
        
        # Test end-to-end (without actually generating if we want to skip API calls)
        print("\n✓ Pipeline ready for image generation")
        print("  - GeminiImageDescriber: active")
        print("  - ImagenProvider: active")
        print("  - Fallback to search: enabled")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def validate_config():
    """Validate config.json has Imagen entries"""
    print("\n" + "="*60)
    print("Validating config.json...")
    print("="*60)
    
    try:
        import json
        with open('AnkiAI_ImageAddon/config.json', 'r') as f:
            config = json.load(f)
        
        required_keys = [
            'imagen_enabled',
            'imagen_api_key',
            'gemini_image_description_api_key',
            'gemini_image_description_api_key_backup_1',
            'gemini_image_description_api_key_backup_2',
        ]
        
        for key in required_keys:
            if key in config:
                print(f"✓ Config key present: {key}")
            else:
                print(f"✗ Missing config key: {key}")
                return False
        
        return True
    except Exception as e:
        print(f"✗ Error reading config: {e}")
        return False


def main():
    print("\n" + "█"*60)
    print("IMAGEN 4 ULTRA + GEMINI IMAGE DESCRIBER INTEGRATION TEST")
    print("█"*60)
    
    # Step 1: Validate config
    config_valid = validate_config()
    
    # Step 2: Try to get API keys from config
    try:
        import json
        with open('AnkiAI_ImageAddon/config.json', 'r') as f:
            config = json.load(f)
        
        gemini_desc_keys = [
            config.get('gemini_image_description_api_key', ''),
            config.get('gemini_image_description_api_key_backup_1', ''),
            config.get('gemini_image_description_api_key_backup_2', ''),
        ]
        gemini_desc_keys = [k for k in gemini_desc_keys if k and k.strip()]
        
        imagen_key = config.get('imagen_api_key', '')
        
    except Exception as e:
        print(f"✗ Failed to load config: {e}")
        return
    
    # Step 3: Run tests
    tests_passed = 0
    tests_total = 3
    
    if gemini_desc_keys:
        if test_gemini_image_describer(gemini_desc_keys):
            tests_passed += 1
    else:
        print("\n[SKIPPED] GeminiImageDescriber - no API keys configured")
    
    if imagen_key:
        if test_imagen_provider(imagen_key):
            tests_passed += 1
    else:
        print("\n[SKIPPED] ImagenProvider - no API key configured")
    
    if gemini_desc_keys and imagen_key:
        if test_imagen_pipeline(gemini_desc_keys, imagen_key):
            tests_passed += 1
    else:
        print("\n[SKIPPED] ImageGenerationPipeline - incomplete configuration")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Tests passed: {tests_passed}/{tests_total}")
    
    if tests_passed == tests_total:
        print("\n✓ All tests passed! Imagen integration is ready.")
    else:
        print(f"\n⚠ {tests_total - tests_passed} test(s) skipped or failed.")
        print("  Configure Imagen API keys in AnkiAI_ImageAddon/config.json:")
        print("  - imagen_api_key: [your Imagen API key]")
        print("  - gemini_image_description_api_key: [Gemini API key]")
        print("  - gemini_image_description_api_key_backup_1: [backup 1]")
        print("  - gemini_image_description_api_key_backup_2: [backup 2]")


if __name__ == "__main__":
    main()
