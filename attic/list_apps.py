#!/usr/bin/env python3
"""
Interactive App Launcher for IDD Models and Data
"""

import sys
from pathlib import Path

def main():
    # Add src to Python path
    script_dir = Path(__file__).parent
    src_dir = script_dir / "src"
    sys.path.insert(0, str(src_dir))
    
    try:
        from src.idd_mad.apps import list_apps, run_app
        
        print("🚀 IDD Models and Data - App Launcher")
        print("=" * 50)
        
        apps = list_apps()
        
        if not apps:
            print("❌ No apps found!")
            return
        
        # Show menu
        print("Available Apps:")
        app_descriptions = {
            'sir_demo': 'SIR Model Demo - Interactive demonstration of SIR epidemiological model',
            'model_comparison': 'Model Comparison - Compare SIR, SEIR, and SEIRS models side by side', 
            'multi_tab_dashboard': 'Multi-Tab Dashboard - Complete dashboard with multiple analysis tabs'
        }
        
        for i, app_name in enumerate(apps, 1):
            friendly_name = app_name.replace('_', ' ').title()
            description = app_descriptions.get(app_name, f"Shiny app: {app_name}")
            print(f"  {i}. {friendly_name}")
            print(f"     {description}")
            print()
        
        print("  q. Quit")
        print("=" * 50)
        
        # Get user choice
        while True:
            choice = input("Select an app to run (number or 'q' to quit): ").strip().lower()
            
            if choice == 'q':
                print("👋 Goodbye!")
                break
            
            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(apps):
                    selected_app = apps[choice_num - 1]
                    print(f"\n🚀 Starting {selected_app.replace('_', ' ').title()}...")
                    print("📱 App will open in your default browser")
                    print("Press Ctrl+C to stop the server")
                    print("=" * 50)
                    
                    run_app(selected_app)
                    break
                else:
                    print("❌ Invalid choice. Please try again.")
            except ValueError:
                print("❌ Invalid choice. Please enter a number or 'q'.")
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
                
    except ImportError as e:
        print(f"❌ Could not import app manager: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
