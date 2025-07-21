#!/usr/bin/env python3
"""
AMS Accounting Module Completion Checker
Run this script in your ams_accounting module directory to identify missing components
"""

import os
import re
from pathlib import Path

class AMSAccountingChecker:
    def __init__(self, module_path="."):
        self.module_path = Path(module_path)
        self.issues = []
        self.models = []
        self.missing_views = []
        
    def check_manifest(self):
        """Check __manifest__.py for completeness"""
        manifest_path = self.module_path / "__manifest__.py"
        
        if not manifest_path.exists():
            self.issues.append("❌ Missing __manifest__.py")
            return
            
        with open(manifest_path, 'r') as f:
            content = f.read()
            
        # Check required dependencies
        required_deps = ['account', 'ams_subscriptions', 'base']
        if "'depends':" in content:
            for dep in required_deps:
                if f"'{dep}'" not in content:
                    self.issues.append(f"⚠️  Missing dependency: {dep}")
        else:
            self.issues.append("❌ No 'depends' section in manifest")
            
        # Check data files
        if "'data':" not in content:
            self.issues.append("⚠️  No 'data' section in manifest")
            
        print("✅ Manifest check completed")
    
    def discover_models(self):
        """Discover all model files"""
        models_path = self.module_path / "models"
        
        if not models_path.exists():
            self.issues.append("❌ Missing models directory")
            return
            
        for py_file in models_path.glob("*.py"):
            if py_file.name != "__init__.py":
                self.models.append(py_file.stem)
                
        print(f"📁 Found {len(self.models)} model files")
        return self.models
    
    def check_views(self):
        """Check if views exist for models"""
        views_path = self.module_path / "views"
        
        if not views_path.exists():
            self.issues.append("❌ Missing views directory")
            return
            
        view_files = list(views_path.glob("*.xml"))
        
        # Expected view files based on models
        expected_views = [
            "ams_member_financial_views.xml",
            "ams_chapter_financial_views.xml", 
            "ams_payment_plan_views.xml",
            "ams_subscription_accounting_views.xml",
            "ams_credit_management_views.xml",
            "account_asset_views.xml",
            "account_followup_views.xml",
            "recurring_payments_views.xml",
            "multiple_invoice_views.xml",
            "credit_limit_views.xml"
        ]
        
        existing_view_names = [vf.name for vf in view_files]
        
        for expected in expected_views:
            if expected not in existing_view_names:
                self.missing_views.append(expected)
                
        if self.missing_views:
            print(f"⚠️  Missing {len(self.missing_views)} view files")
        else:
            print("✅ All expected view files present")
    
    def check_reports(self):
        """Check report structure"""
        report_path = self.module_path / "report"
        
        if not report_path.exists():
            self.issues.append("❌ Missing report directory")
            return
            
        report_files = list(report_path.glob("*.py")) + list(report_path.glob("*.xml"))
        
        if len(report_files) <= 1:  # Only __init__.py
            self.issues.append("⚠️  Report directory appears empty")
            
        templates_path = report_path / "templates"
        if not templates_path.exists():
            self.issues.append("⚠️  Missing report/templates directory")
            
        print("📊 Report structure checked")
    
    def check_static_assets(self):
        """Check for static assets"""
        static_path = self.module_path / "static"
        
        if not static_path.exists():
            self.issues.append("⚠️  Missing static directory (CSS/JS)")
            return
            
        # Check for essential static files
        css_path = static_path / "src" / "css"
        js_path = static_path / "src" / "js"
        
        if not css_path.exists():
            self.issues.append("⚠️  Missing CSS directory")
        if not js_path.exists():
            self.issues.append("⚠️  Missing JS directory")
            
        icon_path = static_path / "description" / "icon.png"
        if not icon_path.exists():
            self.issues.append("⚠️  Missing module icon")
            
        print("🎨 Static assets checked")
    
    def check_security(self):
        """Check security configuration"""
        security_path = self.module_path / "security"
        
        if not security_path.exists():
            self.issues.append("❌ Missing security directory")
            return
            
        access_csv = security_path / "ir.model.access.csv"
        if not access_csv.exists():
            self.issues.append("❌ Missing ir.model.access.csv")
            
        # Check if access CSV has entries for all models
        if access_csv.exists():
            with open(access_csv, 'r') as f:
                content = f.read()
                
            model_count = len([m for m in self.models if not m.startswith('__')])
            access_lines = len([line for line in content.split('\n') if line.strip() and not line.startswith('id')])
            
            if access_lines < model_count:
                self.issues.append(f"⚠️  Security access may be incomplete ({access_lines} entries for {model_count} models)")
                
        print("🔒 Security configuration checked")
    
    def check_integration_points(self):
        """Check integration with ams_subscriptions"""
        integration_issues = []
        
        # Check if subscription models are referenced
        models_path = self.module_path / "models"
        subscription_refs = 0
        
        for py_file in models_path.glob("*.py"):
            with open(py_file, 'r') as f:
                content = f.read()
                if 'ams.subscription' in content or 'subscription_id' in content:
                    subscription_refs += 1
                    
        if subscription_refs == 0:
            integration_issues.append("⚠️  No references to ams.subscription found in models")
            
        # Check for invoice automation
        invoice_automation = False
        for py_file in models_path.glob("*.py"):
            with open(py_file, 'r') as f:
                content = f.read()
                if 'invoice_ids' in content and 'subscription' in content:
                    invoice_automation = True
                    break
                    
        if not invoice_automation:
            integration_issues.append("⚠️  No subscription-to-invoice automation detected")
            
        self.issues.extend(integration_issues)
        print("🔗 Integration points checked")
    
    def generate_report(self):
        """Generate completion report"""
        print("\n" + "="*60)
        print("🏁 AMS ACCOUNTING MODULE COMPLETION REPORT")
        print("="*60)
        
        if not self.issues:
            print("🎉 Congratulations! Your module appears complete!")
            return
            
        print(f"\n📋 Found {len(self.issues)} issues to address:\n")
        
        for i, issue in enumerate(self.issues, 1):
            print(f"{i:2d}. {issue}")
            
        if self.missing_views:
            print(f"\n📄 Missing View Files ({len(self.missing_views)}):")
            for view in self.missing_views:
                print(f"    - {view}")
                
        print("\n🔧 PRIORITY ACTIONS:")
        print("1. Create missing view files for your models")
        print("2. Implement report templates")
        print("3. Add static assets (CSS/JS) for dashboards")
        print("4. Verify subscription integration")
        print("5. Test installation and basic functionality")
        
        print("\n💡 Next Steps:")
        print("- Focus on view files first (highest priority)")
        print("- Test module installation after each major component")
        print("- Create sample data for testing")
        
    def run_full_check(self):
        """Run all checks"""
        print("🚀 Starting AMS Accounting Module Completion Check...\n")
        
        self.check_manifest()
        self.discover_models()
        self.check_views()
        self.check_reports()
        self.check_static_assets()
        self.check_security()
        self.check_integration_points()
        
        self.generate_report()

# Usage
if __name__ == "__main__":
    checker = AMSAccountingChecker()
    checker.run_full_check()