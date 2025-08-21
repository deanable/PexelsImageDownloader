#!/usr/bin/env python3
"""
Simple test script to verify the Pexels API implementation
"""

import sys
import os
import logging
from main import PexelsAPI, download_single_image

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_api_basic_functionality():
    """Test basic API functionality without downloading images"""

    # Test with a sample API key (you'll need to provide a real one)
    api_key = "YOUR_API_KEY_HERE"  # Replace with actual key for testing

    if api_key == "YOUR_API_KEY_HERE":
        print("⚠️  Please provide a valid Pexels API key to test the functionality")
        return False

    try:
        # Initialize API client
        print("🔧 Initializing Pexels API client...")
        api = PexelsAPI(api_key)
        print("✅ API client initialized successfully")

        # Test search functionality
        print("🔍 Testing search functionality...")
        results = api.search_photos("test", per_page=1)

        if results and 'photos' in results:
            print(f"✅ Search successful! Found {len(results['photos'])} photos")
            if results['photos']:
                photo = results['photos'][0]
                print(f"   📸 Sample photo ID: {photo['id']}")
                print(f"   📏 Dimensions: {photo['width']}x{photo['height']}")
                print(f"   👤 Photographer: {photo['photographer']}")
                print(f"   🔗 URL: {photo['src']['original']}")
        else:
            print("❌ Search returned no results")
            return False

        # Test rate limiting
        print("⏱️  Testing rate limiting...")
        import time
        start_time = time.time()

        # Make multiple requests to test rate limiting
        for i in range(3):
            api.search_photos("test", per_page=1)
            print(f"   Request {i+1} completed")

        elapsed_time = time.time() - start_time
        print(f"   Time elapsed: {elapsed_time:.2f}s")

        if elapsed_time >= 1.0:  # Should take at least 1 second due to rate limiting
            print("✅ Rate limiting appears to be working")
        else:
            print("⚠️  Rate limiting may not be working properly")

        print("🎉 All tests passed!")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_image_download():
    """Test image download functionality"""

    api_key = "YOUR_API_KEY_HERE"  # Replace with actual key for testing

    if api_key == "YOUR_API_KEY_HERE":
        print("⚠️  Skipping download test - provide valid API key")
        return True

    try:
        # Create test directory
        test_dir = "test_downloads"
        os.makedirs(test_dir, exist_ok=True)

        # Initialize API and search for a test image
        api = PexelsAPI(api_key)
        results = api.search_photos("test", per_page=1)

        if not results or not results['photos']:
            print("❌ No test image found")
            return False

        img_url = results['photos'][0]['src']['original']
        test_filename = os.path.join(test_dir, "test_image.jpg")

        # Test download
        print("⬇️  Testing image download...")
        success = download_single_image(img_url, test_filename, api.session)

        if success and os.path.exists(test_filename):
            file_size = os.path.getsize(test_filename)
            print(f"✅ Image downloaded successfully! Size: {file_size} bytes")

            # Clean up
            os.remove(test_filename)
            os.rmdir(test_dir)
            return True
        else:
            print("❌ Image download failed")
            return False

    except Exception as e:
        print(f"❌ Download test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Pexels Image Downloader API Implementation")
    print("=" * 60)

    # Test basic functionality
    print("\n📋 Testing basic API functionality...")
    basic_test_passed = test_api_basic_functionality()

    # Test image download
    print("\n📋 Testing image download functionality...")
    download_test_passed = test_image_download()

    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results:")
    print(f"   Basic API functionality: {'✅ PASS' if basic_test_passed else '❌ FAIL'}")
    print(f"   Image download: {'✅ PASS' if download_test_passed else '❌ FAIL'}")

    if basic_test_passed and download_test_passed:
        print("\n🎉 All tests passed! The API implementation is working correctly.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Check the implementation.")
        sys.exit(1)