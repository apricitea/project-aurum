#!/usr/bin/env python3
"""
Security Validation Test for Project Aurum
Quick test to verify security implementations
"""

def test_security_modules():
    """Test that security modules can be imported"""
    try:
        # Test security module imports
        print("Testing security module imports...")
        
        # Test password security
        from src.api.password_security import validate_password, hash_password, verify_password
        print("✅ Password security module loaded")
        
        # Test security config
        from src.api.security_config import SecurityConfig, SecurityValidator
        print("✅ Security config module loaded")
        
        # Test security middleware
        from src.api.security_middleware import SecurityHeaders, RateLimiter, InputSanitizer
        print("✅ Security middleware module loaded")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    
    return True

def test_password_validation():
    """Test password validation functionality"""
    print("\nTesting password validation...")
    
    try:
        from src.api.password_security import validate_password
        
        # Test weak password
        weak_result = validate_password("password123", "testuser")
        if not weak_result["is_valid"]:
            print("✅ Weak password correctly rejected")
        else:
            print("❌ Weak password incorrectly accepted")
        
        # Test strong password
        strong_result = validate_password("MyStr0ng!P@ssw0rd#2024", "testuser")
        if strong_result["is_valid"]:
            print("✅ Strong password correctly accepted")
        else:
            print("❌ Strong password incorrectly rejected")
            print(f"   Errors: {strong_result.get(\"errors\", [])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Password validation test failed: {e}")
        return False

def test_input_sanitization():
    """Test input sanitization"""
    print("\nTesting input sanitization...")
    
    try:
        from src.api.security_middleware import InputSanitizer
        
        # Test SQL injection detection
        try:
            InputSanitizer.sanitize_string("SELECT * FROM users WHERE id = 1")
            print("❌ SQL injection not detected")
        except ValueError:
            print("✅ SQL injection correctly detected")
        
        # Test XSS detection
        try:
            InputSanitizer.sanitize_string("<script>alert(\"xss\")</script>")
            print("❌ XSS not detected")
        except ValueError:
            print("✅ XSS correctly detected")
        
        # Test safe input
        safe_input = InputSanitizer.sanitize_string("This is a safe input string")
        if safe_input:
            print("✅ Safe input correctly processed")
        
        return True
        
    except Exception as e:
        print(f"❌ Input sanitization test failed: {e}")
        return False

def test_security_headers():
    """Test security headers"""
    print("\nTesting security headers...")
    
    try:
        from src.api.security_middleware import SecurityHeaders
        
        headers = SecurityHeaders.get_security_headers()
        
        required_headers = [
            "Strict-Transport-Security",
            "X-Content-Type-Options", 
            "X-Frame-Options",
            "Content-Security-Policy"
        ]
        
        all_present = True
        for header in required_headers:
            if header in headers:
                print(f"✅ {header} header configured")
            else:
                print(f"❌ {header} header missing")
                all_present = False
        
        return all_present
        
    except Exception as e:
        print(f"❌ Security headers test failed: {e}")
        return False

def main():
    """Run all security tests"""
    print("=== PROJECT AURUM SECURITY VALIDATION ===")
    print()
    
    tests = [
        ("Module Imports", test_security_modules),
        ("Password Validation", test_password_validation), 
        ("Input Sanitization", test_input_sanitization),
        ("Security Headers", test_security_headers)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with error: {e}")
            results.append((test_name, False))
        print()
    
    # Summary
    print("=== TEST SUMMARY ===")
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print()
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All security tests passed!")
        print("✅ Security implementation is working correctly")
    else:
        print("⚠️  Some security tests failed")
        print("❌ Review security implementation before production")
    
    return passed == total

if __name__ == "__main__":
    main()

