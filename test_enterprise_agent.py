#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Enterprise Agent POC Test Script
企業 Agent POC 測試腳本

This script performs basic validation of the enterprise agent components.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_imports():
    """Test that all required modules can be imported."""
    print("[TEST] Checking imports...")

    errors = []

    # Test core imports
    try:
        from ultrarag.server import UltraRAG_MCP_Server
        print("  ✓ ultrarag.server")
    except ImportError as e:
        errors.append(f"ultrarag.server: {e}")

    # Test authentication modules
    try:
        from ui.backend.auth import verify_user, create_session
        print("  ✓ ui.backend.auth")
    except ImportError as e:
        errors.append(f"ui.backend.auth: {e}")

    try:
        from ui.backend.auth_routes import auth_bp
        print("  ✓ ui.backend.auth_routes")
    except ImportError as e:
        errors.append(f"ui.backend.auth_routes: {e}")

    # Test optional API libraries
    try:
        import google.generativeai
        print("  ✓ google.generativeai (Gemini API)")
    except ImportError:
        print("  ⚠ google.generativeai not installed (optional)")

    try:
        from tavily import TavilyClient
        print("  ✓ tavily (Web Search API)")
    except ImportError:
        print("  ⚠ tavily not installed (optional)")

    if errors:
        print(f"\n[ERROR] Import failures: {len(errors)}")
        for e in errors:
            print(f"  ✗ {e}")
        return False

    print("[OK] All core imports successful")
    return True


def test_auth_system():
    """Test the authentication system."""
    print("\n[TEST] Checking authentication system...")

    from ui.backend.auth import verify_user, create_session, validate_session

    # Test default admin user
    admin_user = verify_user("admin", "admin123")
    if admin_user:
        print("  ✓ Admin user verification works")
        print(f"    Role: {admin_user.get('role')}")
    else:
        print("  ✗ Admin user verification failed")
        return False

    # Test session creation
    session_token = create_session("admin")
    if session_token:
        print("  ✓ Session creation works")
    else:
        print("  ✗ Session creation failed")
        return False

    # Test session validation
    session_user = validate_session(session_token)
    if session_user:
        print("  ✓ Session validation works")
    else:
        print("  ✗ Session validation failed")
        return False

    print("[OK] Authentication system working")
    return True


def test_server_files():
    """Test that server files exist and are valid Python."""
    print("\n[TEST] Checking server files...")

    server_files = [
        "servers/gemini/src/gemini.py",
        "servers/websearch/src/websearch.py",
        "servers/agent_router/src/agent_router.py",
        "servers/prompt/src/prompt.py",
        "servers/custom/src/custom.py",
    ]

    all_exist = True
    for server_file in server_files:
        path = project_root / server_file
        if path.exists():
            print(f"  ✓ {server_file}")
        else:
            print(f"  ✗ {server_file} not found")
            all_exist = False

    if all_exist:
        print("[OK] All server files exist")
    else:
        print("[WARN] Some server files missing")

    return all_exist


def test_pipeline_files():
    """Test that pipeline and parameter files exist."""
    print("\n[TEST] Checking pipeline files...")

    files = [
        "examples/enterprise_agent.yaml",
        "examples/enterprise_deep_research.yaml",
        "examples/parameter/enterprise_agent_parameter.yaml",
    ]

    all_exist = True
    for f in files:
        path = project_root / f
        if path.exists():
            print(f"  ✓ {f}")
        else:
            print(f"  ✗ {f} not found")
            all_exist = False

    if all_exist:
        print("[OK] All pipeline files exist")

    return all_exist


def test_prompt_templates():
    """Test that prompt templates exist."""
    print("\n[TEST] Checking prompt templates...")

    templates = [
        "prompt/enterprise_rag.jinja",
        "prompt/enterprise_web_search.jinja",
        "prompt/enterprise_hybrid.jinja",
    ]

    all_exist = True
    for template in templates:
        path = project_root / template
        if path.exists():
            print(f"  ✓ {template}")
        else:
            print(f"  ✗ {template} not found")
            all_exist = False

    if all_exist:
        print("[OK] All prompt templates exist")

    return all_exist


def test_env_file():
    """Test environment configuration."""
    print("\n[TEST] Checking environment configuration...")

    env_file = project_root / ".env"
    env_dev_file = project_root / ".env.dev"

    if env_file.exists():
        print("  ✓ .env file exists")

        # Check for API keys (without revealing values)
        with open(env_file, 'r') as f:
            content = f.read()

        if "GOOGLE_API_KEY=" in content:
            value = os.environ.get("GOOGLE_API_KEY", "")
            if value:
                print("  ✓ GOOGLE_API_KEY is set")
            else:
                print("  ⚠ GOOGLE_API_KEY is empty (set in .env or environment)")

        if "TAVILY_API_KEY=" in content:
            value = os.environ.get("TAVILY_API_KEY", "")
            if value:
                print("  ✓ TAVILY_API_KEY is set")
            else:
                print("  ⚠ TAVILY_API_KEY is empty (optional for web search)")
    else:
        print("  ⚠ .env file not found")
        if env_dev_file.exists():
            print("  ℹ .env.dev exists - copy to .env and configure")

    print("[OK] Environment check complete")
    return True


def test_yaml_syntax():
    """Test YAML syntax of pipeline files."""
    print("\n[TEST] Checking YAML syntax...")

    import yaml

    yaml_files = [
        "examples/enterprise_agent.yaml",
        "examples/enterprise_deep_research.yaml",
        "examples/parameter/enterprise_agent_parameter.yaml",
        "servers/gemini/parameter.yaml",
        "servers/websearch/parameter.yaml",
        "servers/agent_router/parameter.yaml",
    ]

    all_valid = True
    for yaml_file in yaml_files:
        path = project_root / yaml_file
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    yaml.safe_load(f)
                print(f"  ✓ {yaml_file}")
            except yaml.YAMLError as e:
                print(f"  ✗ {yaml_file}: {e}")
                all_valid = False
        else:
            print(f"  - {yaml_file} (not found)")

    if all_valid:
        print("[OK] All YAML files have valid syntax")

    return all_valid


def main():
    """Run all tests."""
    print("=" * 50)
    print("   企業 Agent POC - 系統測試")
    print("=" * 50)

    # Change to project directory
    os.chdir(project_root)

    # Load environment variables
    env_file = project_root / ".env"
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)

    results = []

    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Server Files", test_server_files()))
    results.append(("Pipeline Files", test_pipeline_files()))
    results.append(("Prompt Templates", test_prompt_templates()))
    results.append(("YAML Syntax", test_yaml_syntax()))
    results.append(("Environment", test_env_file()))
    results.append(("Authentication", test_auth_system()))

    # Summary
    print("\n" + "=" * 50)
    print("   測試結果摘要")
    print("=" * 50)

    passed = 0
    failed = 0
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\nTotal: {passed} passed, {failed} failed")

    if failed == 0:
        print("\n[SUCCESS] 所有測試通過！系統已準備好運行。")
        print("\n下一步:")
        print("  1. 設定 .env 中的 GOOGLE_API_KEY")
        print("  2. 執行 python start_enterprise_agent.py")
        print("  3. 開啟瀏覽器 http://localhost:5050")
        return 0
    else:
        print(f"\n[WARNING] {failed} 項測試失敗，請檢查上述錯誤")
        return 1


if __name__ == "__main__":
    sys.exit(main())
