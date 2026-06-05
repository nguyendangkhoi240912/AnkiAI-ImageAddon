#!/usr/bin/env python3
"""
Test script for new entertainment image providers.
Tests basic functionality without requiring Anki environment.
"""

import sys
import json
from typing import List, Dict

# Add parent directory to path for imports
sys.path.insert(0, '.')


def test_provider_import():
    """Test that all entertainment providers can be imported."""
    print("=" * 60)
    print("Testing Provider Imports")
    print("=" * 60)
    
    try:
        # Import base classes
        from AnkiAI_ImageAddon.modules.providers.base import (
            ImageProviderError,
            _ImageProviderSessionManager,
        )
        print("✓ Base provider classes imported")
        
        # Import entertainment providers directly from the module
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "entertainment",
            "AnkiAI_ImageAddon/modules/providers/entertainment.py"
        )
        entertainment = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(entertainment)
        
        providers = [
            'HPAPIProvider',
            'PotterAPIProvider',
            'WaifuPicsProvider',
            'NekosBestProvider',
            'StudioGhibliAPIProvider',
            'PokeAPIProvider',
        ]
        
        for provider_name in providers:
            if hasattr(entertainment, provider_name):
                print(f"✓ {provider_name} imported")
            else:
                print(f"✗ {provider_name} NOT FOUND")
                return False
                
        return True
    except Exception as e:
        print(f"✗ Import error: {e}")
        return False


def test_provider_instantiation():
    """Test that providers can be instantiated."""
    print("\n" + "=" * 60)
    print("Testing Provider Instantiation")
    print("=" * 60)
    
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "entertainment",
            "AnkiAI_ImageAddon/modules/providers/entertainment.py"
        )
        entertainment = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(entertainment)
        
        providers = {
            'HPAPIProvider': [],
            'PotterAPIProvider': [],
            'WaifuPicsProvider': [],
            'NekosBestProvider': [],
            'StudioGhibliAPIProvider': [],
            'PokeAPIProvider': [],
        }
        
        for provider_name, args in providers.items():
            try:
                provider_class = getattr(entertainment, provider_name)
                instance = provider_class(*args)
                print(f"✓ {provider_name} instantiated (name: {instance.name})")
            except Exception as e:
                print(f"✗ {provider_name} instantiation failed: {e}")
                return False
                
        return True
    except Exception as e:
        print(f"✗ Instantiation error: {e}")
        return False


def test_provider_attributes():
    """Test that providers have required attributes."""
    print("\n" + "=" * 60)
    print("Testing Provider Attributes")
    print("=" * 60)
    
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "entertainment",
            "AnkiAI_ImageAddon/modules/providers/entertainment.py"
        )
        entertainment = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(entertainment)
        
        required_attrs = ['name', 'session', 'search']
        
        providers = [
            'HPAPIProvider',
            'PotterAPIProvider',
            'WaifuPicsProvider',
            'NekosBestProvider',
            'StudioGhibliAPIProvider',
            'PokeAPIProvider',
        ]
        
        for provider_name in providers:
            provider_class = getattr(entertainment, provider_name)
            instance = provider_class()
            
            missing_attrs = []
            for attr in required_attrs:
                if not hasattr(instance, attr):
                    missing_attrs.append(attr)
            
            if missing_attrs:
                print(f"✗ {provider_name} missing: {', '.join(missing_attrs)}")
                return False
            else:
                print(f"✓ {provider_name} has all required attributes")
                
        return True
    except Exception as e:
        print(f"✗ Attribute check error: {e}")
        return False


def test_provider_registry():
    """Test that providers are registered in the registry."""
    print("\n" + "=" * 60)
    print("Testing Provider Registry")
    print("=" * 60)
    
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "provider_registry",
            "AnkiAI_ImageAddon/modules/provider_registry.py"
        )
        provider_registry = importlib.util.module_from_spec(spec)
        
        # We need to set up the module's globals first to avoid import errors
        provider_registry.__dict__['logging'] = __import__('logging')
        provider_registry.__dict__['ImageProviderError'] = Exception
        
        try:
            spec.loader.exec_module(provider_registry)
        except ImportError:
            # If imports fail due to missing Anki, just check the structure
            print("⚠ Provider registry module requires Anki environment - skipping full load")
            
            # Check the file content instead
            with open('AnkiAI_ImageAddon/modules/provider_registry.py', 'r') as f:
                content = f.read()
                
            provider_ids = [
                'hp_api',
                'potter_api',
                'waifu_pics',
                'nekos_best',
                'studio_ghibli',
                'poke_api',
            ]
            
            for provider_id in provider_ids:
                if f'"{provider_id}"' in content or f"'{provider_id}'" in content:
                    print(f"✓ {provider_id} registered in provider_registry.py")
                else:
                    print(f"✗ {provider_id} NOT found in provider_registry.py")
                    return False
            
            return True
    except Exception as e:
        print(f"✗ Registry check error: {e}")
        return False


def test_documentation():
    """Test that documentation file exists."""
    print("\n" + "=" * 60)
    print("Testing Documentation")
    print("=" * 60)
    
    import os
    
    doc_file = 'ENTERTAINMENT_PROVIDERS_INTEGRATION.md'
    if os.path.exists(doc_file):
        with open(doc_file, 'r') as f:
            content = f.read()
        
        required_sections = [
            'Overview',
            'Harry Potter Providers',
            'Anime Image Providers',
            'Movie Image Providers',
            'Gaming/Character Image Providers',
        ]
        
        for section in required_sections:
            if section in content:
                print(f"✓ {section} documented")
            else:
                print(f"✗ {section} missing from documentation")
                return False
        
        return True
    else:
        print(f"✗ {doc_file} not found")
        return False


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  Entertainment Image Providers - Test Suite".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    
    tests = [
        ("Provider Import", test_provider_import),
        ("Provider Instantiation", test_provider_instantiation),
        ("Provider Attributes", test_provider_attributes),
        ("Provider Registry", test_provider_registry),
        ("Documentation", test_documentation),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} FAILED with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed! Entertainment providers are ready to use.")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed. Please review the output above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
